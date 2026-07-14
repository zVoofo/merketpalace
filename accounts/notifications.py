from .models import Notification


def notify(user, ntype: str, title: str, body: str = '', link: str = ''):
    if not user or not getattr(user, 'pk', None):
        return
    Notification.objects.create(
        user=user,
        ntype=ntype,
        title=title,
        body=body,
        link=link,
    )


def unread_count(user) -> int:
    if not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, is_read=False).count()
