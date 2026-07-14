from django.urls import reverse
from .models import Notification


LINK_ALIASES = {
    '/seller/requests/#offers': lambda: reverse('accounts:my_requests') + '#offers',
    '/seller/requests/': lambda: reverse('accounts:my_requests'),
    '/seller/requests/#sent': lambda: reverse('accounts:my_requests') + '#sent',
    '/accounts/profile/?tab=requests': lambda: reverse('accounts:my_requests'),
    '/accounts/profile/?tab=requests#offers': lambda: reverse('accounts:my_requests') + '#offers',
}


def normalize_notification_link(link: str) -> str:
    link = (link or '').strip()
    if not link or link == '#':
        return reverse('home')
    if link in LINK_ALIASES:
        return LINK_ALIASES[link]()
    if link.startswith('/seller/requests') or link.startswith('/accounts/my-requests'):
        suffix = '#' + link.split('#', 1)[1] if '#' in link else ''
        return reverse('accounts:my_requests') + suffix
    if 'tab=requests' in link:
        suffix = '#' + link.split('#', 1)[1] if '#' in link else ''
        return reverse('accounts:my_requests') + suffix
    if link.startswith('/') and not link.startswith('//'):
        return link
    return reverse('home')


def _trunc(text: str, max_len: int) -> str:
    text = (text or '').strip()
    if len(text) <= max_len:
        return text
    if max_len <= 1:
        return text[:max_len]
    return text[: max_len - 1] + '…'


def notify(user, ntype: str, title: str, body: str = '', link: str = ''):
    if not user or not getattr(user, 'pk', None):
        return
    Notification.objects.create(
        user=user,
        ntype=ntype,
        title=_trunc(title, 255),
        body=_trunc(body, 2000),
        link=normalize_notification_link(link),
    )


def unread_count(user) -> int:
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, is_read=False).count()
