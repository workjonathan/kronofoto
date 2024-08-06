from django import template
from django.core.signing import Signer
from django.http import HttpRequest
from ..reverse import reverse
import markdown as md # type: ignore
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.cache import cache
from ..models import Photo, Card, Collection, PhotoCard, Figure
from ..imageutil import ImageSigner
from typing import Union, Dict, Any, Union, Optional, Tuple
from django.template.defaultfilters import linebreaksbr, linebreaks_filter
from django.contrib.auth.models import User
from django.db.models import QuerySet, Q
from django.db.models.functions import Lower
import json
import uuid
from django import forms


register = template.Library()

@register.filter
def with_parent(figure: Figure, parent: str) -> Tuple[Figure, str]:
    return figure, parent
@register.filter
def figure_form(figure_parent: Tuple[Figure, str], photos: QuerySet[Photo]) -> forms.Form:
    figure, parent = figure_parent
    from ..forms.card import FigureForm
    form = FigureForm(prefix=str(uuid.uuid1()), initial={"parent": parent, 'card_type': 'figure'}, instance=figure)
    assert hasattr(form.fields['photo'], 'queryset')
    form.fields['photo'].queryset = photos
    return form

@register.inclusion_tag('archive/components/card.html', takes_context=False)
def card_tag(card: Card, zindex: int, edit: bool=False) -> Dict[str, Any]:
    from ..forms import CollectionForm, CardForm, PhotoCardForm
    obj : Dict[str, Any] = {
        'zindex': zindex,
        'edit': edit,
    }
    if hasattr(card, 'photocard'):
        card = card.photocard
        if edit:
            photoform = PhotoCardForm(instance=card, initial={'card_type': "photo"}, prefix=str(uuid.uuid1()))
            if hasattr(photoform.fields['photo'], 'queryset'):
                photo_queryset = Photo.objects.filter(card.photo_choices() | Q(id=card.photo.id))
                photoform.fields['photo'].queryset = photo_queryset
                photoform.fields['photo'].image_urls = json.dumps({photo.id: image_url(id=photo.id, path=photo.original.name, height=200, width=200) for photo in photo_queryset})
            obj['form'] = photoform
        if card.alignment == PhotoCard.Alignment.FULL:
            obj['template'] = 'archive/components/full-image-card.html'
            obj['image_area_classes'] = ['full-image-area--contain']
        else:
            obj['template'] = 'archive/components/two-column-card.html'
            obj['image_area_classes'] = (
                ['two-column--image-left', 'two-column--variation-1']
                if card.alignment == PhotoCard.Alignment.LEFT
                else ['two-column--image-right', 'two-column--variation-2']
            )
    else:
        card = card
        if edit:
            form = CardForm(instance=card, initial={"card_type": "text"}, prefix=str(uuid.uuid1()))
            obj['form'] = form
        obj['template'] = 'archive/components/text-card.html'
        if card.figure_set.all().exists():
            obj['styles'] = {
                'border-top': '1px solid #ffffff',
            }
        obj['content_attrs'] = {
            'data-aos': 'fade-up',
            'data-aos-duration': '1000',
        }
    obj['card'] = card
    return obj



    if hasattr(card, 'photocard'):
        if False: # hasattr(card.photocard, 'doublephotocard'):
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
            if card.card_style == 0: # 0, 5, 7, 8 all seem to be the same now.
            # Jeremy says the css class does something, and now I see what it does.
            # I am not convinced it is necessary or sure how to get the right information from users.
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
        elif card.card_style == 1: # only diff between 1 and 2 is that 2 has a 100px border-top and this overrides it down to 1px. I don't think users should care about this. Maybe this should happen if the previous card is a full width image? Should the spacing be a slider?
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
def image_url(*, id: int, path: str, width: Optional[int]=None, height: Optional[int]=None) -> str:
    return ImageSigner(id=id, path=path, width=width, height=height).url

def count_photos() -> int:
    return Photo.objects.filter(is_published=True).count()

@register.simple_tag(takes_context=False)
def photo_count() -> Optional[Any]:
    return cache.get_or_set("photo_count", count_photos)

@register.filter(is_safe=True)
@stringfilter
def markdown(text: str) -> str:
    from .urlify import URLifyExtension
    return mark_safe(md.markdown(escape(text), extensions=[URLifyExtension()]))

@register.simple_tag(takes_context=False)
def thumb_left(*, index: int, offset: int, width: int) -> int:
    return index * width + offset

@register.inclusion_tag("archive/components/collections.html", takes_context=False)
def collections(request: HttpRequest, profile_user: User) -> Dict[str, Any]:
    from ..forms import CollectionForm
    context = {'request': request, 'profile_user': profile_user}
    context['form'] = CollectionForm()
    filter_kwargs = {}
    if request.user.id != profile_user.id:
        filter_kwargs['visibility'] = "PU"
    context['object_list'] = Collection.objects.by_user(user=profile_user, **filter_kwargs)
    return context
