from django import template
from django.templatetags.static import static

register = template.Library()

PLACEHOLDER = 'img/no-photo.svg'


@register.simple_tag
def listing_image_url(listing):
    if not listing:
        return static(PLACEHOLDER)
    img = listing.images.filter(media_type='image').first()
    if img and img.file:
        try:
            return img.file.url
        except Exception:
            return static(PLACEHOLDER)
    return static(PLACEHOLDER)


@register.filter
def dict_get(d, key):
    if not d:
        return ''
    return d.get(key, '')


@register.filter
def media_is_video(media):
    return getattr(media, 'media_type', 'image') == 'video'
