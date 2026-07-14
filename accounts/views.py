from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.urls import reverse
from django.views.decorators.http import require_POST
from .forms import RegisterForm, LoginForm, ProfileForm, OrganizationForm, VerifyCodeForm
from .verification import send_email_verification, verify_email_code, send_phone_verification, verify_phone_code
from .wallet_forms import TopUpForm
from .wallet_service import get_wallet, deposit
from .notifications import normalize_notification_link
from .models import User, Organization, WalletTransaction, SocialAccount
from .middleware import log_action
from . import vk_oauth
from catalog.models import SearchRequest
from listings.models import Listing, ModerationQueue
from listings.services import get_seller_rating
from listings.views import looking_requests_context


def staff_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Доступ только для администраторов. Войдите: admin / admin123')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            get_wallet(user)
            login(request, user)
            log_action(user, 'register', 'user', user.pk, request)
            messages.success(request, 'Регистрация успешна!')
            return redirect('accounts:profile')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form, 'title': 'Регистрация'})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            get_wallet(user)
            login(request, user)
            log_action(user, 'login', 'user', user.pk, request)
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('home')
        messages.error(request, 'Неверный логин или пароль')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form, 'title': 'Вход'})


def logout_view(request):
    logout(request)
    return redirect('home')


def social_login(request, provider):
    """Вход через соцсети. VK — реальный OAuth при настроенных ключах."""
    provider = provider.lower()
    if provider not in ('vk', 'google', 'apple'):
        return redirect('accounts:login')

    if request.user.is_authenticated:
        return redirect('home')

    if provider == 'vk' and vk_oauth.vk_configured():
        return vk_oauth_start(request)

    if provider == 'vk':
        messages.error(
            request,
            'Вход через VK ещё не настроен. Добавьте VK_APP_ID и VK_APP_SECRET в переменные окружения на сервере.',
        )
        return redirect('accounts:login')

    # Демо для Google / Apple (без API-ключей)
    provider_id = request.session.get(f'social_{provider}_id')
    if not provider_id:
        import uuid
        provider_id = str(uuid.uuid4())[:12]
        request.session[f'social_{provider}_id'] = provider_id

    username = f'{provider}_{provider_id}'
    user = User.objects.filter(social_accounts__provider=provider, social_accounts__provider_id=provider_id).first()
    if not user:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@social.local',
                'first_name': {'google': 'Google', 'apple': 'Apple'}.get(provider, provider),
            },
        )
        if created:
            user.set_unusable_password()
            user.save()
            SocialAccount.objects.create(user=user, provider=provider, provider_id=provider_id)
        get_wallet(user)

    login(request, user)
    messages.success(request, f'Демо-вход через {provider.upper()} выполнен')
    return redirect('home')


def vk_oauth_start(request):
    state = vk_oauth.new_oauth_state()
    request.session['vk_oauth_state'] = state
    next_url = request.GET.get('next', '')
    if next_url and next_url.startswith('/'):
        request.session['vk_oauth_next'] = next_url
    redirect_uri = vk_oauth.vk_redirect_uri(request)
    return redirect(vk_oauth.build_authorize_url(redirect_uri, state))


def _login_or_create_vk_user(vk_user_id: str, email: str, profile: dict) -> User:
    provider_id = str(vk_user_id)
    social = SocialAccount.objects.filter(provider='vk', provider_id=provider_id).select_related('user').first()
    if social:
        return social.user

    first = (profile.get('first_name') or '').strip() or 'VK'
    last = (profile.get('last_name') or '').strip()
    username = f'vk_{provider_id}'

    user = None
    if email:
        user = User.objects.filter(email__iexact=email).first()

    if not user:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email or f'{username}@vk.social',
                'first_name': first,
                'last_name': last,
            },
        )
        if created:
            user.set_unusable_password()
            if email:
                user.email_verified = True
            user.save()
    else:
        if not user.first_name and first:
            user.first_name = first
        if not user.last_name and last:
            user.last_name = last
        if email and not user.email_verified:
            user.email_verified = True
        user.save(update_fields=['first_name', 'last_name', 'email_verified'])

    SocialAccount.objects.get_or_create(
        provider='vk',
        provider_id=provider_id,
        defaults={'user': user},
    )
    get_wallet(user)
    return user


