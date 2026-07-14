from django.db.models import Q
from accounts.notifications import unread_count
from chat.models import Conversation, Message
from orders.models import Cart


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


def cart_count(request):
    try:
        cart = get_or_create_cart(request)
        return {'cart_count': cart.item_count()}
    except Exception:
        return {'cart_count': 0}


def site_notifications(request):
    if not request.user.is_authenticated:
        return {'notification_count': 0, 'chat_unread_count': 0}
    try:
        chat_unread = Message.objects.filter(
            conversation__in=Conversation.objects.filter(
                Q(buyer=request.user) | Q(seller=request.user),
            ),
            is_read=False,
            is_deleted=False,
        ).exclude(sender=request.user).count()
        return {
            'notification_count': unread_count(request.user),
            'chat_unread_count': chat_unread,
        }
    except Exception:
        return {'notification_count': 0, 'chat_unread_count': 0}
