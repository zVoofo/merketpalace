import re

from django.db.models import Count, Q

from catalog.models import SearchQuery


def _topic_words(topic: str) -> list[str]:
    return [w for w in re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9\-]+', (topic or '').lower()) if len(w) >= 3]


def get_frequent_search_topics(user, *, limit: int = 5, min_count: int = 1) -> list[str]:
    """Темы, которые пользователь искал чаще всего."""
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_authenticated:
        return []

    rows = (
        SearchQuery.objects.filter(user=user)
        .values('query')
        .annotate(cnt=Count('id'))
        .filter(cnt__gte=min_count)
        .order_by('-cnt', '-query')[:limit]
    )
    return [r['query'].strip() for r in rows if (r['query'] or '').strip()]


def get_personal_recommendations(user, *, limit: int = 8) -> tuple[list, list[str]]:
    """Подборка объявлений по истории поиска пользователя."""
    from listings.models import Listing

    topics = get_frequent_search_topics(user)
    if not topics:
        return [], []

    seen: set[int] = set()
    picked: list = []

    for topic in topics:
        words = _topic_words(topic)
        if not words:
            continue

        clause = Q()
        for word in words[:6]:
            clause |= (
                Q(title__icontains=word)
                | Q(description__icontains=word)
                | Q(sku__icontains=word)
                | Q(brand__name__icontains=word)
                | Q(category__name__icontains=word)
            )

        candidates = (
            Listing.objects.filter(status=Listing.Status.ACTIVE)
            .filter(clause)
            .select_related('category', 'brand')
            .prefetch_related('images')
            .order_by('-views_count', '-rating_avg', '-published_at')
        )

        for listing in candidates[:6]:
            if listing.pk in seen:
                continue
            seen.add(listing.pk)
            picked.append(listing)
            if len(picked) >= limit:
                return picked, topics

    return picked, topics
