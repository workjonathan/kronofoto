from django import template
from ..models.photo import Photo
from dataclasses import dataclass
from typing import Any, List, Protocol
from django.contrib.auth.models import User

register = template.Library()

@dataclass
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
            'archive.change_photo',
            'archive.view_photo',
            'archive.archive.{}.view_photo'.format(slug),
            'archive.archive.{}.change_photo'.format(slug),
        ]

@dataclass
class PermissionListFactory:
    def permission_list(self, object: Any) -> PermissionBase:
        if isinstance(object, Photo):
            return PhotoPermissions(object)
        else:
            raise NotImplemented

@register.filter
def has_view_or_change_permission(user: User, object: Any) -> bool:
    lister = PermissionListFactory().permission_list(object)
    return user.is_staff and any(user.has_perm(perm) for perm in lister.permissions)
