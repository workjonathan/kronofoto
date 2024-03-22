from django import template
from django.core.signing import Signer
from ..reverse import reverse
import markdown as md
from .urlify import URLifyExtension
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.cache import cache
from ..models import Photo, Card
from ..imageutil import ImageSigner
from typing import Union, Dict, Any
from django.template.defaultfilters import linebreaksbr, linebreaks_filter


register = template.Library()

@register.inclusion_tag('archive/components/card.html', takes_context=False)
def card_tag(card: Card, zindex: int) -> Union[Card, Dict[str, Any]]:
    if hasattr(card, 'photocard'):
        if hasattr(card.photocard, 'doublephotocard'):
            card = card.photocard.doublephotocard
            obj = {
                'zindex': zindex,
                'description': card.description,
                'description2': card.description2,
                'photo': card.photo,
                'photo2': card.photo2,
                'template': 'archive/components/two-image-card.html',
            }
            return obj
        else:
            card = card.photocard
            if card.card_style == 0:
                obj = {
                    'zindex': zindex,
                    'image_area_classes': ['full-image-area--contain'], # shrink
                    'description': linebreaks_filter(card.description),
                    'photo': card.photo,
                    'template': 'archive/components/full-image-card.html',
                }
                return obj
            elif card.card_style in (5, 7, 8):
                obj = {
                    'zindex': zindex,
                    'image_area_classes': [], # warp
                    'description': linebreaksbr(card.description),
                    'photo': card.photo,
                    'template': 'archive/components/full-image-card.html',
                }
                return obj
            elif card.card_style in (1,): # area classes represent left/right and slide/reveal animation
                obj = {
                    'zindex': zindex,
                    'image_area_classes': ['two-column--image-left', 'two-column--variation-1'],
                    'description': card.description,
                    'photo': card.photo,
                    'template': 'archive/components/two-column-card.html',
                }
                return obj
            elif card.card_style in (3,):
                obj = {
                    'zindex': zindex,
                    'image_area_classes': ['two-column--image-left', 'two-column--variation-3'],
                    'description': card.description,
                    'photo': card.photo,
                    'template': 'archive/components/two-column-card.html',
                }
                return obj
            elif card.card_style in (4,):
                obj = {
                    'zindex': zindex,
                    'image_area_classes': ['two-column--image-right', 'two-column--variation-4'],
                    'description': card.description,
                    'photo': card.photo,
                    'template': 'archive/components/two-column-card.html',
                }
                return obj
            elif card.card_style in (2,):
                obj = {
                    'zindex': zindex,
                    'image_area_classes': ['two-column--image-right', 'two-column--variation-2'],
                    'description': card.description,
                    'photo': card.photo,
                    'template': 'archive/components/two-column-card.html',
                }
                return obj
            elif card.card_style in (6,):
                obj = {
                    'zindex': zindex,
                    'description': card.description,
                    'photo': card.photo,
                    'template': 'archive/components/figure-card.html',

                }
                return obj
    else:
        if card.card_style == 0:
            return {
                'zindex': zindex,
                'content_attrs': {
                    'data-aos': 'fade-up',
                    'data-aos-duration': '1000',
                },
                'styles': {
                },
                'description': card.description,
                'template': 'archive/components/text-card.html',
            }
        elif card.card_style == 1:
            return {
                'zindex': zindex,
                'content_attrs': {
                },
                'styles': {
                    'border-top': '1px solid #ffffff'
                },
                'description': card.description,
                'template': 'archive/components/text-card.html',
            }
        elif card.card_style == 2:
            return {
                'zindex': zindex,
                'content_attrs': {
                },
                'styles': {
                },
                'description': card.description,
                'template': 'archive/components/text-card.html',
            }
    return card

@register.filter
def all_tags_with(photo, user=None):
    return photo.get_all_tags(user=user)

@register.filter
def describe(object, user=None):
    return object.describe(user)

@register.inclusion_tag('archive/page-links.html', takes_context=False)
def page_links(formatter, page_obj, target=None):
    links = [{'label': label} for label in ['First', 'Previous', 'Next', 'Last']]
    if page_obj.has_previous():
        links[0]['url'] = formatter.page_url(1)
        links[0]['target'] = target
        links[1]['url'] = formatter.page_url(page_obj.previous_page_number())
        links[1]['target'] = target
    if page_obj.has_next():
        links[2]['url'] = formatter.page_url(page_obj.next_page_number())
        links[2]['target'] = target
        links[3]['url'] = formatter.page_url(page_obj.paginator.num_pages)
        links[3]['target'] = target
    return dict(
        links=links,
        page_obj=page_obj
    )

@register.simple_tag(takes_context=False)
def image_url(*, id, path, width=None, height=None):
    return ImageSigner(id=id, path=path, width=width, height=height).url

def count_photos() -> int:
    return Photo.objects.filter(is_published=True).count()

@register.simple_tag(takes_context=False)
def photo_count() -> int:
    return cache.get_or_set("photo_count", count_photos)

@register.filter(is_safe=True)
@stringfilter
def markdown(text):
    return mark_safe(md.markdown(escape(text), extensions=[URLifyExtension()]))

@register.simple_tag(takes_context=False)
def thumb_left(*, index, offset, width):
    return index * width + offset

