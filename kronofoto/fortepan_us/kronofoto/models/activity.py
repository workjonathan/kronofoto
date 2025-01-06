from __future__ import annotations
from django.db import models
import requests
from urllib.parse import urlparse
from django.contrib.sites.models import Site
from django.core.cache import cache
from typing import Any, TypedDict, List, Literal, NewType, Union, cast
from typing_extensions import Never
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from fortepan_us.kronofoto.reverse import reverse, resolve
from fortepan_us.kronofoto import models as kf_models
from . import activity_dicts
from . import activity_schema
from marshmallow.exceptions import ValidationError
import icontract


class ServiceActor(models.Model):
    serialized_public_key = models.BinaryField(null=True, blank=True)
    encrypted_private_key = models.BinaryField(null=True, blank=True)

    @classmethod
    def get_instance(cls) -> "ServiceActor":
        if cls.objects.exists():
            return cls.objects.all()[0]
        else:
            return cls.objects.create()

    def guaranteed_public_key(self) -> bytes:
        if not self.serialized_public_key:
            self.generate_new_keys()
        assert self.serialized_public_key
        return self.serialized_public_key

    @property
    def keyId(self) -> str:
        return reverse("kronofoto:activitypub-main-service") + "#mainKey"

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

class RemoteActor(models.Model):
    profile = models.URLField(unique=True)
    actor_follows_app = models.BooleanField(default=False)
    app_follows_actor = models.BooleanField(default=False)
    follow_app_request = models.JSONField(null=True)
    archives_followed = models.ManyToManyField('kronofoto.Archive')
    requested_archive_follows : models.ManyToManyField["kf_models.Archive", "FollowArchiveRequest"] = models.ManyToManyField("kronofoto.Archive", through="FollowArchiveRequest", related_name="%(app_label)s_%(class)s_request_follows")

    def public_key(self) -> bytes | None:
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
                print(data)
                key = data.get('publicKey', {}).get('publicKeyPem', None)
            return key.encode('utf-8') if key else None
        return cache.get_or_set("kronofoto:keyId:" + self.profile, _, timeout=10)

class FollowArchiveRequest(models.Model):
    remote_actor = models.ForeignKey(RemoteActor, on_delete=models.CASCADE)
    request_body = models.JSONField()
    archive = models.ForeignKey("kronofoto.Archive", on_delete=models.CASCADE, null=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["archive", "remote_actor"], name="unique_actor_archive_follows"),
        ]

class OutboxActivity(models.Model):
    body = models.JSONField()
    created = models.DateTimeField(auto_now=True)


class LdIdQuerySet(models.QuerySet["LdId"]):
    def get_or_create_ld_object(self, ld_id: activity_dicts.LdIdUrl) -> tuple["LdId", bool]:
        server_domain = urlparse(ld_id).netloc
        if Site.objects.filter(domain=server_domain).exists():
            resolved = resolve(ld_id)
            if resolved.match.namespaces == ['kronofoto', 'activitypub_data', 'archives', 'contributors'] and resolved.match.url_name == 'detail':
                return LdId(content_object=kf_models.Donor.objects.get(archive__slug=resolved.match.kwargs['short_name']), id=resolved.match.kwargs['pk']), False
            raise NotImplementedError
        try:
            return (self.get(ld_id=ld_id), False)
        except self.model.DoesNotExist:
            object = requests.get(
                ld_id,
                headers={
                    'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
            ).json()
            assert object['id'] == ld_id
            if object['type'] == 'Contact':
                try:
                    data : activity_dicts.ActivitypubContact = activity_schema.Contact().load(object)
                    archive, _ = kf_models.Archive.objects.get_or_create_by_profile(profile=data['attributedTo'][0])
                    if not archive:
                        raise NotImplementedError
                    db_obj = kf_models.Donor()
                    db_obj.archive = archive
                    db_obj.reconcile(data)
                    ct = ContentType.objects.get_for_model(kf_models.Donor)
                    ldid, _ = self.get_or_create(ld_id=object['id'], defaults={"content_type": ct, "object_id":db_obj.id})
                    return ldid, True
                except ValidationError:
                    raise NotImplementedError
            else:
                raise NotImplementedError


    def update_or_create_ld_object(self, owner: "kf_models.Archive", object: activity_dicts.ActivitypubData) -> tuple["LdId" | None, bool]:
        ldid = None
        try:
            ldid = self.get(ld_id=object['id'])
            db_obj = ldid.content_object
            if db_obj and db_obj.archive.id != owner.id:
                db_obj = None
            else:
                created = False
        except self.model.DoesNotExist:
            if object['type'] == "Contact":
                db_obj = kf_models.Donor()
                db_obj.archive = owner
                created = True
            elif object['type'] == "Image":
                db_obj = kf_models.Photo()
                db_obj.archive = owner
                created = True
        if not db_obj:
            return (None, False)
        if isinstance(db_obj, kf_models.Donor):
            assert object['type'] == 'Contact'
            db_obj.reconcile(object)
            ct = ContentType.objects.get_for_model(kf_models.Donor)
        elif isinstance(db_obj, kf_models.Photo):
            assert object['type'] == 'Image'
            donor, _ = self.get_or_create_ld_object(object['contributor'])
            assert donor.content_object
            db_obj.reconcile(object, donor.content_object)
            ct = ContentType.objects.get_for_model(kf_models.Photo)
            db_obj.save()
            for tag in object['tags']:
                new_tag, _ = kf_models.Tag.objects.get_or_create(tag=tag)
                kf_models.PhotoTag.objects.get_or_create(tag=new_tag, photo=db_obj, accepted=True)
            for term in object['terms']:
                db_obj.terms.add(kf_models.Term.objects.get_or_create(term=term)[0])
        ldid, _ = self.get_or_create(ld_id=object['id'], defaults={"content_type": ct, "object_id":db_obj.id})
        return ldid, created


class LdId(models.Model):
    ld_id = cast("models.Field[activity_dicts.LdIdUrl, activity_dicts.LdIdUrl]", models.URLField(unique=True))
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    objects = LdIdQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["content_type", "object_id"], name="unique_content_id_per_object"),
        ]
