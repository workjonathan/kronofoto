from django.db import models
from .archive import Archive, ArchiveBase

class RemoteActor(models.Model):
    profile = models.URLField(unique=True)
    actor_follows_app = models.BooleanField()
    app_follows_actor = models.BooleanField()
    follow_app_request = models.JSONField(null=True)
    archives_followed = models.ManyToManyField(Archive)
    requested_archive_follows : models.ManyToManyField = models.ManyToManyField(Archive, through="FollowArchiveRequest", related_name="%(app_label)s_%(class)s_request_follows")

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
