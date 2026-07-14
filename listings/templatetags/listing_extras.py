from django import template
from django.templatetags.static import static

register = template.Library()

PLACEHOLDER = 'img/no-photo.svg'


@register.simple_tag
def listing_image_url(listing):
    thumb = listing.thumb
    if thumb:
        return thumb
    return static(PLACEHOLDER)


@register.filter
def media_is_video(media):
    return getattr(media, 'media_type', 'image') == 'video'
