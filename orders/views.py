from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django import forms
from listings.models import Listing
from listings.forms import ReviewForm
from listings.services import user_can_review, update_listing_rating
from accounts.notifications import notify
from accounts.wallet_service import get_wallet, pay_from_wallet, refund_to_wallet
from .models import Cart, CartItem, Order, OrderItem
from .context_processors import get_or_create_cart
from .cart_service import merge_session_cart_into_user


def _cart_json(cart):
    items = []
    for item in cart.items.select_related('listing').all():
        items.append({
            'id': item.pk,
            'listing_id': item.listing_id,
            'title': item.listing.title,
            'quantity': item.quantity,
            'price': float(item.price),
            'subtotal': float(item.subtotal),
            'max_qty': item.listing.quantity,
        })
    return {
        'ok': True,
        'total': float(cart.total()),
        'count': cart.item_count(),
        'items': items,
    }


def _safe_int(value, default=1, min_val=1):
    try:
        return max(min_val, int(value))
    except (TypeError, ValueError):
        return default


def _safe_int_qty(value, default=0, min_val=0):
    try:
        return max(min_val, int(value))
    except (TypeError, ValueError):
        return default


def _order_action_flags(order, user):
    """Какие кнопки и подсказки показать на странице заказа."""
    ship = (
        user == order.seller
        and order.status in (Order.Status.PAID, Order.Status.PROCESSING)
    )
    complete = (
        user == order.buyer
        and order.status in (Order.Status.SHIPPED, Order.Status.DELIVERED)
    )
    seller_wait = user == order.seller and order.status in (
        Order.Status.SHIPPED, Order.Status.DELIVERED,
    )
    buyer_wait = (
        user == order.buyer
        and order.status in (Order.Status.PAID, Order.Status.PROCESSING)
    )
    buyer_pending_pay = user == order.buyer and order.status == Order.Status.PENDING
    seller_pending_pay = user == order.seller and order.status == Order.Status.PENDING
    cancellable = order.status in (
        Order.Status.PENDING, Order.Status.PAID, Order.Status.PROCESSING,
    )
    show_cancel = cancellable and user in (order.buyer, order.seller)
    return {
        'show_ship_btn': ship,
        'show_complete_btn': complete,
        'order_hint_seller_wait': seller_wait,
        'order_hint_buyer_wait': buyer_wait,
        'order_hint_buyer_pending': buyer_pending_pay,
        'order_hint_seller_pending': seller_pending_pay,
        'show_cancel_btn': show_cancel,
    }


def is_own_listing(user, listing) -> bool:
    return user.is_authenticated and listing.user_id == user.id


class CheckoutForm(forms.Form):
    buyer_type = forms.ChoiceField(choices=Order.BuyerType.choices, label='Тип покупателя')
    delivery_type = forms.ChoiceField(choices=Order.DeliveryType.choices, label='Доставка')
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label='Адрес')
    payment_method = forms.ChoiceField(
        choices=[
            ('wallet', 'Кошелёк MarketPlace'),
            ('card', 'Банковская карта'),
            ('yukassa', 'ЮKassa'),
            ('postpay', 'Пост-оплата (B2B)'),
            ('escrow', 'Безопасная сделка'),
        ],
        label='Способ оплаты',
    )


def cart_view(request):
    cart = get_or_create_cart(request)
    if request.user.is_authenticated:
        cart.items.filter(listing__user=request.user).delete()
    items = cart.items.select_related('listing').all()
    return render(request, 'orders/cart.html', {
        'title': 'Корзина',
        'cart': cart,
        'items': items,
        'total': cart.total(),
    })


def cart_add(request):
    if request.method == 'POST':
        listing_id = request.POST.get('listing_id')
        if not listing_id or not str(listing_id).isdigit():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': 'Не указан товар'}, status=400)
            messages.error(request, 'Не указан товар')
            return redirect('cart')
        listing = get_object_or_404(Listing, pk=int(listing_id), status=Listing.Status.ACTIVE)
        if is_own_listing(request.user, listing):
            err = 'Нельзя заказать своё объявление'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': err}, status=400)
            messages.error(request, err)
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('listings:detail', slug=listing.slug)
        qty = _safe_int(request.POST.get('quantity', 1))
        if listing.quantity < qty:
            err = 'Недостаточно товара на складе'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': err}, status=400)
            messages.error(request, err)
        else:
            cart = get_or_create_cart(request)
            item, created = CartItem.objects.get_or_create(
                cart=cart, listing=listing,
                defaults={'quantity': qty, 'price': listing.price}
            )
            if not created:
                item.quantity += qty
                if item.quantity > listing.quantity:
                    err = 'Недостаточно товара'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'ok': False, 'error': err}, status=400)
                    messages.error(request, err)
                    return redirect(request.POST.get('next', 'cart'))
                item.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                data = _cart_json(cart)
                data.update({
                    'title': listing.title,
                    'listing_id': listing.pk,
                    'slug': listing.slug,
                    'message': 'Товар добавлен в корзину',
                })
                return JsonResponse(data)
            messages.success(request, 'Товар добавлен в корзину')
        next_url = request.POST.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('cart')
    return redirect('cart')


