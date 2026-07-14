from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from listings.models import Listing
from orders.models import Order, CartItem
from accounts.models import WalletTransaction


class Command(BaseCommand):
    help = 'Удаляет заказы и позиции корзины, где покупатель = продавец'

    @transaction.atomic
    def handle(self, *args, **options):
        self_orders = Order.objects.filter(buyer_id=F('seller_id'))
        count = self_orders.count()

        for order in self_orders.prefetch_related('items__listing'):
            for item in order.items.all():
                listing = item.listing
                listing.quantity += item.quantity
                listing.sales_count = max(0, listing.sales_count - item.quantity)
                if listing.status == Listing.Status.OUT_OF_STOCK and listing.quantity > 0:
                    listing.status = listing.Status.ACTIVE
                listing.save(update_fields=['quantity', 'sales_count', 'status'])

            for tx in WalletTransaction.objects.filter(order=order, tx_type='payment'):
                wallet = tx.wallet
                wallet.balance += tx.amount
                wallet.save(update_fields=['balance'])
                tx.delete()

            order.delete()

        cart_removed, _ = CartItem.objects.filter(
            cart__user_id=F('listing__user_id'),
        ).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Удалено самозаказов: {count}, позиций из корзин: {cart_removed}',
        ))
