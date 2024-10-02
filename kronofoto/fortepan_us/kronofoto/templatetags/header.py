from django import template
from fortepan_us.kronofoto.views.basetemplate import Theme
import random
from django.conf import settings
from django.template import RequestContext

register = template.Library()

@register.inclusion_tag('kronofoto/components/header.html', takes_context=True)
def header(context):
    context.setdefault('url_kwargs', {})
    context.setdefault('get_params', {})
    context.setdefault('theme', Theme.select_random_theme())
    context.setdefault('KF_DJANGOCMS_NAVIGATION', settings.KF_DJANGOCMS_NAVIGATION)
    context.setdefault('KF_DJANGOCMS_ROOT', settings.KF_DJANGOCMS_ROOT)
    if hasattr(context, "flatten"):
        context = context.flatten()
    return context


@register.inclusion_tag('kronofoto/components/page-editor-header.html', takes_context=True)
def page_editor_header(context):
    context.setdefault('url_kwargs', {})
    context.setdefault('get_params', {})
    context.setdefault('theme', Theme.select_random_theme())
    context.setdefault('KF_DJANGOCMS_NAVIGATION', settings.KF_DJANGOCMS_NAVIGATION)
    context.setdefault('KF_DJANGOCMS_ROOT', settings.KF_DJANGOCMS_ROOT)
    if hasattr(context, "flatten"):
        context = context.flatten()
    return context