def cart_update(request):
    if request.method == 'POST':
        cart = get_or_create_cart(request)
        for key, val in request.POST.items():
            if key.startswith('qty_'):
                item_id = key.replace('qty_', '')
                if not item_id.isdigit():
                    continue
                try:
                    item = cart.items.select_related('listing').get(pk=int(item_id))
                    qty = _safe_int_qty(val, default=0, min_val=0)
                    if qty <= 0:
                        item.delete()
                    elif qty > item.listing.quantity:
                        item.quantity = item.listing.quantity
                        item.save(update_fields=['quantity'])
                        messages.warning(request, f'«{item.listing.title}»: максимум {item.listing.quantity} шт.')
                    else:
                        item.quantity = qty
                        item.save(update_fields=['quantity'])
                except CartItem.DoesNotExist:
                    pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(_cart_json(cart))
    return redirect('cart')


@require_POST
def cart_remove(request, item_id):
    cart = get_or_create_cart(request)
    item = cart.items.filter(pk=item_id).select_related('listing').first()
    if item:
        title = item.listing.title
        item.delete()
        messages.success(request, f'«{title}» удалён из корзины')
    return redirect('cart')


def _restore_order_stock(order):
    for item in order.items.select_related('listing'):
        if not item.listing:
            continue
        listing = item.listing
        listing.quantity += item.quantity
        if listing.status == Listing.Status.OUT_OF_STOCK and listing.quantity > 0:
            listing.status = Listing.Status.ACTIVE
        listing.save(update_fields=['quantity', 'status'])


def _process_payment(request, order, method, total):
    """Обработка оплаты заказа."""
    if method == 'wallet':
        try:
            pay_from_wallet(request.user, total, order=order, description=f'Заказ {order.order_number}')
            order.payment_status = 'paid'
            order.status = Order.Status.PAID
            order.save()
            return True
        except ValueError as e:
            messages.error(request, str(e))
            return False
    elif method in ('card', 'yukassa'):
        order.payment_status = 'paid'
        order.status = Order.Status.PAID
        order.save()
        messages.info(request, 'Оплата картой прошла успешно (демо-режим)')
        return True
    elif method == 'escrow':
        order.payment_status = 'held'
        order.escrow_held = True
        order.status = Order.Status.PAID
        order.save()
        messages.info(request, 'Средства заморожены на счёте безопасной сделки')
        return True
    elif method == 'postpay':
        order.payment_status = 'pending'
        order.status = Order.Status.PENDING
        order.save()
        messages.info(request, 'Счёт отправлен на согласование')
        return True
    return True


@login_required
def checkout_view(request):
    cart = get_or_create_cart(request)

    def _fresh_items():
        return list(cart.items.select_related('listing').all())

    items = _fresh_items()
    if not items:
        messages.error(request, 'Корзина пуста')
        return redirect('cart')
    own_items = [i for i in items if is_own_listing(request.user, i.listing)]
    if own_items:
        for item in own_items:
            item.delete()
        messages.error(request, 'Нельзя заказать своё объявление')
        return redirect('cart')
    wallet = get_wallet(request.user)
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    items = _fresh_items()
                    if not items:
                        raise ValueError('Корзина пуста')
                    seller = items[0].listing.user
                    subtotal = sum(i.subtotal for i in items)
                    method = form.cleaned_data['payment_method']
                    order = Order.objects.create(
                        order_number=Order.generate_number(),
                        buyer=request.user,
                        seller=seller,
                        buyer_type=form.cleaned_data['buyer_type'],
                        subtotal=subtotal,
                        total=subtotal,
                        delivery_type=form.cleaned_data['delivery_type'],
                        delivery_address=form.cleaned_data['delivery_address'],
                        payment_method=method,
                    )
                    for item in items:
                        OrderItem.objects.create(
                            order=order, listing=item.listing,
                            title=item.listing.title, quantity=item.quantity,
                            price=item.price, total=item.subtotal,
                        )
                        listing = item.listing
                        listing.quantity -= item.quantity
                        listing.sales_count += item.quantity
                        if listing.quantity <= 0:
                            listing.status = Listing.Status.OUT_OF_STOCK
                        listing.save()
                    if not _process_payment(request, order, method, subtotal):
                        raise ValueError('Оплата не прошла')
                    cart.items.all().delete()
                addr = form.cleaned_data['delivery_address'].strip()
                if addr and addr != (getattr(request.user, 'delivery_address', '') or ''):
                    request.user.delivery_address = addr
                    request.user.save(update_fields=['delivery_address'])
                notify(
                    seller,
                    'order',
                    f'Новый заказ {order.order_number}',
                    f'Покупатель заказал на {int(subtotal)} ₽. Нажмите «Отправить» после отправки.',
                    f'/orders/{order.pk}/',
                )
                notify(
                    request.user,
                    'order',
                    f'Заказ {order.order_number} оформлен',
                    f'Сумма {int(subtotal)} ₽. Ожидайте отправки продавцом.',
                    f'/orders/{order.pk}/',
                )
                messages.success(request, f'Заказ оформлен! № {order.order_number}')
                return redirect('orders:detail', pk=order.pk)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = CheckoutForm(initial={
            'delivery_address': getattr(request.user, 'delivery_address', '') or '',
        })
    return render(request, 'orders/checkout.html', {
        'title': 'Оформление заказа',
        'items': items,
        'total': sum(i.subtotal for i in items),
        'form': form,
        'wallet': wallet,
    })


