from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Max, Min, F
from django.conf import settings
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_POST
from .models import Category, Brand, CarMake, SearchQuery, SearchRequest
from .validators import is_valid_search_query
from .search_images import get_cached_search_image, get_preview_bytes
from .external import get_external_offers
from accounts.notifications import notify


def _catalog_without(get_params, *keys):
    params = get_params.copy()
    for key in keys:
        params.pop(key, None)
    qs = params.urlencode()
    base = reverse('catalog:index')
    return f'{base}?{qs}' if qs else base


def home(request):
    from listings.models import Listing
    listings = Listing.objects.filter(status='active').select_related('category').prefetch_related('images')[:12]
    categories = Category.objects.filter(parent__isnull=True, is_active=True).prefetch_related('children')
    return render(request, 'home/index.html', {
        'title': 'Главная — MarketPlace',
        'listings': listings,
        'categories': categories,
    })


def catalog_index(request):
    from listings.models import Listing

    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    listing_type = request.GET.get('type')
    condition = request.GET.get('condition')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    in_stock = request.GET.get('in_stock')
    has_warranty = request.GET.get('warranty')
    on_sale = request.GET.get('sale')
    make_id = request.GET.get('make')
    min_rating = request.GET.get('rating')
    with_photo = request.GET.get('photo')
    preorder = request.GET.get('preorder')
    sort = request.GET.get('sort', 'new')

    search_valid = True
    search_error = ''
    if q:
        search_valid, search_error = is_valid_search_query(q)

    qs = Listing.objects.filter(status='active').select_related('category', 'brand').prefetch_related('images')

    preview_image = None
    preview_source = None
    external_offers = []

    if q and search_valid:
        qs = qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) |
            Q(sku__icontains=q)
        )
        preview = get_cached_search_image(q)
        preview_source = preview.get('source')
        external_offers = get_external_offers(q)
    elif q and not search_valid:
        qs = qs.none()

    if category_id:
        qs = qs.filter(category_id=category_id)
    if brand_id:
        qs = qs.filter(brand_id=brand_id)
    if listing_type:
        qs = qs.filter(type=listing_type)
    if price_min:
        qs = qs.filter(price__gte=price_min)
    if price_max:
        qs = qs.filter(price__lte=price_max)
    if in_stock:
        qs = qs.filter(quantity__gt=0)
    if has_warranty:
        qs = qs.filter(has_warranty=True)
    if on_sale:
        qs = qs.filter(old_price__isnull=False, old_price__gt=F('price'))
    if condition:
        qs = qs.filter(condition=condition)
    if make_id:
        qs = qs.filter(car_compat__make_id=make_id)
    if min_rating:
        try:
            qs = qs.filter(rating_avg__gte=float(min_rating), rating_count__gt=0)
        except (TypeError, ValueError):
            pass
    if with_photo:
        qs = qs.filter(images__isnull=False)
    if preorder:
        qs = qs.filter(quantity=0)

    order_map = {
        'price_asc': 'price',
        'price_desc': '-price',
        'rating': '-rating_avg',
        'popular': '-views_count',
        'new': '-published_at',
    }
    qs = qs.order_by(order_map.get(sort, '-published_at')).distinct()

    total = qs.count()
    if q and search_valid:
        SearchQuery.objects.create(
            user=request.user if request.user.is_authenticated else None,
            query=q,
            results_count=total,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

    paginator = Paginator(qs, settings.ITEMS_PER_PAGE)
    page = paginator.get_page(request.GET.get('page'))

    price_bounds = Listing.objects.filter(status='active').aggregate(
        min_price=Min('price'),
        max_price=Max('price'),
    )
    price_min_default = int(price_bounds.get('min_price') or 0)
    price_max_default = int(price_bounds.get('max_price') or 500000)
    if price_max_default < 10000:
        price_max_default = 500000

    active_filters = []
    if q:
        active_filters.append(('q', f'«{q}»'))
    if category_id:
        cat = Category.objects.filter(pk=category_id).first()
        if cat:
            active_filters.append(('category', cat.name))
    if brand_id:
        br = Brand.objects.filter(pk=brand_id).first()
        if br:
            active_filters.append(('brand', br.name))
    if listing_type:
        active_filters.append(('type', 'Товар' if listing_type == 'product' else 'Услуга'))
    if condition:
        labels = {'new': 'Новый', 'used': 'Б/У', 'refurbished': 'Восстановленный'}
        active_filters.append(('condition', labels.get(condition, condition)))
    if price_min:
        active_filters.append(('price_min', f'от {price_min} ₽'))
    if price_max:
        active_filters.append(('price_max', f'до {price_max} ₽'))
    if in_stock:
        active_filters.append(('in_stock', 'В наличии'))
    if has_warranty:
        active_filters.append(('warranty', 'С гарантией'))
    if on_sale:
        active_filters.append(('sale', 'Со скидкой'))
    if make_id:
        mk = CarMake.objects.filter(pk=make_id).first()
        if mk:
            active_filters.append(('make', mk.name))
    if min_rating:
        active_filters.append(('rating', f'Рейтинг от {min_rating}★'))
    if with_photo:
        active_filters.append(('photo', 'С фото'))
    if preorder:
        active_filters.append(('preorder', 'Под заказ'))

    filter_remove_urls = {key: _catalog_without(request.GET, key) for key, _ in active_filters}

    return render(request, 'catalog/index.html', {
        'title': 'Каталог',
        'listings': page,
        'total': total,
        'categories': Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related('children'),
        'brands': Brand.objects.filter(is_active=True).order_by('name'),
        'car_makes': CarMake.objects.all().order_by('name'),
        'filters': request.GET,
        'active_filters': active_filters,
        'filter_remove_urls': filter_remove_urls,
        'has_active_filters': bool(active_filters),
        'sort': sort,
        'zero_result': bool(q) and search_valid and total == 0,
        'search_invalid': bool(q) and not search_valid,
        'search_error': search_error,
        'preview_image': preview_image,
        'show_search_preview': bool(q) and search_valid,
        'preview_source': preview_source,
        'external_offers': external_offers,
        'search_query': q,
        'price_slider_max': price_max_default,
        'price_slider_min': price_min_default,
    })


@require_POST
def search_request_view(request):
    query = request.POST.get('query', '').strip()
    description = request.POST.get('description', '').strip()
    valid, error = is_valid_search_query(query)
    if not valid:
        messages.error(request, error)
        return redirect(f'/catalog/?q={query}')
    if description and len(description) >= 3:
        desc_valid, desc_error = is_valid_search_query(description)
        if not desc_valid:
            messages.error(request, f'Описание: {desc_error}')
            return redirect(f'/catalog/?q={query}')
    SearchRequest.objects.create(
        user=request.user if request.user.is_authenticated else None,
        query=query,
        description=description,
        contact=request.POST.get('contact', ''),
    )
    messages.success(request, 'Заявка на поиск отправлена!')
    if request.user.is_authenticated:
        return redirect(reverse('accounts:my_requests'))
    return redirect('catalog:looking')


def _listing_thumb_url(listing) -> str:
    from django.templatetags.static import static
    img = listing.images.filter(media_type='image').first()
    if img and img.file:
        try:
            return img.file.url
        except Exception:
            pass
    return static('img/no-photo.svg')


def _rank_listings_for_query(listings, query: str):
    """Поднять вверх объявления, похожие на текст заявки."""
    q = (query or '').strip().lower()
    words = [w for w in q.replace('—', ' ').replace(',', ' ').split() if len(w) >= 3]

    def score(listing):
        title = listing.title.lower()
        s = 0
        if q and q in title:
            s += 10
        for w in words:
            if w in title:
                s += 3
        return s

    return sorted(listings, key=score, reverse=True)


def looking_board_context(request):
    """Контекст доски заявок покупателей."""
    requests_qs = SearchRequest.objects.filter(
        status__in=[SearchRequest.Status.NEW, SearchRequest.Status.IN_PROGRESS]
    ).select_related('user').order_by('-created_at')
    if request.user.is_authenticated:
        requests_qs = requests_qs.exclude(user=request.user)

    seller_listings = []
    if request.user.is_authenticated and request.user.active_role == 'seller':
        from listings.models import Listing
        seller_listings = list(Listing.objects.filter(
            user=request.user, status=Listing.Status.ACTIVE,
        ).prefetch_related('images').order_by('-updated_at'))

    seller_listings_payload = [
        {
            'id': l.id,
            'title': l.title,
            'slug': l.slug,
            'price': int(l.price),
            'quantity': l.quantity,
            'image': _listing_thumb_url(l),
        }
        for l in seller_listings
    ]

    return {
        'search_requests': requests_qs,
        'seller_listings': seller_listings,
        'seller_listings_count': len(seller_listings),
        'seller_listings_payload': seller_listings_payload,
    }


def looking_board(request):
    ctx = looking_board_context(request)
    incoming_count = 0
    if request.user.is_authenticated:
        from listings.views import looking_requests_context
        incoming_count = looking_requests_context(request.user).get('incoming_count', 0)
    return render(request, 'catalog/looking.html', {
        'title': 'Заявки покупателей',
        'hub_active': 'board',
        'requests_badge': incoming_count,
        **ctx,
    })


@login_required
@require_POST
def respond_to_search(request, pk):
    """Продавец предлагает своё объявление на заявку."""
    from listings.models import Listing
    sr = get_object_or_404(SearchRequest, pk=pk)
    if sr.user_id == request.user.id:
        messages.error(request, 'Нельзя предложить товар на свою же заявку')
        return redirect('catalog:looking')
    if sr.status not in (SearchRequest.Status.NEW, SearchRequest.Status.IN_PROGRESS):
        messages.error(request, 'На эту заявку уже есть отклик')
        return redirect('catalog:looking')
    listing_id = request.POST.get('listing_id')
    if not listing_id or not str(listing_id).isdigit():
        messages.error(request, 'Выберите объявление')
        return redirect('catalog:looking')
    listing = Listing.objects.filter(
        pk=int(listing_id), user=request.user, status=Listing.Status.ACTIVE,
    ).first()
    if not listing:
        messages.error(request, 'Объявление не найдено или снято с публикации')
        return redirect('catalog:looking')
    sr.matched_listing = listing
    sr.matched_seller = request.user
    sr.status = SearchRequest.Status.FOUND
    sr.response_seen = False
    sr.save(update_fields=['matched_listing', 'matched_seller', 'status', 'response_seen'])
    if sr.user:
        seller_name = request.user.first_name or request.user.username
        try:
            notify(
                sr.user,
                'search_offer',
                f'Отклик: {sr.query}',
                f'Продавец {seller_name} предложил: {listing.title}',
                '/accounts/my-requests/#offers',
            )
        except Exception:
            pass
    messages.success(request, f'Вы предложили «{listing.title}» на заявку «{sr.query}»')
    return redirect(reverse('catalog:looking') + '#board')


@login_required
@require_POST
def decline_search_offer(request, pk):
    """Покупатель отклоняет предложение — заявка снова в «Ищу», продавец получает уведомление."""
    sr = get_object_or_404(SearchRequest, pk=pk, user=request.user, status=SearchRequest.Status.FOUND)
    seller = sr.matched_seller or (sr.matched_listing.user if sr.matched_listing else None)
    if not sr.matched_listing or not seller:
        messages.error(request, 'Нет активного предложения для отклонения')
        return redirect(reverse('accounts:my_requests') + '#offers')

    listing_title = sr.matched_listing.title
    query = sr.query

    sr.matched_listing = None
    sr.matched_seller = None
    sr.status = SearchRequest.Status.NEW
    sr.response_seen = False
    sr.save(update_fields=['matched_listing', 'matched_seller', 'status', 'response_seen'])

    notify(
        seller,
        'search_offer',
        f'Предложение не подошло — «{query}»',
        f'Покупатель отклонил ваше предложение «{listing_title}». Заявка снова в разделе «Ищу».',
        '/catalog/looking/',
    )

    messages.success(request, 'Предложение отклонено. Заявка снова видна продавцам.')
    return redirect(reverse('accounts:my_requests') + '#offers')


@login_required
@require_POST
def withdraw_search_offer(request, pk):
    """Продавец отзывает своё предложение."""
    sr = get_object_or_404(
        SearchRequest,
        pk=pk,
        matched_listing__user=request.user,
        status=SearchRequest.Status.FOUND,
    )
    if not sr.matched_listing:
        messages.error(request, 'Нет активного предложения')
        return redirect(reverse('accounts:my_requests') + '#sent')

    listing_title = sr.matched_listing.title
    buyer = sr.user
    query = sr.query

    sr.matched_listing = None
    sr.matched_seller = None
    sr.status = SearchRequest.Status.NEW
    sr.response_seen = False
    sr.save(update_fields=['matched_listing', 'matched_seller', 'status', 'response_seen'])

    if buyer:
        notify(
            buyer,
            'search_offer',
            f'Предложение отозвано — «{query}»',
            f'Продавец отозвал предложение «{listing_title}». Можете дождаться других откликов.',
            '/accounts/my-requests/',
        )

    messages.success(request, 'Предложение отозвано. Заявка снова в общем списке.')
    return redirect(reverse('accounts:my_requests') + '#sent')


def search_preview(request):
    """Картинка-превью поиска — отдаётся напрямую, без /media/."""
    q = request.GET.get('q', '').strip()
    valid, _ = is_valid_search_query(q)
    if not valid:
        raise Http404
    data, _ = get_preview_bytes(q)
    if not data:
        raise Http404
    response = HttpResponse(data, content_type='image/jpeg')
    response['Cache-Control'] = 'public, max-age=3600'
    return response
