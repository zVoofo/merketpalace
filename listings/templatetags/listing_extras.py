from django import template
from django.templatetags.static import static

register = template.Library()

PLACEHOLDER = 'img/no-photo.svg'


@register.simple_tag
def listing_image_url(listing):
    img = listing.images.filter(media_type='image').first()
    if img and img.file:
        return img.file.url
    return static(PLACEHOLDER)


@register.filter
def media_is_video(media):
    return getattr(media, 'media_type', 'image') == 'video'
