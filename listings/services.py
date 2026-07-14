from django.db.models import Q, Count, Max
from orders.models import Order, OrderItem
from .models import Listing, ListingImage, ModerationQueue, Review, ReviewMedia


COMPLETED_STATUSES = (
    Order.Status.COMPLETED,
    Order.Status.DELIVERED,
)

MAX_MEDIA = 10

from .moderation import schedule_auto_moderation


def remoderate_listing(listing, reason='Обновление объявления'):
    """Повторная отправка на модерацию после редактирования."""
    listing.status = Listing.Status.PENDING
    listing.save(update_fields=['status'])
    ModerationQueue.objects.create(listing=listing, reason=reason)
    schedule_auto_moderation(listing.pk)


def save_listing_media(listing, files):
    start_order = listing.images.count()
    for i, f in enumerate(files):
        from .forms import detect_media_type
        ListingImage.objects.create(
            listing=listing,
            file=f,
            media_type=detect_media_type(f),
            sort_order=start_order + i,
        )


def save_review_media(review, files):
    for i, f in enumerate(files):
        from .forms import detect_media_type
        ReviewMedia.objects.create(
            review=review,
            file=f,
            media_type=detect_media_type(f),
            sort_order=i,
        )


def user_can_review(user, listing) -> tuple[bool, str]:
    if not user.is_authenticated:
        return False, 'Войдите в аккаунт'
    if user == listing.user:
        return False, 'Нельзя оставить отзыв на своё объявление'
    has_order = OrderItem.objects.filter(
        listing=listing,
        order__buyer=user,
        order__status__in=COMPLETED_STATUSES,
    ).exists()
    if not has_order:
        return False, 'Отзыв доступен только после успешной покупки'
    if Review.objects.filter(listing=listing, reviewer=user).exists():
        return False, 'Вы уже оставили отзыв'
    return True, ''


def update_listing_rating(listing):
    from django.db.models import Avg, Count
    agg = listing.reviews.filter(status=Review.Status.APPROVED).aggregate(avg=Avg('rating'), cnt=Count('id'))
    listing.rating_avg = agg['avg'] or 0
    listing.rating_count = agg['cnt'] or 0
    listing.save(update_fields=['rating_avg', 'rating_count'])


def get_seller_rating(user):
    from django.db.models import Avg, Count
    agg = Review.objects.filter(
        seller=user, status=Review.Status.APPROVED,
    ).aggregate(avg=Avg('rating'), cnt=Count('id'))
    return agg['avg'], agg['cnt'] or 0


# Сопутствующие запчасти: что обычно покупают вместе с этой деталью
_PART_GROUPS = (
    (('колодк', 'колодки'), ('диск', 'тормозн', 'суппорт', 'жидкост', 'колодк')),
    (('фильтр',), ('масл', 'маслян', 'фильтр')),
    (('свеч',), ('катуш', 'провод', 'зажиган', 'свеч')),
    (('амортизатор', 'стойк'), ('опор', 'пружин', 'пыльник', 'амортизатор')),
    (('ремень', 'грм'), ('ролик', 'натяж', 'помп', 'ремень')),
    (('аккумулятор', 'акб'), ('клемм', 'провод', 'заряд')),
    (('шин', 'покрыш'), ('диск', 'колпак', 'датчик')),
)


def _title_matches(title: str, keywords: tuple[str, ...]) -> bool:
    t = title.lower()
    return any(kw in t for kw in keywords)


def _keyword_complements(listing, limit: int):
    title = listing.title
    related_keywords = []
    for triggers, companions in _PART_GROUPS:
        if _title_matches(title, triggers):
            related_keywords.extend(companions)
    if not related_keywords:
        return []

    seen = {listing.pk}
    results = []
    candidates = Listing.objects.filter(
        status=Listing.Status.ACTIVE,
    ).exclude(pk=listing.pk).prefetch_related('images', 'car_compat')

    for item in candidates:
        if item.pk in seen:
            continue
        if not _title_matches(item.title, tuple(related_keywords)):
            continue
        if listing.brand_id and item.brand_id == listing.brand_id:
            score = 3
        elif listing.category_id == item.category_id:
            score = 2
        else:
            score = 1
        results.append((score, item))
        seen.add(item.pk)

    results.sort(key=lambda x: (-x[0], -x[1].sales_count, -float(x[1].rating_avg or 0)))
    return [item for _, item in results[:limit]]


def get_complementary_listings(listing, limit: int = 6):
    """Сопутствующие товары: co-purchase + правила для запчастей + совместимость по авто."""
    seen = {listing.pk}
    scored = []

    order_ids = OrderItem.objects.filter(
        listing=listing,
        order__status__in=COMPLETED_STATUSES,
    ).values_list('order_id', flat=True).distinct()

    if order_ids:
        bought_together = (
            OrderItem.objects.filter(order_id__in=order_ids)
            .exclude(listing_id=listing.pk)
            .values('listing_id')
            .annotate(freq=Count('id'))
            .order_by('-freq')[:limit * 2]
        )
        ids = [row['listing_id'] for row in bought_together]
        for item in Listing.objects.filter(
            pk__in=ids, status=Listing.Status.ACTIVE,
        ).prefetch_related('images'):
            if item.pk not in seen:
                scored.append((100, item))
                seen.add(item.pk)

    for item in _keyword_complements(listing, limit):
        if item.pk not in seen:
            scored.append((50, item))
            seen.add(item.pk)

    make_ids = list(listing.car_compat.values_list('make_id', flat=True))
    if make_ids and len(scored) < limit:
        for item in Listing.objects.filter(
            status=Listing.Status.ACTIVE,
            car_compat__make_id__in=make_ids,
        ).exclude(pk__in=seen).prefetch_related('images').distinct()[:limit]:
            scored.append((30, item))
            seen.add(item.pk)

    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:limit]]
