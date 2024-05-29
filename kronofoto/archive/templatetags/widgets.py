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
from ..models import Photo, Collection
from ..imageutil import ImageSigner
from typing import Optional, Any, Dict
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.db.models.functions import Lower
from ..forms import CollectionForm


register = template.Library()

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
