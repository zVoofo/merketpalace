"""Слияние гостевой корзины с корзиной пользователя при входе."""
from .models import Cart, CartItem


def merge_session_cart_into_user(request, user) -> int:
    """Переносит товары из session-корзины в user-корзину. Возвращает число перенесённых позиций."""
    session_key = request.session.session_key
    if not session_key:
        return 0

    session_cart = Cart.objects.filter(session_key=session_key, user=None).first()
    if not session_cart or not session_cart.items.exists():
        return 0

    user_cart, _ = Cart.objects.get_or_create(user=user)
    merged = 0

    for item in session_cart.items.select_related('listing').all():
        listing = item.listing
        if not listing or listing.status != 'active':
            continue
        if listing.user_id == user.id:
            continue
        qty = min(item.quantity, max(listing.quantity, 0))
        if qty <= 0:
            continue
        existing = CartItem.objects.filter(cart=user_cart, listing=listing).first()
        if existing:
            new_qty = min(existing.quantity + qty, listing.quantity)
            if new_qty != existing.quantity:
                existing.quantity = new_qty
                existing.save(update_fields=['quantity'])
            merged += 1
        else:
            CartItem.objects.create(
                cart=user_cart,
                listing=listing,
                quantity=qty,
                price=listing.price,
            )
            merged += 1

    session_cart.items.all().delete()
    session_cart.delete()
    return merged
