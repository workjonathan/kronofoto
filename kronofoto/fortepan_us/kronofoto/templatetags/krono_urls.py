from django import template
from django.utils.http import urlencode
from fortepan_us.kronofoto.reverse import reverse
from django.http import QueryDict

register = template.Library()

@register.simple_tag(takes_context=False)
def krono_url(view_name, url_kwargs={}, /, **kwargs):
    return reverse(view_name, kwargs=dict(**url_kwargs, **kwargs))

@register.simple_tag(takes_context=False)
def krono_params(params={}, /, **kwargs):
    if params or kwargs:
        qd = QueryDict(mutable=True)
        qd.update(params)
        qd.update(kwargs)
        return "?" + qd.urlencode()
    return ""

@register.simple_tag(takes_context=False)
def object_url(obj, url_kwargs=None, get_params=None):
    if hasattr(obj, 'get_absolute_url'):
        return obj.get_absolute_url(kwargs=url_kwargs, params=get_params)
    else:
        return ''

@register.simple_tag(takes_context=False)
def grid_url(photo, url_kwargs=None, get_params=None):
    return photo.get_grid_url(kwargs=url_kwargs, params=get_params)

@register.simple_tag(takes_context=False)
def download_page_url(photo, url_kwargs=None, get_params=None):
    return photo.get_download_page_url(kwargs=url_kwargs, params=get_params)
