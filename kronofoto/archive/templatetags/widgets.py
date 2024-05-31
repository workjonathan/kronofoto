from django import template
from django.core.signing import Signer
from django.http import HttpRequest
from ..reverse import reverse
import markdown as md # type: ignore
from .urlify import URLifyExtension
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.cache import cache
from ..models import Photo, Card, Collection
from ..imageutil import ImageSigner
from typing import Union, Dict, Any, Union, Optional
from django.template.defaultfilters import linebreaksbr, linebreaks_filter
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.db.models.functions import Lower
from ..forms import CollectionForm


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
def all_tags_with(photo: Photo, user: Optional[User]=None) -> QuerySet:
    return photo.get_all_tags(user=user)

@register.filter
def describe(object: Photo, user: Optional[User]=None) -> str:
    return object.describe(user)

@register.inclusion_tag('archive/page-links.html', takes_context=False)
def page_links(formatter: Any, page_obj: Any, target: Any=None) -> Dict[str, Any]:
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
def image_url(*, id: int, path: str, width: int, height: int) -> str:
    return ImageSigner(id=id, path=path, width=width, height=height).url

def count_photos() -> int:
    return Photo.objects.filter(is_published=True).count()

@register.simple_tag(takes_context=False)
def photo_count() -> Optional[Any]:
    return cache.get_or_set("photo_count", count_photos)

@register.filter(is_safe=True)
@stringfilter
def markdown(text: str) -> str:
    return mark_safe(md.markdown(escape(text), extensions=[URLifyExtension()]))

@register.simple_tag(takes_context=False)
def thumb_left(*, index: int, offset: int, width: int) -> int:
    return index * width + offset

@register.inclusion_tag("archive/components/collections.html", takes_context=False)
def collections(request: HttpRequest, profile_user: User) -> Dict[str, Any]:
    context = {'request': request, 'profile_user': profile_user}
    context['form'] = CollectionForm()
    filter_kwargs = {}
    if request.user.id != profile_user.id:
        filter_kwargs['visibility'] = "PU"
    context['object_list'] = Collection.objects.by_user(user=profile_user, **filter_kwargs)
    return context
