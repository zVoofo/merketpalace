from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django import forms
from listings.models import Listing
from accounts.wallet_service import get_wallet, pay_from_wallet
from .models import Cart, CartItem, Order, OrderItem
from .context_processors import get_or_create_cart


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
        removed = cart.items.filter(listing__user=request.user).delete()[0]
        if removed:
            messages.info(request, 'Свои объявления нельзя заказать — убрали из корзины')
    items = cart.items.select_related('listing').all()
    return render(request, 'orders/cart.html', {
        'title': 'Корзина',
        'cart': cart,
        'items': items,
        'total': cart.total(),
    })


def cart_add(request):
    if request.method == 'POST':
        listing = get_object_or_404(Listing, pk=request.POST.get('listing_id'), status=Listing.Status.ACTIVE)
        if is_own_listing(request.user, listing):
            messages.error(request, 'Нельзя заказать своё объявление')
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('listings:detail', slug=listing.slug)
        qty = max(1, int(request.POST.get('quantity', 1)))
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
    order = get_object_or_404(Order, pk=pk)
    if order.buyer != request.user and order.seller != request.user and not request.user.is_staff:
        return render(request, 'errors/403.html', {'title': 'Доступ запрещён'}, status=403)
    return render(request, 'orders/detail.html', {'title': f'Заказ {order.order_number}', 'order': order})
