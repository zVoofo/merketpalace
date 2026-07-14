from django.db import models
from django.utils import timezone
from .utils import make_slug


class Listing(models.Model):
    class Type(models.TextChoices):
        PRODUCT = 'product', 'Товар'
        SERVICE = 'service', 'Услуга'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PENDING = 'pending', 'На модерации'
        ACTIVE = 'active', 'Активно'
        REJECTED = 'rejected', 'Отклонено'
        ARCHIVED = 'archived', 'В архиве'
        OUT_OF_STOCK = 'out_of_stock', 'Нет в наличии'
        ON_ORDER = 'on_order', 'Под заказ'

    class Condition(models.TextChoices):
        NEW = 'new', 'Новый'
        USED = 'used', 'Б/У'
        REFURBISHED = 'refurbished', 'Восстановленный'

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='listings')
    category = models.ForeignKey('catalog.Category', on_delete=models.PROTECT)
    brand = models.ForeignKey('catalog.Brand', null=True, blank=True, on_delete=models.SET_NULL)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.PRODUCT)
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=350, unique=True)
    description = models.TextField(blank=True)
    sku = models.CharField('Артикул', max_length=100, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    quantity = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.NEW)
    has_warranty = models.BooleanField(default=False)
    warranty_text = models.CharField(max_length=500, blank=True)
    return_policy = models.TextField(blank=True)
    views_count = models.PositiveIntegerField(default=0)
    chat_clicks = models.PositiveIntegerField(default=0)
    sales_count = models.PositiveIntegerField(default=0)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = make_slug(self.title)
            slug = base
            i = 1
            while Listing.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        if self.old_price and self.old_price > self.price:
            self.discount_pct = int((1 - float(self.price) / float(self.old_price)) * 100)
        super().save(*args, **kwargs)

    @property
    def thumb(self):
        img = self.images.filter(media_type=ListingImage.MediaType.IMAGE).first()
        if not img:
            img = self.images.exclude(media_type=ListingImage.MediaType.VIDEO).first()
        return img.file.url if img else None

    @property
    def in_stock(self):
        return self.quantity > 0


class ListingImage(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'image', 'Фото'
        VIDEO = 'video', 'Видео'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    file = models.FileField(upload_to='listings/')
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.IMAGE)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']


class ListingCarCompat(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='car_compat')
    make = models.ForeignKey('catalog.CarMake', on_delete=models.CASCADE)
    model = models.ForeignKey('catalog.CarModel', null=True, blank=True, on_delete=models.SET_NULL)
    year_from = models.PositiveSmallIntegerField(null=True, blank=True)
    year_to = models.PositiveSmallIntegerField(null=True, blank=True)
    aggregate = models.CharField(max_length=100, blank=True)


class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'На модерации'
        APPROVED = 'approved', 'Одобрен'
        REJECTED = 'rejected', 'Отклонён'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews_written')
    seller = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.PositiveSmallIntegerField()
    text = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    seller_reply = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ModerationQueue(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='moderation')
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Очередь модерации'
        verbose_name_plural = 'Очередь модерации'
