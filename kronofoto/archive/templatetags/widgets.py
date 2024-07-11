from django import template
from django.core.signing import Signer
from ..reverse import reverse
import markdown as md
from .urlify import URLifyExtension
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.cache import cache
from ..models import Photo
from ..imageutil import ImageSigner
from typing import Optional, Any, List, Dict


register = template.Library()

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

@register.inclusion_tag('archive/thumbnails.html', takes_context=False)
def thumbnails(*, object_list: List[Photo], positioning: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return  {}
