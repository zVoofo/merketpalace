import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class ActiveRole(models.TextChoices):
        BUYER = 'buyer', 'Покупатель'
        SELLER = 'seller', 'Продавец'

    phone = models.CharField('Телефон', max_length=20, blank=True, null=True, unique=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True, null=True)
    active_role = models.CharField(
        'Активная роль', max_length=10,
        choices=ActiveRole.choices, default=ActiveRole.BUYER
    )
    is_verified = models.BooleanField('Верифицирован', default=False)
    email_verified = models.BooleanField('Email подтверждён', default=False)
    phone_verified = models.BooleanField('Телефон подтверждён', default=False)
    delivery_address = models.TextField('Адрес доставки', blank=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.username

    @property
    def is_seller(self):
        return self.active_role == self.ActiveRole.SELLER

    @property
    def wallet_balance(self):
        wallet, _ = Wallet.objects.get_or_create(user=self)
        return wallet.balance


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField('Баланс', max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Кошелёк'
        verbose_name_plural = 'Кошельки'

    def __str__(self):
        return f'{self.user.username}: {self.balance} ₽'


class WalletTransaction(models.Model):
    class TxType(models.TextChoices):
        DEPOSIT = 'deposit', 'Пополнение'
        PAYMENT = 'payment', 'Оплата'
        REFUND = 'refund', 'Возврат'
        ESCROW = 'escrow', 'Эскроу'

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tx_type = models.CharField(max_length=20, choices=TxType.choices)
    description = models.CharField(max_length=255, blank=True)
    order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SocialAccount(models.Model):
    class Provider(models.TextChoices):
        VK = 'vk', 'VK'
        GOOGLE = 'google', 'Google'
        APPLE = 'apple', 'Apple'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('provider', 'provider_id')


class Organization(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='organization')
    name = models.CharField('Название', max_length=255, blank=True)
    inn = models.CharField('ИНН', max_length=12, blank=True)
    ogrn = models.CharField('ОГРН', max_length=15, blank=True)
    kpp = models.CharField('КПП', max_length=9, blank=True)
    legal_address = models.TextField('Юр. адрес', blank=True)
    logo = models.ImageField('Логотип', upload_to='org_logos/', blank=True, null=True)
    is_verified = models.BooleanField('Верифицирована', default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'

    def __str__(self):
        return self.name


class SmsCode(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, default='login')
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class EmailVerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_codes')
    email = models.EmailField()
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    entity = models.CharField(max_length=50, blank=True)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    meta = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    class Type(models.TextChoices):
        MESSAGE = 'message', 'Сообщение'
        SEARCH_OFFER = 'search_offer', 'Отклик «Ищу»'
        ORDER = 'order', 'Заказ'
        SYSTEM = 'system', 'Система'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    ntype = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'


class StoredFile(models.Model):
    """Файл в базе данных (фото, видео, документы)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, default='application/octet-stream')
    size = models.PositiveIntegerField(default=0)
    data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Файл в БД'
        verbose_name_plural = 'Файлы в БД'
