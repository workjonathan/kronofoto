from django import template
from fortepan_us.kronofoto.models.photo import Photo
from dataclasses import dataclass
from typing import Any, List, Protocol
from django.contrib.auth.models import User

register = template.Library()

class PermissionBase(Protocol):
    @property
    def permissions(self) -> List[str]:
        ...

@dataclass
class PhotoPermissions:
    object: Photo
    @property
    def permissions(self) -> List[str]:
        slug = self.object.archive.slug
        return [
            'kronofoto.change_photo',
            'kronofoto.view_photo',
            'kronofoto.archive.{}.view_photo'.format(slug),
            'kronofoto.archive.{}.change_photo'.format(slug),
        ]

class PermissionListFactory:
    def permission_list(self, object: Any) -> PermissionBase:
        if isinstance(object, Photo):
            return PhotoPermissions(object)
        else:
            raise NotImplementedError

@register.filter
def has_view_or_change_permission(user: User, object: Any) -> bool:
    lister = PermissionListFactory().permission_list(object)
    return user.is_staff and any(user.has_perm(perm) for perm in lister.permissions)
