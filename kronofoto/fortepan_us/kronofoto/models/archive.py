from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
from django.db import models
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.utils.text import slugify
from urllib.parse import urlparse
from django.core.validators import MinLengthValidator
from django.conf import settings
from fortepan_us.kronofoto.reverse import reverse, resolve
from django.urls.exceptions import Resolver404
from django.contrib.auth.models import Permission, Group
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from typing import Tuple, Any, Dict, Optional
from django.contrib.sites.models import Site
import requests
from marshmallow import Schema, fields, pre_dump, post_load, pre_load, ValidationError
import icontract
from django.db import models
import requests
from urllib.parse import urlparse
from django.contrib.sites.models import Site
from django.core.cache import cache
from typing import Any, TypedDict, List, Literal, NewType, Union, cast, TYPE_CHECKING
from typing_extensions import Never
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from fortepan_us.kronofoto.reverse import reverse, resolve
from marshmallow.exceptions import ValidationError
import icontract


class InvalidArchive(Exception):
    pass

class ServiceActor(models.Model):
    """This stores encryption keys for the application itself. It is used to
    authenticate messages about Places and other data that is complicated and
    shared by archives and instances.
    """
    serialized_public_key = models.BinaryField(null=True, blank=True)
    encrypted_private_key = models.BinaryField(null=True, blank=True)

    @classmethod
    def get_instance(cls) -> "ServiceActor":
        """Get the first instance and create one if it does not exist. There
        should be only one.

        Returns:
            ServiceActor: The ServiceActor
        """
        if cls.objects.exists():
            return cls.objects.all()[0]
        else:
            return cls.objects.create()

    def ldid(self) -> str:
        """Get the LD ID url that describes this actor.

        Returns:
            str: A URL
        """
        return reverse("kronofoto:activitypub-main-service")

    def guaranteed_public_key(self) -> bytes:
        """Get the ServiceActor's public key. It will create a new one if this
        fails.

        Returns:
            bytes: The ServiceActor's public key.
        """
        if not self.serialized_public_key:
            self.generate_new_keys()
        if isinstance(self.serialized_public_key, memoryview):
            return self.serialized_public_key.tobytes()
        elif isinstance(self.serialized_public_key, bytes):
            return self.serialized_public_key
        elif isinstance(self.serialized_public_key, bytearray):
            return bytes(self.serialized_public_key)
        else:
            assert False, "unreachable"


    @property
    def keyId(self) -> str:
        """The LD ID for this actor's main key.

        Returns:
            str: A URL.
        """
        return reverse("kronofoto:activitypub-main-service") + "#mainKey"

    def generate_new_keys(self) -> None:
        """Create new public/private key pairs and save to database."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.serialized_public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.encrypted_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                settings.ENCRYPTION_KEY
            ),
        )
        self.save()

    @property
    def private_key(self) -> rsa.RSAPrivateKey:
        """Get this actor's private key. It will create a new one if this fails.

        Returns:
            rsa.RSAPrivateKey: The private key.
        """
        if self.encrypted_private_key:
            if isinstance(self.encrypted_private_key, bytes):
                byte_key = self.encrypted_private_key
            elif isinstance(self.encrypted_private_key, memoryview):
                byte_key = self.encrypted_private_key.tobytes()
            elif isinstance(self.encrypted_private_key, bytearray):
                byte_key = bytes(self.encrypted_private_key)

            private_key = serialization.load_pem_private_key(
                byte_key,
                password=settings.ENCRYPTION_KEY,
            )
            if isinstance(private_key, rsa.RSAPrivateKey):
                return private_key
        self.generate_new_keys()
        return self.private_key

    @property
    def public_key(self) -> rsa.RSAPublicKey:
        """Get this actor's public key. It will create a new one if this fails.

        Returns:
            rsa.RSAPublicKey: The public key.
        """
        if self.serialized_public_key:
            if isinstance(self.serialized_public_key, bytes):
                byte_key = self.serialized_public_key
            elif isinstance(self.serialized_public_key, memoryview):
                byte_key = self.serialized_public_key.tobytes()
            elif isinstance(self.serialized_public_key, bytearray):
                byte_key = bytes(self.serialized_public_key)
            public_key = serialization.load_pem_public_key(
                byte_key,
            )
            if isinstance(public_key, rsa.RSAPublicKey):
                return public_key
        self.generate_new_keys()
        return self.public_key




class RemoteActorQuerySet(models.QuerySet["RemoteActor"]):
    def get_or_create_by_profile(self, profile: str) -> Tuple[RemoteActor | None, bool]:
        """Get or create a remote actor by LD ID. The profile may be for a local
        URL, in which case it will not do anything. If it is for a remote url,
        it will load it remotely if necessary.

        Returns:
            (RemoteActor | None, bool): The first value will be None if the url is local or the remote url is not valid. The second value will be True if the RemoteActor is saved locally as a result of this call.
        """
        from .activity_dicts import RemoteActorGetOrCreate
        return RemoteActorGetOrCreate(queryset=self, profile=profile).actor

# Django-stubs cannot make sense of reverse relationships to MPTTModels. That is the reason for django-manager-missing.
class RemoteActor(models.Model): # type: ignore[django-manager-missing]
    profile = models.URLField(unique=True)
    actor_follows_app = models.BooleanField(default=False)
    app_follows_actor = models.BooleanField(default=False)
    follow_app_request = models.JSONField(null=True)
    archives_followed = models.ManyToManyField("kronofoto.Archive")
    requested_archive_follows: models.ManyToManyField[
        "Archive", "FollowArchiveRequest"
    ] = models.ManyToManyField(
        "kronofoto.Archive",
        through="FollowArchiveRequest",
        related_name="%(app_label)s_%(class)s_request_follows",
    )

    #@icontract.require(lambda self:
    #    not Site.objects.filter(domain=urlparse(self.profile).netloc).exists()
    #)
    #def save(self, *args: Any, **kwargs: Any) -> Any:
    #    return super().save(*args, **kwargs)


    objects = RemoteActorQuerySet.as_manager()

    def public_key(self) -> bytes | None:
        """Get the remote actor's public key.

        Returns:
            Optional[bytes]: The remote actor's public key, if it can be loaded. If it cannot, it will return None.
        """
        def _() -> str | None:
            resp = requests.get(
                self.profile,
                headers={
                    "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
            )
            key = None
            if resp.status_code == 200:
                data = resp.json()
                key = data.get("publicKey", {}).get("publicKeyPem", None)
            return key.encode("utf-8") if key else None

        return cache.get_or_set("kronofoto:keyId:" + self.profile, _, timeout=10)

class FollowServiceOutbox(models.Model):
    remote_actor_profile = models.URLField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["remote_actor_profile"], name="unique_service_follows"
            ),
        ]

class FollowServiceRequest(models.Model):
    """Used to track when a remote actor has requested to follow the application
    itself (eg for Place data).
    """
    remote_actor = models.ForeignKey(RemoteActor, on_delete=models.CASCADE)
    request_id = models.URLField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["remote_actor"], name="unique_actor_service_follows"
            ),
        ]

class FollowArchiveRequest(models.Model):
    "Used to track requests to follow an Archive."
    remote_actor = models.ForeignKey(RemoteActor, on_delete=models.CASCADE)
    request_id = models.URLField()
    archive = models.ForeignKey(
        "kronofoto.Archive", on_delete=models.CASCADE, null=False
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["archive", "remote_actor"], name="unique_actor_archive_follows"
            ),
        ]


class OutboxActivity(models.Model):
    body = models.JSONField()
    created = models.DateTimeField(auto_now=True)


class ArchiveQuerySet(models.QuerySet):
    @icontract.require(lambda self, profile: self.have_remote_by_profile(profile))
    @icontract.ensure(
        lambda self, profile, result: not result[1]
        and result[0].actor is not None
        and result[0].actor.profile == profile
    )
    def get_remote_by_profile(self, profile: str) -> Tuple["Archive", bool]:
        """Get a remote archive by profile. The Archive must exist for this
        function to succeed.

        Args:
            profile (str): The LD ID of the remote Archive.

        Returns:
            (Archive, bool): The Archive with the requested LD ID, and whether the Archive is created, so False.
        """
        return (
            Archive.objects.get(
                actor__profile=profile, type=Archive.ArchiveType.REMOTE
            ),
            False,
        )

    def have_remote_by_profile(self, profile: str) -> bool:
        """Determine whether the database has the requested remote Archive.

        Args:
            profile (str): The LD ID of the remote Archive.

        Returns:
            bool: True if the remote archive is known to our database.
        """
        return Archive.objects.filter(
            actor__profile=profile, type=Archive.ArchiveType.REMOTE
        ).exists()

    @icontract.ensure(lambda self, profile, result: not result or result in profile)
    def extract_slug(self, profile: str) -> Optional[str]:
        """Attempt to extract the archive's slug from the profile url.

        Args:
            profile (str): The LD ID of the remote Archive.

        Returns:
            Optional[str]: If the slug can be extracted, return the slug. Otherwise it will be None.
        """
        try:
            if not Site.objects.filter(domain=urlparse(profile).netloc).exists():
                return None
            else:
                resolved = resolve(profile)
                if resolved.match.url_name == "actor":
                    return resolved.match.kwargs["short_name"]
                else:
                    return None
        except Resolver404:
            return None

    @icontract.require(
        lambda self, profile: not Site.objects.filter(
            domain=urlparse(profile).netloc
        ).exists()
        and not self.have_remote_by_profile(profile)
    )
    @icontract.ensure(
        lambda self, profile, result: (result[0] is not None) == result[1]
    )
    @icontract.ensure(
        lambda self, profile, result: result[0] is None
        or (result[0].actor is not None and result[0].actor.profile == profile)
    )
    def create_remote_profile(self, profile: str) -> Tuple[Optional["Archive"], bool]:
        """Create an Archive representing a remote actor.

        It is only valid to call this with a non-local url.

        Args:
            profile (str): The LD ID of the remote Archive.

        Returns:
            (Optional[Archive], bool): The first in the tuple is the Archive. If the remote definition cannot be loaded, it will return None. The second in the tuple represents whether the Archive has been created as a result of this call. It will be False if the remote data cannot be loaded or parsed.
        """
        from fortepan_us.kronofoto.models.activity_dicts import ArchiveValue
        data_dict = requests.get(
            profile,
            headers={
                "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
        ).json()
        try:
            from fortepan_us.kronofoto.models.activity_schema import ArchiveSchema
            data : ArchiveValue = ArchiveSchema().load(data_dict)
            if data.id != profile:
                return None, False
            actor = RemoteActor.objects.create(profile=profile)
            server_domain = urlparse(profile).netloc
            return (
                self.create(
                    type=Archive.ArchiveType.REMOTE,
                    actor=actor,
                    server_domain=server_domain,
                    name=data.name,
                    slug=data.slug,
                ),
                True,
            )
        except ValidationError as e:
            print(e)
            return None, False

    @icontract.require(
        lambda self, profile: Site.objects.filter(
            domain=urlparse(profile).netloc
        ).exists()
    )
    @icontract.ensure(
        lambda self, profile, result: not result[1]
        and (
            slug := self.extract_slug(profile),
            archive_exists := Archive.objects.filter(
                slug=slug, type=Archive.ArchiveType.LOCAL
            ).exists(),
            (archive_exists == result[0] is not None)
            and (
                not archive_exists or result[0] is not None and result[0].slug == slug
            ),
        )[1]
    )
    def get_local_by_profile(self, profile: str) -> Tuple[Optional["Archive"], bool]:
        """Get a local Archive by the profile url.

        It is not valid to call this function with a non-local url.

        Args:
            profile (str): The LD ID of the local archive.

        Returns:
            (Optional[Archive], bool): The first in the tuple will be None if the archive does not exist. The second represents whether this call resulted in the Archive being created, and it will be False.
        """
        slug = self.extract_slug(profile)
        if (
            slug is not None
            and self.filter(slug=slug, type=Archive.ArchiveType.LOCAL).exists()
        ):
            return self.get(slug=slug, type=Archive.ArchiveType.LOCAL), False
        return None, False

    @icontract.ensure(
        lambda self, profile, result: not result[0]
        or (
            (not result[0].actor or result[0].actor.profile == profile)
            and (result[0].actor or result[0].slug in profile)
        )
    )
    def get_or_create_by_profile(
        self, profile: str
    ) -> Tuple[Optional["Archive"], bool]:
        """Get an Archive by its LD ID profile URL.

        Args:
            profile (str): The LD ID profile URL.

        Returns:
            (Optional[Archive], bool): The first value will be the Archive if it exists and can be loaded, otherwise None. The second value conveys whether the Archive was created as a result of the call.
        """
        server_domain = urlparse(profile).netloc
        if Site.objects.filter(domain=server_domain).exists():
            return self.get_local_by_profile(profile)
        elif self.have_remote_by_profile(profile=profile):
            return self.get_remote_by_profile(profile=profile)
        else:
            return self.create_remote_profile(profile)


class Archive(models.Model):
    """Archives are basically the work of a moderation team. Photos and Donors
    both belong to an Archive.
    """
    class ArchiveType(models.IntegerChoices):
        LOCAL = 0
        REMOTE = 1

    actor = models.ForeignKey(RemoteActor, on_delete=models.CASCADE, null=True, editable=False)
    type = models.IntegerField(choices=ArchiveType.choices, default=ArchiveType.LOCAL, editable=False)
    name = models.CharField(max_length=64, null=False, blank=False)
    slug = models.SlugField(blank=False, null=False)
    server_domain = models.CharField(max_length=255, null=False, blank=True, default="", editable=False)

    class Meta:
        unique_together = ("slug", "server_domain")
        indexes = (models.Index(fields=["slug"], name="archivebase_slug_idx"),)

    cms_root = models.CharField(max_length=16, null=True, blank=False)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="kronofoto.ArchiveUserPermission"
    )
    groups = models.ManyToManyField(Group, through="kronofoto.ArchiveGroupPermission")
    categories = models.ManyToManyField(
        "kronofoto.Category", through="kronofoto.ValidCategory"
    )
    serialized_public_key = models.BinaryField(null=True, blank=True)
    encrypted_private_key = models.BinaryField(null=True, blank=True)

    objects = ArchiveQuerySet.as_manager()

    def guaranteed_public_key(self) -> bytes:
        """Get a public key for this archive.

        Returns:
            bytes: The public key for this Archive.
        """
        if not self.serialized_public_key:
            self.generate_new_keys()
        if isinstance(self.serialized_public_key, memoryview):
            return self.serialized_public_key.tobytes()
        elif isinstance(self.serialized_public_key, bytes):
            return self.serialized_public_key
        elif isinstance(self.serialized_public_key, bytearray):
            return bytes(self.serialized_public_key)
        else:
            assert False, "unreachable"

    def ldid(self) -> str:
        """The LD ID url for this archive. It is the `profile` that is
        frequently referenced. It should only be used for local actors.

        Returns:
            str: A LD ID url.
        """
        return reverse(
            "kronofoto:activitypub_data:archives:actor",
            kwargs={"short_name": self.slug},
        )

    @property
    def keyId(self) -> str:
        """The LD ID url for this archive's public key.

        Returns:
            str: A LD ID for a key.
        """
        return (
            reverse(
                "kronofoto:activitypub_data:archives:actor",
                kwargs={"short_name": self.slug},
            )
            + "#mainKey"
        )

    def generate_new_keys(self) -> None:
        """Generate a new public/private key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.serialized_public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.encrypted_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                settings.ENCRYPTION_KEY
            ),
        )
        self.save()

    @property
    def private_key(self) -> rsa.RSAPrivateKey:
        """Get a private key for this Archive. If it fails, it will create a new
        key pair.

        Returns:
            rsa.RSAPrivateKey: The private key for this archive.
        """
        if self.encrypted_private_key:
            if isinstance(self.encrypted_private_key, bytes):
                byte_key = self.encrypted_private_key
            elif isinstance(self.encrypted_private_key, memoryview):
                byte_key = self.encrypted_private_key.tobytes()
            elif isinstance(self.encrypted_private_key, bytearray):
                byte_key = bytes(self.encrypted_private_key)
            private_key = serialization.load_pem_private_key(
                byte_key,
                password=settings.ENCRYPTION_KEY,
            )
            if isinstance(private_key, rsa.RSAPrivateKey):
                return private_key
        self.generate_new_keys()
        return self.private_key

    @property
    def public_key(self) -> rsa.RSAPublicKey:
        """Get a public key for this Archive. If it fails, it will create a new
        key pair.

        Returns:
            rsa.RSAPublicKey: The public key for this archive.
        """
        if self.serialized_public_key:
            if isinstance(self.serialized_public_key, bytes):
                byte_key = self.serialized_public_key
            elif isinstance(self.serialized_public_key, memoryview):
                byte_key = self.serialized_public_key.tobytes()
            elif isinstance(self.serialized_public_key, bytearray):
                byte_key = bytes(self.serialized_public_key)
            public_key = serialization.load_pem_public_key(
                byte_key,
            )
            if isinstance(public_key, rsa.RSAPublicKey):
                return public_key
        self.generate_new_keys()
        return self.public_key

    def __str__(self) -> str:
        return (
            "{}@{}".format(self.slug, self.server_domain)
            if self.server_domain
            else self.name
        )


