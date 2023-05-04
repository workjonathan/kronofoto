from django.db import models
from django.utils.text import slugify
from django.core.validators import MinLengthValidator
from django.conf import settings
from django.contrib.auth.models import Permission

class Archive(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False)
    cms_root = models.CharField(max_length=16, null=False, blank=False)
    slug = models.SlugField(unique=True, blank=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through="ArchiveUserPermission")
    # many to many field to user
    #   through object has many to many to permissions. permissions should be restricted only things which i control
    #   admin site for. Because I won't be enabling behavior for anything else.
    #   through object has many to many to custom groups? I think using built in group will result in global
    #   permissions across archives.

    def __str__(self):
        return self.name

class ArchiveUserPermission(models.Model):
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    permission = models.ManyToManyField(Permission)

    def __str__(self):
        return str(self.archive)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['archive', 'user'], name='unique_archive_user'),
        ]
        indexes = [
            models.Index(fields=['archive', 'user']),
        ]
        verbose_name = "archive"
        verbose_name_plural = "archive permissions"

