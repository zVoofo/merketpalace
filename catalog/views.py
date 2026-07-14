from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Max, Min
from django.conf import settings
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_POST
from .models import Category, Brand, CarMake, SearchQuery, SearchRequest
from .validators import is_valid_search_query
from .search_images import get_cached_search_image, get_preview_bytes
from .external import get_external_offers
from accounts.notifications import notify


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
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    in_stock = request.GET.get('in_stock')
    make_id = request.GET.get('make')
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
    if make_id:
        qs = qs.filter(car_compat__make_id=make_id)

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
        max_price=Max('price'),
    )
    price_max_default = int(price_bounds.get('max_price') or 500000)
    if price_max_default < 10000:
        price_max_default = 500000

    return render(request, 'catalog/index.html', {
        'title': 'Каталог',
        'listings': page,
        'total': total,
        'categories': Category.objects.filter(is_active=True),
        'brands': Brand.objects.filter(is_active=True),
        'car_makes': CarMake.objects.all(),
        'filters': request.GET,
        'zero_result': bool(q) and search_valid and total == 0,
        'search_invalid': bool(q) and not search_valid,
        'search_error': search_error,
        'preview_image': preview_image,
        'show_search_preview': bool(q) and search_valid,
        'preview_source': preview_source,
        'external_offers': external_offers,
        'search_query': q,
        'price_slider_max': price_max_default,
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
        return redirect('accounts:my_requests')
    return redirect('catalog:looking')


def looking_board(request):
    """Публичная доска — заявки других покупателей (без своих)."""
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

    return render(request, 'catalog/looking.html', {
        'title': 'Заявки покупателей',
        'search_requests': requests_qs,
        'seller_listings': seller_listings,
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
        return redirect(reverse('seller:requests') + '#sent')

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
    return redirect(reverse('seller:requests') + '#sent')


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
