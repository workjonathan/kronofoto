from django import template

register = template.Library()

@register.inclusion_tag('archive/photometadata.html', takes_context=True)
def photo_metadata(context):
    return context
