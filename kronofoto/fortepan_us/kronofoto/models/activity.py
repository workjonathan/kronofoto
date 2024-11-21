from django.db import models
import requests
from .archive import Archive, ArchiveBase
from django.core.cache import cache
from typing import Optional
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class RemoteActor(models.Model):
    profile = models.URLField(unique=True)
    actor_follows_app = models.BooleanField(default=False)
    app_follows_actor = models.BooleanField(default=False)
    follow_app_request = models.JSONField(null=True)
    archives_followed = models.ManyToManyField(Archive)
    requested_archive_follows : models.ManyToManyField = models.ManyToManyField(Archive, through="FollowArchiveRequest", related_name="%(app_label)s_%(class)s_request_follows")

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
                key = data.get('publicKey', {}).get('publicKeyPem', None)
            return key.encode('utf-8') if key else None
        return cache.get_or_set("kronofoto:keyId:" + self.profile, _, timeout=7*24*60*60)

class RemoteArchive(ArchiveBase):
    actor = models.ForeignKey(RemoteActor, on_delete=models.CASCADE)

class FollowArchiveRequest(models.Model):
    remote_actor = models.ForeignKey(RemoteActor, on_delete=models.CASCADE)
    request_body = models.JSONField()
    archive = models.ForeignKey(Archive, to_field="archivebase_ptr", on_delete=models.CASCADE, null=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["archive", "remote_actor"], name="unique_actor_archive_follows"),
        ]

class OutboxActivity(models.Model):
    body = models.JSONField()
    created = models.DateTimeField(auto_now=True)

class LdId(models.Model):
    ld_id = models.URLField(unique=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["content_type", "object_id"], name="unique_content_id_per_object"),
        ]
