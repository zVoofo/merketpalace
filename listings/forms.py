from django import forms

from catalog.models import CarMake, CarModel
from catalog.validators import is_valid_listing_text
from .models import Listing, Review, ListingCarCompat

MAX_MEDIA = 10
MIN_MEDIA = 1
MAX_REVIEW_MEDIA = 5
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/webm', 'video/quicktime'}


LISTING_LABELS = {
    'type': 'Тип объявления',
    'title': 'Название',
    'category': 'Категория',
    'brand': 'Бренд',
    'condition': 'Состояние',
    'description': 'Описание',
    'sku': 'Артикул (SKU)',
    'price': 'Цена, ₽',
    'old_price': 'Старая цена, ₽',
    'quantity': 'Количество на складе',
    'has_warranty': 'Есть гарантия',
    'warranty_text': 'Условия гарантии',
    'return_policy': 'Условия возврата',
}


class ListingForm(forms.ModelForm):
    AVAILABILITY_CHOICES = (
        ('stock', 'В наличии'),
        ('preorder', 'Под заказ'),
    )

    availability = forms.ChoiceField(
        choices=AVAILABILITY_CHOICES,
        label='Наличие',
        widget=forms.RadioSelect,
        initial='stock',
    )
    car_make = forms.ModelChoiceField(
        queryset=CarMake.objects.order_by('name'),
        required=False,
        label='Марка авто',
        empty_label='— не указана —',
    )
    car_model = forms.ModelChoiceField(
        queryset=CarModel.objects.select_related('make').order_by('make__name', 'name'),
        required=False,
        label='Модель авто',
        empty_label='— любая модель —',
    )
    year_from = forms.IntegerField(
        required=False,
        min_value=1980,
        max_value=2030,
        label='Год выпуска от',
        widget=forms.NumberInput(attrs={'placeholder': '2015'}),
    )
    year_to = forms.IntegerField(
        required=False,
        min_value=1980,
        max_value=2030,
        label='Год выпуска до',
        widget=forms.NumberInput(attrs={'placeholder': '2020'}),
    )

    class Meta:
        model = Listing
        fields = (
            'type', 'title', 'category', 'brand', 'condition', 'description',
            'sku', 'price', 'old_price', 'quantity',
            'has_warranty', 'warranty_text', 'return_policy',
        )
        labels = LISTING_LABELS
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Подробное описание товара...'}),
            'return_policy': forms.Textarea(attrs={'rows': 2}),
            'title': forms.TextInput(attrs={'placeholder': 'Например: Тормозные колодки BMW X5'}),
            'brand': forms.Select(),
            'category': forms.Select(),
            'condition': forms.Select(),
            'old_price': forms.NumberInput(attrs={'placeholder': 'Для отображения скидки в каталоге'}),
            'warranty_text': forms.TextInput(attrs={'placeholder': 'Например: 12 месяцев от производителя'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['brand'].required = False
        self.fields['brand'].empty_label = '— не выбран —'
        self.fields['old_price'].required = False
        self.fields['sku'].required = False
        self.fields['warranty_text'].required = False
        self.fields['return_policy'].required = False
        self.fields['quantity'].widget.attrs.setdefault('min', 0)

        if self.instance and self.instance.pk:
            compat = self.instance.car_compat.select_related('make', 'model').first()
            if compat:
                self.fields['car_make'].initial = compat.make_id
                self.fields['car_model'].initial = compat.model_id
                self.fields['year_from'].initial = compat.year_from
                self.fields['year_to'].initial = compat.year_to
            self.fields['availability'].initial = (
                'preorder' if self.instance.quantity == 0 else 'stock'
            )

    def clean(self):
        cleaned = super().clean()
        availability = cleaned.get('availability')
        quantity = cleaned.get('quantity')
        year_from = cleaned.get('year_from')
        year_to = cleaned.get('year_to')

        if availability == 'preorder':
            cleaned['quantity'] = 0
        elif quantity is None or quantity <= 0:
            self.add_error('quantity', 'Укажите количество или выберите «Под заказ»')

        if year_from and year_to and year_from > year_to:
            self.add_error('year_to', 'Год «до» не может быть меньше года «от»')

        car_make = cleaned.get('car_make')
        car_model = cleaned.get('car_model')
        if car_model and car_make and car_model.make_id != car_make.pk:
            self.add_error('car_model', 'Модель не соответствует выбранной марке')

        if cleaned.get('has_warranty') and not (cleaned.get('warranty_text') or '').strip():
            self.add_error('warranty_text', 'Укажите условия гарантии')

        return cleaned

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        valid, err = is_valid_listing_text(title, min_length=3)
        if not valid:
            raise forms.ValidationError(err)
        return title

    def clean_description(self):
        desc = (self.cleaned_data.get('description') or '').strip()
        if desc and len(desc) > 25:
            valid, err = is_valid_listing_text(desc[:500], min_length=10)
            if not valid:
                raise forms.ValidationError(err)
        return desc

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError('Цена должна быть больше 0')
        return price

    def save_car_compat(self, listing):
        listing.car_compat.all().delete()
        make = self.cleaned_data.get('car_make')
        if not make:
            return
        ListingCarCompat.objects.create(
            listing=listing,
            make=make,
            model=self.cleaned_data.get('car_model'),
            year_from=self.cleaned_data.get('year_from'),
            year_to=self.cleaned_data.get('year_to'),
        )


def detect_media_type(uploaded_file) -> str:
    ct = getattr(uploaded_file, 'content_type', '') or ''
    name = (uploaded_file.name or '').lower()
    if ct in ALLOWED_VIDEO_TYPES or name.endswith(('.mp4', '.webm', '.mov')):
        return 'video'
    return 'image'


def validate_media_files(files, existing_count: int = 0, require_min: bool = True, max_count: int = MAX_MEDIA):
    errors = []
    total = existing_count + len(files)
    min_required = MIN_MEDIA if require_min else 0
    if require_min and total < min_required:
        errors.append(f'Добавьте от {MIN_MEDIA} до {max_count} фото или видео')
    if total > max_count:
        errors.append(f'Максимум {max_count} файлов (сейчас будет {total})')
    for f in files:
        mt = detect_media_type(f)
        ct = getattr(f, 'content_type', '') or ''
        if mt == 'video' and ct not in ALLOWED_VIDEO_TYPES and not f.name.lower().endswith(('.mp4', '.webm', '.mov')):
            errors.append(f'Видео «{f.name}»: допустимы MP4, WebM, MOV')
        elif mt == 'image' and ct not in ALLOWED_IMAGE_TYPES and not f.name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            errors.append(f'Фото «{f.name}»: допустимы JPG, PNG, WebP, GIF')
        if f.size > 50 * 1024 * 1024:
            errors.append(f'Файл «{f.name}» слишком большой (макс. 50 МБ)')
    return errors


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'text')
        labels = {'rating': 'Оценка', 'text': 'Текст отзыва'}
        widgets = {
            'rating': forms.Select(choices=[(i, f'{i} звёзд') for i in range(5, 0, -1)]),
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Расскажите о товаре...'}),
        }
