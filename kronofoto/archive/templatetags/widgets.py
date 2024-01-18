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
    block1 = id & 255
    block2 = (id >> 8) & 255
    signer = Signer(salt="{}/{}".format(block1, block2))
    profile_args = {"path": path}
    if width:
        profile_args['width'] = width
    if height:
        profile_args['height'] = width
    profile = signer.sign_object(profile_args)
    return reverse("kronofoto:resize-image", kwargs={'block1': block1, 'block2': block2, 'profile1': profile.split(':')[0], 'profile2': profile.split(":")[1]})

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

