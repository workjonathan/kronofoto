from django import template
from ..views.basetemplate import THEME
import random
from django.conf import settings
from django.template import RequestContext

register = template.Library()

@register.inclusion_tag('archive/components/header.html', takes_context=True)
def header(context):
    context.setdefault('url_kwargs', {})
    context.setdefault('get_params', {})
    context.setdefault('theme', random.choice(list(THEME['us'].values())))
    context.setdefault('KF_DJANGOCMS_NAVIGATION', settings.KF_DJANGOCMS_NAVIGATION)
    context.setdefault('KF_DJANGOCMS_ROOT', settings.KF_DJANGOCMS_ROOT)
    if hasattr(context, "flatten"):
        context = context.flatten()
    return context
