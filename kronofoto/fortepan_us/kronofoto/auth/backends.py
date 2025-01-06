from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission, AbstractBaseUser, AnonymousUser, User
from django.db.models import Q, Exists, OuterRef, QuerySet
from fortepan_us.kronofoto.models.archive import Archive
from typing import Any, Union, Optional, List, Dict, Set, Tuple

class ArchiveBackend(ModelBackend):
    def get_group_permissions(self, user_obj: Union[User, AnonymousUser], obj: Any=None) -> Set[str]:
        if user_obj.is_anonymous:
            return set()
        perm_cache = super().get_group_permissions(user_obj, obj)
        group_perms_qs = Permission.objects.filter(
            archivegrouppermission__group__user__id=user_obj.pk,
            content_type__app_label='kronofoto',
        )
        group_perms = group_perms_qs.values_list(
            'content_type__app_label',
            'archivegrouppermission__archive__slug',
            'codename',
        ).order_by()
        perm_cache = perm_cache.union({
            "{label}.any.{codename}".format(label=label, codename=codename)
            for label, slug, codename in group_perms
        })
        perm_cache = perm_cache.union({
            "{label}.archive.{slug}.{codename}".format(label=label, slug=slug, codename=codename)
            for label, slug, codename in group_perms
        })
        perms_qs = Permission.objects.filter(
            group__user=user_obj,
            content_type__app_label='kronofoto',
        )
        perms = perms_qs.values_list('content_type__app_label', 'codename').order_by()
        perm_cache = perm_cache.union(self.implied_per_archive_permissions(perms))
        user_obj._group_perm_cache = perm_cache # type: ignore
        return perm_cache

    def implied_per_archive_permissions(self, values: Any) -> Set[str]:
        return {
            "{label}.archive.{slug}.{codename}".format(label=label, codename=codename, slug=archive.slug)
            for label, codename in values
            for archive in Archive.objects.all()
        } | {
            "{label}.any.{codename}".format(label=label, codename=codename)
            for label, codename in values
        }

    def get_user_permissions(self, user_obj: Union[User, AnonymousUser], obj: Any=None) -> Set[str]:
        assert hasattr(user_obj, "is_superuser")
        perm_cache = super().get_user_permissions(user_obj, obj)
        perms: QuerySet = Permission.objects.filter(
            archiveuserpermission__user=user_obj,
            content_type__app_label='kronofoto',
        )
        perms = perms.values_list('content_type__app_label', 'archiveuserpermission__archive__slug', 'codename').order_by()
        perm_cache = perm_cache.union({
            "{label}.any.{codename}".format(label=label, codename=codename)
            for label, slug, codename in perms
        })
        perm_cache = perm_cache.union({
            "{label}.archive.{slug}.{codename}".format(label=label, slug=slug, codename=codename)
            for label, slug, codename in perms
        })
        if user_obj.is_superuser:
            perms = Permission.objects.filter(
                content_type__app_label='kronofoto',
            )
        else:
            perms = Permission.objects.filter(
                user=user_obj,
                content_type__app_label='kronofoto',
            )
        perms = perms.values_list('content_type__app_label', 'codename').order_by()
        perm_cache = perm_cache.union(self.implied_per_archive_permissions(perms))

        user_obj._user_perm_cache = perm_cache # type: ignore
        return perm_cache

    def has_perm(self, user_obj: Union[User, AnonymousUser], perm: str, obj: Any=None) -> bool:
        return super().has_perm(user_obj, perm, obj)
