from django.db import models
import requests
from django.core.cache import cache
from typing import Optional, Tuple, Dict, Any
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from fortepan_us.kronofoto.reverse import reverse
from fortepan_us.kronofoto import models as kf_models

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
        return self.serialized_public_key or b""

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
    requested_archive_follows : models.ManyToManyField = models.ManyToManyField("kronofoto.Archive", through="FollowArchiveRequest", related_name="%(app_label)s_%(class)s_request_follows")

    def public_key(self) -> Optional[bytes]:
        def _() -> Optional[str]:
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


class LdIdQuerySet(models.QuerySet):
    def get_or_create_ld_object(self, ld_id: str) -> Tuple["LdId", bool]:
        return (self.get(ld_id=ld_id), True)

    def update_or_create_ld_object(self, owner: "kf_models.Archive", object: Dict[str, Any]) -> Tuple[Optional["LdId"], bool]:
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
                created = True
            elif object['type'] == "Image":
                db_obj = kf_models.Photo()
                created = True
        if not db_obj:
            return (None, False)
        if isinstance(db_obj, kf_models.Donor):
            db_obj.first_name = object['firstName']
            db_obj.last_name = object['lastName']
            db_obj.archive = owner
            db_obj.save()
            ct = ContentType.objects.get_for_model(kf_models.Donor)
        elif isinstance(db_obj, kf_models.Photo):
            donor, _ = self.get_or_create_ld_object(object['contributor'])
            db_obj.caption = object['content']
            db_obj.year = object['year']
            db_obj.archive = owner
            db_obj.circa = object['circa']
            db_obj.is_published = object['is_published']
            db_obj.donor = donor.content_object
            db_obj.category, _ = kf_models.Category.objects.get_or_create(
                slug=object['category']['slug'],
                defaults={"name": object['category']['name']},
            )
            ct = ContentType.objects.get_for_model(kf_models.Photo)
            db_obj.save()
            for tag in object['tags']:
                tag, _ = kf_models.Tag.objects.get_or_create(tag=tag)
                kf_models.PhotoTag.objects.get_or_create(tag=tag, photo=db_obj, accepted=True)
            for term in object['terms']:
                db_obj.terms.add(kf_models.Term.objects.get_or_create(term=term)[0])
        ldid, _ = self.get_or_create(ld_id=object['id'], defaults={"content_type": ct, "object_id":db_obj.id})
        return ldid, created


class LdId(models.Model):
    ld_id = models.URLField(unique=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    objects = LdIdQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["content_type", "object_id"], name="unique_content_id_per_object"),
        ]
