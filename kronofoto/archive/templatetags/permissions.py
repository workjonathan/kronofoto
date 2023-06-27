from django import template
from ..models.photo import Photo

register = template.Library()

@register.filter
def has_view_or_change_permission(user, object):
    if isinstance(object, Photo):
        perms = [
            'archive.change_photo',
            'archive.view_photo',
            'archive.archive.{}.view_photo'.format(object.archive.slug),
            'archive.archive.{}.change_photo'.format(object.archive.slug),
        ]
    else:
        raise NotImplemented
    return user.is_staff and any(user.has_perm(perm) for perm in perms)