def vk_callback(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.GET.get('error'):
        messages.error(request, 'Вход через VK отменён')
        return redirect('accounts:login')

    code = request.GET.get('code', '').strip()
    state = request.GET.get('state', '').strip()
    expected = request.session.pop('vk_oauth_state', '')
    next_url = request.session.pop('vk_oauth_next', '')

    if not code or not state or not expected or state != expected:
        messages.error(request, 'Ошибка безопасности при входе через VK. Попробуйте снова.')
        return redirect('accounts:login')

    redirect_uri = vk_oauth.vk_redirect_uri(request)
    try:
        token_data = vk_oauth.exchange_code(code, redirect_uri)
        vk_user_id = str(token_data.get('user_id', ''))
        access_token = token_data.get('access_token', '')
        email = (token_data.get('email') or '').strip()
        if not vk_user_id or not access_token:
            raise ValueError('VK не вернул данные пользователя')
        profile = vk_oauth.fetch_profile(access_token, vk_user_id)
        user = _login_or_create_vk_user(vk_user_id, email, profile)
    except Exception as e:
        messages.error(request, f'Не удалось войти через VK: {e}')
        return redirect('accounts:login')

    login(request, user)
    log_action(user, 'login', 'user', user.pk, request, meta='vk')
    messages.success(request, 'Вход через VK выполнен')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('home')


def public_profile_view(request, username):
    from django.db.models import Avg, Count
    from listings.models import Listing, Review

    profile_user = get_object_or_404(User, username=username)
    active_listings = Listing.objects.filter(
        user=profile_user, status=Listing.Status.ACTIVE,
    ).prefetch_related('images').order_by('-published_at')[:12]

    listings_count = Listing.objects.filter(
        user=profile_user, status=Listing.Status.ACTIVE,
    ).count()
    total_listings = Listing.objects.filter(user=profile_user).exclude(
        status=Listing.Status.ARCHIVED,
    ).count()

    reviews_agg = Review.objects.filter(
        seller=profile_user, status=Review.Status.APPROVED,
    ).aggregate(avg=Avg('rating'), cnt=Count('id'))

    return render(request, 'accounts/public_profile.html', {
        'title': profile_user.full_name,
        'profile_user': profile_user,
        'listings_count': listings_count,
        'total_listings': total_listings,
        'rating_avg': reviews_agg['avg'],
        'rating_count': reviews_agg['cnt'] or 0,
        'listings': active_listings,
        'is_own': request.user.is_authenticated and request.user.pk == profile_user.pk,
    })


@login_required
def profile_view(request):
    tab = request.GET.get('tab', '')
    if tab == 'requests':
        anchor = request.GET.get('section', '')
        url = reverse('accounts:my_requests')
        if anchor in ('offers', 'my-searches', 'sent'):
            url += f'#{anchor}'
        return redirect(url)
    if tab == 'board':
        return redirect('catalog:looking')

    org = getattr(request.user, 'organization', None)
    wallet = get_wallet(request.user)
    verify_form = VerifyCodeForm()
    edit_mode = request.GET.get('edit') == '1'
    form = None
    org_form = None

    if request.method == 'POST':
        if 'switch_role' in request.POST:
            role = request.POST.get('role', 'buyer')
            request.user.active_role = role
            request.user.save(update_fields=['active_role'])
            messages.success(request, f'Режим: {"Продавец" if role == "seller" else "Покупатель"}')
            return redirect('accounts:profile')

        if 'send_email_code' in request.POST:
            email = request.POST.get('email') or request.user.email
            if not email:
                messages.error(request, 'Укажите email')
            else:
                try:
                    code = send_email_verification(request.user, email)
                    msg = 'Код отправлен на email'
                    if settings.DEBUG:
                        msg += f' (тест: {code})'
                    messages.success(request, msg)
                except Exception as e:
                    messages.error(request, f'Не удалось отправить email: {e}')
            return redirect('accounts:profile')

        if 'verify_email' in request.POST:
            verify_form = VerifyCodeForm(request.POST)
            if verify_form.is_valid():
                email = request.POST.get('email') or request.user.email
                if verify_email_code(request.user, email, verify_form.cleaned_data['code']):
                    messages.success(request, 'Email подтверждён!')
                else:
                    messages.error(request, 'Неверный или просроченный код')
            return redirect('accounts:profile')

        if 'send_phone_code' in request.POST:
            phone = request.POST.get('phone') or request.user.phone
            if not phone:
                messages.error(request, 'Укажите телефон')
            else:
                code = send_phone_verification(request.user, phone)
                msg = 'SMS-код отправлен'
                if settings.DEBUG:
                    msg += f' (тест: {code})'
                messages.success(request, msg)
            return redirect('accounts:profile')

        if 'verify_phone' in request.POST:
            verify_form = VerifyCodeForm(request.POST)
            if verify_form.is_valid():
                phone = request.POST.get('phone') or request.user.phone
                if verify_phone_code(request.user, phone, verify_form.cleaned_data['code']):
                    messages.success(request, 'Телефон подтверждён!')
                else:
                    messages.error(request, 'Неверный или просроченный код')
            return redirect('accounts:profile')

        if 'save_profile' in request.POST:
            form = ProfileForm(request.POST, request.FILES, instance=request.user)
            org_form = OrganizationForm(request.POST, instance=org)
            profile_ok = form.is_valid()
            org_ok = org_form.is_valid()
            edit_mode = True
            if profile_ok:
                form.save()
            if org_ok:
                org_data = org_form.cleaned_data
                if org_data.get('name'):
                    org_obj = org_form.save(commit=False)
                    org_obj.user = request.user
                    org_obj.save()
            if profile_ok:
                messages.success(request, 'Профиль обновлён')
                return redirect('accounts:profile')
            for field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, f'{field}: {err}')

    if form is None:
        form = ProfileForm(instance=request.user)
        org_form = OrganizationForm(instance=org)

    rating_avg, rating_count = get_seller_rating(request.user)
    looking_incoming_count = SearchRequest.objects.filter(
        user=request.user,
        status=SearchRequest.Status.FOUND,
        matched_listing__isnull=False,
        response_seen=False,
    ).count()

    ctx = {
        'title': 'Профиль',
        'form': form,
        'org_form': org_form,
        'wallet': wallet,
        'verify_form': verify_form,
        'org': org,
        'edit_mode': edit_mode,
        'rating_avg': rating_avg,
        'rating_count': rating_count,
        'looking_incoming_count': looking_incoming_count,
        **looking_requests_context(request.user),
    }

    return render(request, 'accounts/profile.html', ctx)


