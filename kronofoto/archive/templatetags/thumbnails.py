from django import template

register = template.Library()

@register.inclusion_tag('archive/thumbnails.html', takes_context=True)
def make_thumbnails(context):
    return context
