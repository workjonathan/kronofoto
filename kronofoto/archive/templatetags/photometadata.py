from django import template

register = template.Library()

@register.inclusion_tag('archive/photometadata.html')
def photo_metadata(photo):
    return {'photo': photo }
