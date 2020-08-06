from django import template

register = template.Library()

@register.inclusion_tag('archive/photometadata.html')
def photo_metadata(photo, user=None):
    return {
        'photo': photo,
        'tags': photo.get_accepted_tags(user),
    }
