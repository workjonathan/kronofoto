from django import template
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
