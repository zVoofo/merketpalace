from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django import forms
from listings.models import Listing
from listings.forms import ReviewForm
from listings.services import user_can_review, update_listing_rating
from accounts.notifications import notify
from accounts.wallet_service import get_wallet, pay_from_wallet
from .models import Cart, CartItem, Order, OrderItem
from .context_processors import get_or_create_cart


def _safe_int(value, default=1, min_val=1):
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
    return {
        'show_ship_btn': ship,
        'show_complete_btn': complete,
        'order_hint_seller_wait': seller_wait,
        'order_hint_buyer_wait': buyer_wait,
        'order_hint_buyer_pending': buyer_pending_pay,
        'order_hint_seller_pending': seller_pending_pay,
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
            messages.error(request, 'Не указан товар')
            return redirect('cart')
        listing = get_object_or_404(Listing, pk=int(listing_id), status=Listing.Status.ACTIVE)
        if is_own_listing(request.user, listing):
            messages.error(request, 'Нельзя заказать своё объявление')
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('listings:detail', slug=listing.slug)
        qty = _safe_int(request.POST.get('quantity', 1))
        if listing.quantity < qty:
            messages.error(request, 'Недостаточно товара на складе')
        else:
            cart = get_or_create_cart(request)
            item, created = CartItem.objects.get_or_create(
                cart=cart, listing=listing,
                defaults={'quantity': qty, 'price': listing.price}
            )
            if not created:
                item.quantity += qty
                if item.quantity > listing.quantity:
                    messages.error(request, 'Недостаточно товара')
                    return redirect(request.POST.get('next', 'cart'))
                item.save()
            messages.success(request, 'Товар добавлен в корзину')
        return redirect(request.POST.get('next', 'cart'))
    return redirect('cart')


def cart_update(request):
    if request.method == 'POST':
        cart = get_or_create_cart(request)
        for key, val in request.POST.items():
            if key.startswith('qty_'):
                item_id = key.replace('qty_', '')
                try:
                    item = cart.items.get(pk=item_id)
                    qty = int(val)
                    if qty <= 0:
                        item.delete()
                    else:
                        item.quantity = qty
                        item.save()
                except (CartItem.DoesNotExist, ValueError):
                    pass
    return redirect('cart')


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
    items = cart.items.select_related('listing').all()
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
                    seller = items[0].listing.user
                    subtotal = cart.total()
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
                notify(
                    seller,
                    'order',
                    f'Новый заказ {order.order_number}',
                    f'Сумма {int(subtotal)} ₽. Откройте заказ и нажмите «Отправить» после отправки товара.',
                    f'/orders/{order.pk}/',
                )
                messages.success(request, f'Заказ оформлен! № {order.order_number}')
                return redirect('orders:detail', pk=order.pk)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = CheckoutForm()
    return render(request, 'orders/checkout.html', {
        'title': 'Оформление заказа',
        'items': items,
        'total': cart.total(),
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
