from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission

class ArchiveBackend(ModelBackend):
    def get_user_permissions(self, user_obj, obj=None):
        perm_cache = super().get_user_permissions(user_obj, obj)
        perms = Permission.objects.filter(
            archiveuserpermission__user=user_obj,
            content_type__app_label='archive',
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
        user_obj._user_perm_cache = perm_cache
        return perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        return super().has_perm(user_obj, perm, obj)
