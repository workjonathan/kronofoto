from django.db import models
from django.utils.text import slugify
from urllib.parse import urlparse
from django.core.validators import MinLengthValidator
from django.conf import settings
from fortepan_us.kronofoto.reverse import reverse, resolve
from django.urls.exceptions import Resolver404
from django.contrib.auth.models import Permission, Group
from .category import Category, ValidCategory
from .activity import RemoteActor
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from typing import Tuple, Any, Dict, Optional
from django.contrib.sites.models import Site
import requests
from marshmallow import Schema, fields, pre_dump, post_load, pre_load, ValidationError
import icontract
from . import activity_dicts, activity_schema

class InvalidArchive(Exception): pass


class ArchiveSchema(activity_schema.ObjectSchema):
    type = fields.Constant("Organization")
    id = fields.Url(relative=True, required=True)
    name = fields.Str(required=True)
    slug = fields.Str(required=True)
    publicKey = fields.Dict(keys=fields.Str(), values=fields.Str())

    inbox = fields.Url(relative=True)
    outbox = fields.Url(relative=True)
    contributors = fields.Url(relative=True)
    photos = fields.Url(relative=True)
    following = fields.Url(relative=True)
    followers = fields.Url(relative=True)

    @pre_dump
    def extract_fields_from_object(self, object: "Archive", **kwargs: Any) -> activity_dicts.ArchiveDict:
        return {
            "id": activity_dicts.str_to_ldidurl(reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object.slug})),
            "name": object.name,
            "slug": object.slug,
            "inbox": activity_dicts.str_to_url(reverse("kronofoto:activitypub_data:archives:inbox", kwargs={"short_name": object.slug})),
            "outbox": activity_dicts.str_to_url(reverse("kronofoto:activitypub_data:archives:outbox", kwargs={"short_name": object.slug})),
            "contributors": activity_dicts.str_to_url(reverse("kronofoto:activitypub_data:archives:contributors:page", kwargs={"short_name": object.slug})),
            "photos": activity_dicts.str_to_url(reverse("kronofoto:activitypub_data:archives:photos:page", kwargs={"short_name": object.slug})),
            "followers": activity_dicts.str_to_url(reverse("kronofoto:activitypub_data:archives:followers", kwargs={"short_name": object.slug})),
            "following": activity_dicts.str_to_url(reverse("kronofoto:activitypub_data:archives:following", kwargs={"short_name": object.slug})),
            "publicKey": {
                "id": object.keyId,
                "owner": reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object.slug}),
                "publicKeyPem": object.guaranteed_public_key(), # type: ignore
            },
        }

class ArchiveQuerySet(models.QuerySet):
    @icontract.require(lambda self, profile: self.have_remote_by_profile(profile))
    @icontract.ensure(lambda self, profile, result: not result[1] and result[0].actor is not None and result[0].actor.profile == profile)
    def get_remote_by_profile(self, profile: str) -> Tuple["Archive", bool]:
        return Archive.objects.get(actor__profile=profile, type=Archive.ArchiveType.REMOTE), False

    @icontract.ensure(lambda self, profile, result: result == Archive.objects.filter(actor__profile=profile, type=Archive.ArchiveType.REMOTE).exists())
    def have_remote_by_profile(self, profile: str) -> bool:
        return Archive.objects.filter(actor__profile=profile, type=Archive.ArchiveType.REMOTE).exists()

    @icontract.ensure(lambda self, profile, result: not result or result in profile)
    def extract_slug(self, profile: str) -> Optional[str]:
        try:
            if not Site.objects.filter(domain=urlparse(profile).netloc).exists():
                return None
            else:
                resolved = resolve(profile)
                if resolved.match.url_name == "actor":
                    return resolved.match.kwargs['short_name']
                else:
                    return None
        except Resolver404:
            return None


    @icontract.require(lambda self, profile: not Site.objects.filter(domain=urlparse(profile).netloc).exists() and not self.have_remote_by_profile(profile))
    @icontract.ensure(lambda self, profile, result: (result[0] is not None) == result[1])
    @icontract.ensure(lambda self, profile, result: result[0] is None or (result[0].actor is not None and result[0].actor.profile == profile))
    def create_remote_profile(self, profile: str) -> Tuple[Optional["Archive"], bool]:
        data : activity_dicts.ArchiveDict = requests.get(
            profile,
            headers={
                'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
        ).json()
        try:
            data = ArchiveSchema().load(data)
            if data['id'] != profile:
                return None, False
            actor = RemoteActor.objects.create(profile=profile)
            server_domain = urlparse(profile).netloc
            return self.create(
                type=Archive.ArchiveType.REMOTE,
                actor=actor,
                server_domain=server_domain,
                name=data['name'],
                slug=data['slug'],
            ), True
        except ValidationError as e:
            print(e)
            return None, False

    @icontract.require(lambda self, profile: Site.objects.filter(domain=urlparse(profile).netloc).exists())
    @icontract.ensure(lambda self, profile, result: not result[1] and (
            slug := self.extract_slug(profile),
            archive_exists := Archive.objects.filter(slug=slug, type=Archive.ArchiveType.LOCAL).exists(),
            (archive_exists == result[0] is not None) and (not archive_exists or result[0] is not None and result[0].slug == slug)
        )[1]
    )
    def get_local_by_profile(self, profile: str) -> Tuple[Optional["Archive"], bool]:
        slug = self.extract_slug(profile)
        if slug is not None and self.filter(slug=slug, type=Archive.ArchiveType.LOCAL).exists():
            return self.get(slug=slug, type=Archive.ArchiveType.LOCAL), False
        return None, False

    @icontract.ensure(lambda self, profile, result: not result[0] or ((not result[0].actor or result[0].actor.profile == profile) and (result[0].actor or result[0].slug in profile)))
    def get_or_create_by_profile(self, profile: str) -> Tuple[Optional["Archive"], bool]:
        server_domain = urlparse(profile).netloc
        if Site.objects.filter(domain=server_domain).exists():
            return self.get_local_by_profile(profile)
        elif self.have_remote_by_profile(profile=profile):
            return self.get_remote_by_profile(profile=profile)
        else:
            return self.create_remote_profile(profile)

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

    objects = ArchiveQuerySet.as_manager()

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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False
    )
    agreement = models.ForeignKey(
        ArchiveAgreement, on_delete=models.CASCADE, null=False
    )
    version = models.DateTimeField(null=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agreement", "user"], name="unique_agreement_user"
            ),
        ]
        indexes = [
            models.Index(fields=["agreement", "user"]),
        ]


class ArchiveUserPermission(models.Model):
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    permission = models.ManyToManyField(Permission)

    def __str__(self) -> str:
        return str(self.archive)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["archive", "user"], name="unique_archive_user"
            ),
        ]
        indexes = [
            models.Index(fields=["archive", "user"]),
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
            models.UniqueConstraint(
                fields=["archive", "group"], name="unique_archive_group"
            ),
        ]
        indexes = [
            models.Index(fields=["archive", "group"]),
        ]
        verbose_name = "archive group permission"
        verbose_name_plural = "archive permissions"
