from django.db import models
from django.utils.text import slugify
from django.core.validators import MinLengthValidator
from django.conf import settings
from django.contrib.auth.models import Permission, Group
from .category import Category, ValidCategory




class Archive(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False)
    cms_root = models.CharField(max_length=16, null=False, blank=False)
    slug = models.SlugField(unique=True, blank=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through="archive.ArchiveUserPermission")
    groups = models.ManyToManyField(Group, through="archive.ArchiveGroupPermission")
    categories = models.ManyToManyField(Category, through=ValidCategory)
    class Meta:
        indexes = (
            models.Index(fields=['slug'], name="archive_slug_idx"),
        )
        db_table = 'kronofoto_archive'


    def __str__(self) -> str:
        return self.name


class ArchiveAgreementQuerySet(models.QuerySet):
    def object_for(self, slug: str) -> models.QuerySet["ArchiveAgreement"]:
        return self.filter(archive__slug=slug)

class ArchiveAgreement(models.Model):
    text = models.TextField(blank=False, null=False)
    version = models.DateTimeField(null=False, auto_now=True)
    archive = models.OneToOneField(Archive, on_delete=models.CASCADE)

    objects = ArchiveAgreementQuerySet.as_manager()

    @property
    def session_key(self) -> str:
        return "kf.agreement.{}.{}".format(self.pk, self.version)


    def __str__(self) -> str:
        return "{} agreement".format(self.archive.name)

    class Meta:
        verbose_name = "agreement"
        db_table = 'kronofoto_archiveagreement'


class UserAgreement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False)
    agreement = models.ForeignKey(ArchiveAgreement, on_delete=models.CASCADE, null=False)
    version = models.DateTimeField(null=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['agreement', 'user'], name='unique_agreement_user'),
        ]
        indexes = [
            models.Index(fields=['agreement', 'user']),
        ]
        db_table = 'kronofoto_useragreement'


class ArchiveUserPermission(models.Model):
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    permission = models.ManyToManyField(Permission)

    def __str__(self) -> str:
        return str(self.archive)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['archive', 'user'], name='unique_archive_user'),
        ]
        indexes = [
            models.Index(fields=['archive', 'user']),
        ]
        verbose_name = "user-archive permissions"
        verbose_name_plural = "archive permissions"
        db_table = 'kronofoto_archiveuserpermission'

class ArchiveGroupPermission(models.Model):
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    permission = models.ManyToManyField(Permission)

    def __str__(self) -> str:
        return str(self.archive)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['archive', 'group'], name='unique_archive_group'),
        ]
        indexes = [
            models.Index(fields=['archive', 'group']),
        ]
        verbose_name = "archive group permission"
        verbose_name_plural = "archive permissions"
        db_table = 'kronofoto_archivegrouppermission'