@login_required
def cabinet_view(request):
    return redirect('accounts:profile')


@login_required
def my_requests_view(request):
    return render(request, 'accounts/my_requests.html', {
        'title': 'Мои заявки',
        **looking_requests_context(request.user),
    })


@login_required
def wallet_view(request):
    wallet = get_wallet(request.user)
    transactions = wallet.transactions.all()[:30]
    form = TopUpForm()
    quick_amounts = [500, 1000, 3000, 10000]
    if request.method == 'POST':
        quick = request.POST.get('quick_amount')
        if quick:
            try:
                from decimal import Decimal
                amount = Decimal(quick)
                if Decimal('100') <= amount <= Decimal('500000'):
                    deposit(request.user, amount, 'Быстрое пополнение')
                    messages.success(request, f'Кошелёк пополнен на {amount:,.0f} ₽'.replace(',', ' '))
                    return redirect('accounts:wallet')
            except Exception:
                messages.error(request, 'Некорректная сумма')
                return redirect('accounts:wallet')
        form = TopUpForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            method = form.cleaned_data['payment_type']
            deposit(request.user, amount, f'Пополнение через {method}')
            messages.success(request, f'Кошелёк пополнен на {amount:,.0f} ₽'.replace(',', ' '))
            return redirect('accounts:wallet')
    return render(request, 'accounts/wallet.html', {
        'title': 'Кошелёк',
        'wallet': wallet,
        'transactions': transactions,
        'form': form,
        'quick_amounts': quick_amounts,
    })


@staff_required
def panel_dashboard(request):
    stats = {
        'users': User.objects.count(),
        'listings': Listing.objects.count(),
        'pending': ModerationQueue.objects.filter(status='pending').count(),
    }
    return render(request, 'panel/dashboard.html', {'title': 'Панель управления', 'stats': stats})


@staff_required
def panel_moderation(request):
    queue = ModerationQueue.objects.filter(status='pending').select_related('listing')
    return render(request, 'panel/moderation.html', {'title': 'Модерация', 'queue': queue})


@staff_required
def panel_approve(request, pk):
    item = get_object_or_404(ModerationQueue, pk=pk)
    if item.listing:
        item.listing.status = Listing.Status.ACTIVE
        item.listing.published_at = timezone.now()
        item.listing.save()
    item.status = 'approved'
    item.save()
    messages.success(request, 'Объявление одобрено')
    return redirect('panel:moderation')


@staff_required
def panel_reject(request, pk):
    item = get_object_or_404(ModerationQueue, pk=pk)
    if item.listing:
        item.listing.status = Listing.Status.REJECTED
        item.listing.save()
    item.status = 'rejected'
    item.save()
    return redirect('panel:moderation')


@staff_required
def panel_users(request):
    users = User.objects.all().order_by('-date_joined')[:100]
    return render(request, 'panel/users.html', {'title': 'Пользователи', 'users': users})


@staff_required
def panel_verify_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.is_verified = True
    user.save()
    Organization.objects.filter(user=user).update(is_verified=True)
    return redirect('panel:users')


@login_required
def notification_open(request, pk):
    """Безопасный переход по уведомлению — исправляет старые битые ссылки."""
    from .models import Notification
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=['is_read'])
    return redirect(normalize_notification_link(n.link))


@login_required
@require_POST
def notifications_delete(request, pk):
    from .models import Notification
    Notification.objects.filter(pk=pk, user=request.user).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def notifications_read(request):
    from .models import Notification
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})


def serve_stored_file(request, file_id):
    import uuid
    from pathlib import Path
    from .models import StoredFile

    try:
        uid = uuid.UUID(str(file_id))
        obj = StoredFile.objects.filter(pk=uid).first()
        if obj:
            response = HttpResponse(bytes(obj.data), content_type=obj.content_type)
            response['Content-Length'] = obj.size
            if obj.content_type.startswith('image/') or obj.content_type.startswith('video/'):
                response['Content-Disposition'] = 'inline'
            else:
                response['Content-Disposition'] = f'inline; filename="{obj.original_name}"'
            return response
    except (ValueError, TypeError, AttributeError):
        pass

    disk_path = Path(settings.MEDIA_ROOT) / file_id
    if disk_path.is_file():
        return FileResponse(disk_path.open('rb'), as_attachment=False)

    raise Http404
