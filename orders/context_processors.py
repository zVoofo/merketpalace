from .models import Cart


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