class ArchiveAgreementQuerySet(models.QuerySet):
    def object_for(self, slug: str) -> models.QuerySet["ArchiveAgreement"]:
        """Get the ArchiveAgreements for a given slug.

        Args:
            slug (str): The slug of the Archive.

        Returns:
            ArchiveAgreementQuerySet: The Agreements for this archive slug.
        """
        return self.filter(archive__slug=slug)


class ArchiveAgreement(models.Model):
    text = models.TextField(blank=False, null=False)
    version = models.DateTimeField(null=False, auto_now=True)
    archive = models.OneToOneField(Archive, on_delete=models.CASCADE)

    objects = ArchiveAgreementQuerySet.as_manager()

    @property
    def session_key(self) -> str:
        """Get a session key for this agreement.

        Agreements can be agreed to by anonymous users, so these keys are used
        to save agreement for anonymous users. The Agreements are also
        versioned, so if the user agrees to an older version, they should be
        asked again to agree to the new version.

        Returns:
            str: A session key.
        """
        return "kf.agreement.{}.{}".format(self.pk, self.version)

    def __str__(self) -> str:
        return "{} agreement".format(self.archive.name)

    class Meta:
        verbose_name = "agreement"


class UserAgreement(models.Model):
    """Used to store whether a user has agreed while logged in, so users do not
    need to be asked to agree multiple times.
    """
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
    """User permissions can be granted for certain archive associated data on a
    per-archive basis.
    """
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
    """Groups can also have permissions on a per-archive basis."""

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
