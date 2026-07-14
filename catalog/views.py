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
from .filter_params import MAX_FILTER_PRICE, parse_catalog_filters
from .search_images import get_cached_search_image, get_preview_bytes
from .external import get_external_offers
from accounts.notifications import notify


def _filters_for_template(cleaned: dict) -> dict:
    """Значения фильтров для шаблона (строки для сравнения в select/checkbox)."""
    return {
        'q': cleaned['q'],
        'category': cleaned['category'] or '',
        'brand': cleaned['brand'] or '',
        'type': cleaned['type'] or '',
        'condition': cleaned['condition'] or '',
        'make': cleaned['make'] or '',
        'rating': cleaned['rating'] or '',
        'sort': cleaned['sort'],
        'price_min': cleaned['price_min'] if cleaned['price_min'] is not None else '',
        'price_max': cleaned['price_max'] if cleaned['price_max'] is not None else '',
        'in_stock': '1' if cleaned['in_stock'] else '',
        'preorder': '1' if cleaned['preorder'] else '',
        'warranty': '1' if cleaned['warranty'] else '',
        'sale': '1' if cleaned['sale'] else '',
        'photo': '1' if cleaned['photo'] else '',
    }


def _catalog_without(get_params, *keys):
    params = get_params.copy()
    for key in keys:
        params.pop(key, None)
    qs = params.urlencode()
    base = reverse('catalog:index')
    return f'{base}?{qs}' if qs else base


def home(request):
    from listings.models import Listing
    from .recommendations import get_personal_recommendations

    recommended, search_topics = [], []
    if request.user.is_authenticated:
        recommended, search_topics = get_personal_recommendations(request.user)

    listings = Listing.objects.filter(status='active').select_related('category').prefetch_related('images')
    if recommended:
        exclude_ids = [item.pk for item in recommended]
        listings = listings.exclude(pk__in=exclude_ids)
    listings = listings[:12]

    categories = Category.objects.filter(parent__isnull=True, is_active=True).prefetch_related('children')
    return render(request, 'home/index.html', {
        'title': 'Главная — MarketPlace',
        'listings': listings,
        'recommended': recommended,
        'search_topics': search_topics,
        'categories': categories,
    })


