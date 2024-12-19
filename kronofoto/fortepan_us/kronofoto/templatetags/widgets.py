from django import template
from django.http import QueryDict
from django.core.signing import Signer
from django.http import HttpRequest
from fortepan_us.kronofoto.reverse import reverse
import markdown as md # type: ignore
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.cache import cache
from fortepan_us.kronofoto.models import Photo, Card, Collection, PhotoCard, Figure
from fortepan_us.kronofoto.imageutil import ImageSigner
from typing import Union, Dict, Any, Union, Optional, Tuple, List, overload
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
    form = FigureForm(prefix=str(uuid.uuid4()), initial={"parent": parent, 'card_type': 'figure'}, instance=figure)
    assert hasattr(form.fields['photo'], 'queryset')
    form.fields['photo'].queryset = photos
    return form

@register.filter
def all_tags_with(photo: Photo, user: Optional[User]=None) -> QuerySet:
    return photo.get_all_tags(user=user)

@register.filter
def describe(object: Photo, user: Optional[User]=None) -> str:
    return object.describe(user)

@register.inclusion_tag('kronofoto/components/page-links.html', takes_context=False)
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

# caller must either photo or photo id (and path which is ignored until other branches are adjusted).
# caller must provide at least a width or a height (or both).
@overload
def image_url(*, width: int, height: Optional[int]=None, photo: Photo) -> str:
    ...
@overload
def image_url(*, width: int, height: Optional[int]=None, id: int, path: Any) -> str:
    ...
@overload
def image_url(*, width: Optional[int]=None, height: int, photo: Photo) -> str:
    ...
@overload
def image_url(*, width: Optional[int]=None, height: int, id: int, path: Any) -> str:
    ...

@register.simple_tag(takes_context=False)
def image_url(*, width: Optional[int]=None, height: Optional[int]=None, photo: Optional[Photo]=None, id: Optional[int]=None, path: Any=None) -> str:
    if photo is None:
        assert id is not None
        photo = Photo.objects.get(id=id)
    return photo.image_url(width=width, height=height)

def count_photos() -> int:
    return Photo.objects.filter(is_published=True).count()

@register.simple_tag(takes_context=False)
def photo_count() -> Optional[Any]:
    return cache.get_or_set("photo_count", count_photos)

@register.filter(is_safe=True)
@stringfilter
def markdown(text: str, extension: Optional[str]=None) -> str:
    # disable ParagraphProcessor?
    from .urlify import URLifyExtension
    extensions = []
    extensions.append(URLifyExtension())
    if extension:
        extensions.append(extension)
    return mark_safe(md.markdown(escape(text), output_format="html", extensions=extensions))

@register.simple_tag(takes_context=False)
def thumb_left(*, index: int, offset: int, width: int) -> int:
    return index * width + offset


@register.inclusion_tag('kronofoto/components/thumbnails.html', takes_context=False)
def thumbnails(*, object_list: List[Photo], positioning: Optional[Dict[str, Any]], url_kwargs=Optional[Dict[str, Any]], get_params: Optional[QueryDict]) -> Dict[str, Any]:
    return  {
        "object_list": object_list,
        "positioning": positioning,
        "url_kwargs": url_kwargs,
        "get_params": get_params,
    }

@register.inclusion_tag("kronofoto/components/collections.html", takes_context=False)
def collections(request: HttpRequest, profile_user: User) -> Dict[str, Any]:
    from fortepan_us.kronofoto.forms import CollectionForm
    context = {'request': request, 'profile_user': profile_user}
    context['form'] = CollectionForm()
    filter_kwargs = {}
    if request.user.id != profile_user.id:
        filter_kwargs['visibility'] = "PU"
    context['object_list'] = Collection.objects.by_user(user=profile_user, **filter_kwargs)
    return context

