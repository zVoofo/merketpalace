from django.db import models


class Category(models.Model):
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    slug = models.SlugField(unique=True, max_length=150)
    name = models.CharField('Название', max_length=255)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True, max_length=150)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
        ordering = ['name']

    def __str__(self):
        return self.name


class Attribute(models.Model):
    class AttrType(models.TextChoices):
        TEXT = 'text', 'Текст'
        NUMBER = 'number', 'Число'
        SELECT = 'select', 'Выбор'
        BOOLEAN = 'boolean', 'Да/Нет'
        COLOR = 'color', 'Цвет'

    code = models.SlugField(unique=True, max_length=50)
    name = models.CharField(max_length=150)
    attr_type = models.CharField(max_length=20, choices=AttrType.choices, default=AttrType.TEXT)
    unit = models.CharField(max_length=20, blank=True)
    is_filterable = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CarMake(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Марка авто'
        verbose_name_plural = 'Марки авто'

    def __str__(self):
        return self.name


class CarModel(models.Model):
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('make', 'name')
        verbose_name = 'Модель авто'
        verbose_name_plural = 'Модели авто'

    def __str__(self):
        return f'{self.make.name} {self.name}'


class SearchQuery(models.Model):
    user = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL)
    query = models.CharField(max_length=500)
    results_count = models.IntegerField(default=0)
    filters = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Поисковый запрос'
        verbose_name_plural = 'Поисковые запросы'


class SearchRequest(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        IN_PROGRESS = 'in_progress', 'В работе'
        FOUND = 'found', 'Найдено'
        CLOSED = 'closed', 'Закрыта'

    user = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL)
    query = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    contact = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    matched_listing = models.ForeignKey(
        'listings.Listing', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='search_requests',
    )
    matched_seller = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='search_offers_sent',
    )
    response_seen = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Заявка на поиск'
        verbose_name_plural = 'Заявки на поиск'