def catalog_index(request):
    from listings.models import Listing

    categories_qs = Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related('children')
    brands_qs = Brand.objects.filter(is_active=True).order_by('name')
    car_makes_qs = CarMake.objects.all().order_by('name')

    price_bounds = Listing.objects.filter(status='active').aggregate(
        min_price=Min('price'),
        max_price=Max('price'),
    )
    price_min_default = int(price_bounds.get('min_price') or 0)
    price_max_default = int(price_bounds.get('max_price') or 500000)
    if price_max_default < 10000:
        price_max_default = 500000

    category_ids = {str(pk) for pk in Category.objects.filter(is_active=True).values_list('pk', flat=True)}
    brand_ids = {str(pk) for pk in brands_qs.values_list('pk', flat=True)}
    make_ids = {str(pk) for pk in car_makes_qs.values_list('pk', flat=True)}

    cleaned, filter_errors = parse_catalog_filters(
        request.GET,
        category_ids=category_ids,
        brand_ids=brand_ids,
        make_ids=make_ids,
        price_cap=price_max_default,
    )

    q = cleaned['q']
    sort = cleaned['sort']

    search_valid = True
    search_error = ''
    if q:
        search_valid, search_error = is_valid_search_query(q)

    qs = Listing.objects.filter(status='active').select_related('category', 'brand').prefetch_related('images')
    external_offers = []
    preview_source = None

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

    if cleaned['category']:
        qs = qs.filter(category_id=cleaned['category'])
    if cleaned['brand']:
        qs = qs.filter(brand_id=cleaned['brand'])
    if cleaned['type']:
        qs = qs.filter(type=cleaned['type'])
    if cleaned['price_min'] is not None:
        qs = qs.filter(price__gte=cleaned['price_min'])
    if cleaned['price_max'] is not None:
        qs = qs.filter(price__lte=cleaned['price_max'])
    if cleaned['in_stock']:
        qs = qs.filter(quantity__gt=0)
    if cleaned['warranty']:
        qs = qs.filter(has_warranty=True)
    if cleaned['sale']:
        qs = qs.filter(old_price__isnull=False, old_price__gt=F('price'))
    if cleaned['condition']:
        qs = qs.filter(condition=cleaned['condition'])
    if cleaned['make']:
        qs = qs.filter(car_compat__make_id=cleaned['make'])
    if cleaned['rating']:
        qs = qs.filter(rating_avg__gte=float(cleaned['rating']), rating_count__gt=0)
    if cleaned['photo']:
        qs = qs.filter(images__isnull=False)
    if cleaned['preorder']:
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
    page = paginator.get_page(cleaned['page'])

    active_filters = []
    if q:
        active_filters.append(('q', f'«{q}»'))
    if cleaned['category']:
        cat = Category.objects.filter(pk=cleaned['category']).first()
        if cat:
            active_filters.append(('category', cat.name))
    if cleaned['brand']:
        br = Brand.objects.filter(pk=cleaned['brand']).first()
        if br:
            active_filters.append(('brand', br.name))
    if cleaned['type']:
        active_filters.append(('type', 'Товар' if cleaned['type'] == 'product' else 'Услуга'))
    if cleaned['condition']:
        labels = {'new': 'Новый', 'used': 'Б/У', 'refurbished': 'Восстановленный'}
        active_filters.append(('condition', labels.get(cleaned['condition'], cleaned['condition'])))
    if cleaned['price_min'] is not None:
        active_filters.append(('price_min', f'от {cleaned["price_min"]} ₽'))
    if cleaned['price_max'] is not None:
        active_filters.append(('price_max', f'до {cleaned["price_max"]} ₽'))
    if cleaned['in_stock']:
        active_filters.append(('in_stock', 'В наличии'))
    if cleaned['warranty']:
        active_filters.append(('warranty', 'С гарантией'))
    if cleaned['sale']:
        active_filters.append(('sale', 'Со скидкой'))
    if cleaned['make']:
        mk = CarMake.objects.filter(pk=cleaned['make']).first()
        if mk:
            active_filters.append(('make', mk.name))
    if cleaned['rating']:
        active_filters.append(('rating', f'Рейтинг от {cleaned["rating"]}★'))
    if cleaned['photo']:
        active_filters.append(('photo', 'С фото'))
    if cleaned['preorder']:
        active_filters.append(('preorder', 'Под заказ'))

    filter_remove_urls = {key: _catalog_without(request.GET, key) for key, _ in active_filters}
    template_filters = _filters_for_template(cleaned)

    return render(request, 'catalog/index.html', {
        'title': 'Каталог',
        'listings': page,
        'total': total,
        'categories': categories_qs,
        'brands': brands_qs,
        'car_makes': car_makes_qs,
        'filters': template_filters,
        'active_filters': active_filters,
        'filter_remove_urls': filter_remove_urls,
        'has_active_filters': bool(active_filters),
        'filter_errors': filter_errors,
        'sort': sort,
        'zero_result': bool(q) and search_valid and total == 0,
        'search_invalid': bool(q) and not search_valid,
        'search_error': search_error,
        'show_search_preview': bool(q) and search_valid,
        'preview_source': preview_source,
        'external_offers': external_offers,
        'search_query': q,
        'price_slider_max': price_max_default,
        'price_slider_min': price_min_default,
        'price_filter_max': MAX_FILTER_PRICE,
    })


@require_POST
def search_request_view(request):
    if not request.user.is_authenticated:
        query = request.POST.get('query', '').strip()
        messages.info(request, 'Войдите или зарегистрируйтесь, чтобы оставить заявку «Ищу»')
        login_url = reverse('accounts:login')
        next_path = f'/catalog/?q={query}' if query else '/catalog/'
        return redirect(f'{login_url}?next={next_path}')

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
        user=request.user,
        query=query,
        description=description,
        contact=request.POST.get('contact', ''),
    )
    messages.success(request, 'Заявка на поиск отправлена!')
    return redirect(reverse('accounts:my_requests') + '#my-searches')


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
    return render(request, 'catalog/looking.html', {
        'title': 'Заявки покупателей',
        **looking_board_context(request),
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
