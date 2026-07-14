import uuid
from django.db import models
from django.conf import settings


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name='cart')
    session_key = models.CharField(max_length=64, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total(self):
        return sum(item.subtotal for item in self.items.all())

    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    listing = models.ForeignKey('listings.Listing', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('cart', 'listing')

    @property
    def subtotal(self):
        return self.price * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        PAID = 'paid', 'Оплачен'
        PROCESSING = 'processing', 'В обработке'
        SHIPPED = 'shipped', 'Отправлен'
        DELIVERED = 'delivered', 'Доставлен'
        COMPLETED = 'completed', 'Завершён'
        CANCELLED = 'cancelled', 'Отменён'

    class BuyerType(models.TextChoices):
        INDIVIDUAL = 'individual', 'Физлицо'
        ORGANIZATION = 'organization', 'Юрлицо'

    class DeliveryType(models.TextChoices):
        COURIER = 'courier', 'Курьер'
        PICKUP = 'pickup', 'Самовывоз'
        TRANSPORT = 'transport', 'ТК'
        SERVICE = 'service_location', 'Место услуги'

    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'Карта'
        WALLET = 'wallet', 'Кошелёк'
        POSTPAY = 'postpay', 'Пост-оплата'
        ESCROW = 'escrow', 'Безопасная сделка'

    order_number = models.CharField(max_length=20, unique=True)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_received')
    buyer_type = models.CharField(max_length=20, choices=BuyerType.choices, default=BuyerType.INDIVIDUAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_type = models.CharField(max_length=20, choices=DeliveryType.choices, blank=True)
    delivery_address = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    payment_status = models.CharField(max_length=20, default='pending')
    escrow_held = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def generate_number():
        return f'ORD-{uuid.uuid4().hex[:8].upper()}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    listing = models.ForeignKey('listings.Listing', on_delete=models.PROTECT)
    title = models.CharField(max_length=300)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