@login_required
def order_list(request):
    tab = request.GET.get('tab', 'bought')
    bought_orders = Order.objects.filter(buyer=request.user).select_related('seller').order_by('-created_at')
    sales_orders = Order.objects.filter(seller=request.user).select_related('buyer').order_by('-created_at')
    if tab == 'sales':
        orders = sales_orders
    else:
        orders = bought_orders
        tab = 'bought'
    return render(request, 'orders/list.html', {
        'title': 'Заказы',
        'orders': orders,
        'tab': tab,
        'bought_count': bought_orders.count(),
        'sales_count': sales_orders.count(),
    })


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('buyer', 'seller').prefetch_related('items__listing'),
        pk=pk,
    )
    if order.buyer != request.user and order.seller != request.user and not request.user.is_staff:
        return render(request, 'errors/403.html', {'title': 'Доступ запрещён'}, status=403)

    listing = None
    first_item = order.items.select_related('listing').first()
    if first_item:
        listing = first_item.listing

    can_review = False
    review_block_reason = ''
    review_form = None
    if request.user == order.buyer and order.status == Order.Status.COMPLETED and listing:
        can_review, review_block_reason = user_can_review(request.user, listing)
        if can_review:
            review_form = ReviewForm()

    return render(request, 'orders/detail.html', {
        'title': f'Заказ {order.order_number}',
        'order': order,
        'listing': listing,
        'can_review': can_review,
        'review_block_reason': review_block_reason,
        'review_form': review_form,
        **_order_action_flags(order, request.user),
    })


@login_required
@require_POST
def order_ship(request, pk):
    """Продавец отмечает отправку заказа."""
    order = get_object_or_404(Order, pk=pk, seller=request.user)
    if order.status not in (Order.Status.PAID, Order.Status.PROCESSING):
        messages.error(request, 'Отправить можно только оплаченный заказ')
        return redirect('orders:detail', pk=pk)
    order.status = Order.Status.SHIPPED
    order.save(update_fields=['status'])
    notify(
        order.buyer,
        'order',
        f'Заказ {order.order_number} отправлен',
        'Продавец отправил товар. Когда получите — нажмите «Товар пришёл» в заказе.',
        f'/orders/{order.pk}/',
    )
    messages.success(request, 'Заказ отмечен как отправленный')
    return redirect('orders:detail', pk=pk)


@login_required
@require_POST
def order_complete(request, pk):
    """Покупатель подтверждает получение — заказ завершён, можно оставить отзыв."""
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    if order.status not in (Order.Status.SHIPPED, Order.Status.DELIVERED):
        messages.error(request, 'Подтвердить можно после отправки продавцом')
        return redirect('orders:detail', pk=pk)
    order.status = Order.Status.COMPLETED
    order.save(update_fields=['status'])
    notify(
        order.seller,
        'order',
        f'Заказ {order.order_number} завершён',
        f'Покупатель получил товар. Сумма: {int(order.total)} ₽',
        f'/orders/{order.pk}/',
    )
    messages.success(request, 'Заказ завершён! Теперь можно оставить отзыв продавцу.')
    return redirect('orders:detail', pk=pk)


@login_required
@require_POST
def order_cancel(request, pk):
    """Отмена заказа до отправки — покупателем или продавцом."""
    order = get_object_or_404(Order, pk=pk)
    if request.user not in (order.buyer, order.seller):
        return render(request, 'errors/403.html', {'title': 'Доступ запрещён'}, status=403)
    if order.status not in (Order.Status.PENDING, Order.Status.PAID, Order.Status.PROCESSING):
        messages.error(request, 'Отменить можно только до отправки товара')
        return redirect('orders:detail', pk=pk)
    with transaction.atomic():
        _restore_order_stock(order)
        if order.payment_method == Order.PaymentMethod.WALLET and order.payment_status == 'paid':
            refund_to_wallet(
                order.buyer, order.total, order=order,
                description=f'Возврат за отмену {order.order_number}',
            )
        order.status = Order.Status.CANCELLED
        order.payment_status = 'refunded' if order.payment_method == Order.PaymentMethod.WALLET else 'cancelled'
        order.escrow_held = False
        order.save(update_fields=['status', 'payment_status', 'escrow_held'])
    who = 'Покупатель' if request.user == order.buyer else 'Продавец'
    other = order.seller if request.user == order.buyer else order.buyer
    notify(
        other,
        'order',
        f'Заказ {order.order_number} отменён',
        f'{who} отменил заказ.',
        f'/orders/{order.pk}/',
    )
    messages.success(request, 'Заказ отменён')
    return redirect('orders:detail', pk=pk)
