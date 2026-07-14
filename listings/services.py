from django.db.models import Q, Count, Max
from orders.models import Order, OrderItem
from .models import Listing, ListingImage, ModerationQueue, Review


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
