from django import forms
from .models import Listing, Review

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
    class Meta:
        model = Listing
        fields = (
            'type', 'title', 'category', 'brand', 'description',
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['brand'].required = False
        self.fields['brand'].empty_label = '— не выбран —'
        self.fields['old_price'].required = False
        self.fields['sku'].required = False
        self.fields['warranty_text'].required = False
        self.fields['return_policy'].required = False

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError('Цена должна быть больше 0')
        return price


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
