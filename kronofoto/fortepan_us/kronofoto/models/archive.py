from django.db import models
from django.utils.text import slugify
from django.core.validators import MinLengthValidator
from django.conf import settings
from fortepan_us.kronofoto.reverse import reverse
from django.contrib.auth.models import Permission, Group
from .category import Category, ValidCategory
from .activity import RemoteActor
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class Archive(models.Model):
    class ArchiveType(models.IntegerChoices):
        LOCAL = 0
        REMOTE = 1

    actor = models.ForeignKey(RemoteActor, on_delete=models.CASCADE, null=True)
    type = models.IntegerField(choices=ArchiveType.choices, default=ArchiveType.LOCAL)
    name = models.CharField(max_length=64, null=False, blank=False)
    slug = models.SlugField(blank=False, null=False)
    server_domain = models.CharField(max_length=255, null=False, blank=True, default="")

    class Meta:
        unique_together = ("slug", "server_domain")
        indexes = (
            models.Index(fields=['slug'], name="archivebase_slug_idx"),
        )


    cms_root = models.CharField(max_length=16, null=True, blank=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through="kronofoto.ArchiveUserPermission")
    groups = models.ManyToManyField(Group, through="kronofoto.ArchiveGroupPermission")
    categories = models.ManyToManyField(Category, through=ValidCategory)
    serialized_public_key = models.BinaryField(null=True, blank=True)
    encrypted_private_key = models.BinaryField(null=True, blank=True)

    def guaranteed_public_key(self) -> bytes:
        if not self.serialized_public_key:
            self.generate_new_keys()
        return self.serialized_public_key or b""

    @property
    def keyId(self) -> str:
        return reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": self.slug}) + "#mainKey"

    def generate_new_keys(self) -> None:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.serialized_public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.encrypted_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(settings.ENCRYPTION_KEY),
        )
        self.save()

    @property
    def private_key(self) -> rsa.RSAPrivateKey:
        if self.encrypted_private_key and isinstance(self.encrypted_private_key, bytes):
            private_key = serialization.load_pem_private_key(
                self.encrypted_private_key,
                password=settings.ENCRYPTION_KEY,
            )
            if isinstance(private_key, rsa.RSAPrivateKey):
                return private_key
        self.generate_new_keys()
        return self.private_key

    @property
    def public_key(self) -> rsa.RSAPublicKey:
        if self.serialized_public_key and isinstance(self.serialized_public_key, bytes):
            public_key = serialization.load_pem_public_key(
                self.serialized_public_key,
            )
            if isinstance(public_key, rsa.RSAPublicKey):
                return public_key
        self.generate_new_keys()
        return self.public_key


    def __str__(self) -> str:
        return "{}@{}".format(self.slug, self.server_domain) if self.server_domain else self.name


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
