import re
import threading

from django.utils import timezone

from catalog.validators import is_valid_search_query

PROHIBITED_PATTERNS = [
    r'наркот', r'героин', r'кокаин', r'марихуан', r'мефедрон',
    r'оружи[ея]', r'пистолет', r'взрывчат',
    r'казино', r'ставк[иа]', r'лохотрон', r'скам', r'мошенн',
    r'порно', r'xxx', r'18\+',
    r'обнал', r'отмыв',
]

SCAM_PATTERNS = [
    r'перевед[иь]\s+на\s+карт',
    r'только\s+предоплат',
    r'без\s+встреч',
    r'telegram\s*@',
    r'whatsapp\s*\+',
]


def _check_text(text: str) -> tuple[bool, str]:
    low = (text or '').lower()
    for pat in PROHIBITED_PATTERNS:
        if re.search(pat, low):
            return False, 'Объявление содержит запрещённый товар или услугу'
    for pat in SCAM_PATTERNS:
        if re.search(pat, low):
            return False, 'Подозрение на мошенничество — уточните описание'
    return True, ''


def check_listing(listing) -> tuple[bool, str]:
    if not listing.title or len(listing.title.strip()) < 5:
        return False, 'Слишком короткое название'
    valid, err = is_valid_search_query(listing.title)
    if not valid:
        return False, f'Название: {err}'
    if listing.description:
        valid, err = is_valid_search_query(listing.description[:200])
        if not valid and len(listing.description) > 20:
            return False, f'Описание: {err}'
    ok, reason = _check_text(listing.title)
    if not ok:
        return False, reason
    ok, reason = _check_text(listing.description)
    if not ok:
        return False, reason
    if listing.price <= 0:
        return False, 'Некорректная цена'
    if listing.price > 50_000_000:
        return False, 'Подозрительно высокая цена'
    if not listing.images.exists():
        return False, 'Нужно хотя бы одно фото или видео'
    return True, ''


def moderate_listing(listing_id: int):
    from .models import Listing, ModerationQueue

    try:
        listing = Listing.objects.prefetch_related('images').get(pk=listing_id)
    except Listing.DoesNotExist:
        return

    queue = ModerationQueue.objects.filter(listing=listing, status='pending').order_by('-created_at').first()
    if not queue:
        return

    if listing.status != Listing.Status.PENDING:
        return

    ok, reason = check_listing(listing)
    if ok:
        listing.status = Listing.Status.ACTIVE
        listing.published_at = timezone.now()
        listing.save(update_fields=['status', 'published_at'])
        queue.status = 'approved'
        queue.reason = 'Автоматическая проверка пройдена'
    else:
        listing.status = Listing.Status.REJECTED
        listing.save(update_fields=['status'])
        queue.status = 'rejected'
        queue.reason = reason
    queue.save(update_fields=['status', 'reason'])


def schedule_auto_moderation(listing_id: int, delay: float = 30.0):
    timer = threading.Timer(delay, moderate_listing, args=[listing_id])
    timer.daemon = True
    timer.start()
