from __future__ import annotations
import icontract
from functools import cached_property
from typing import cast, Any
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from urllib.parse import urlparse
from django.contrib.sites.models import Site
from django.db import models
from .archive import RemoteActor
import requests
from marshmallow.exceptions import ValidationError
from django.urls.exceptions import Resolver404
from .place import Place, PlaceType
from .donor import Donor
from .photo import Photo, PhotoTag
from .archive import Archive
from .tag import Tag
from .term import Term

from fortepan_us.kronofoto.reverse import reverse, resolve, ResolveResults
from dataclasses import dataclass


class LdIdQuerySet(models.QuerySet["LdId"]):
    pass


class LdId(models.Model):
    """Store LD ID for remote objects. This uses a GenericForeignKey so any
    database object can have an LD ID. However, only Photos, Donors, and Places
    are supported.
    """
    ld_id = models.URLField(unique=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    objects = LdIdQuerySet.as_manager()

    def delete_if_can(self, actor: RemoteActor) -> None:
        """Deprecated."""
        content_object = self.content_object
        if isinstance(content_object, Photo):
            if actor.archive_set.filter(id=content_object.archive.id).exists():
                content_object.delete()
                self.delete()
        elif isinstance(content_object, Donor):
            if actor.archive_set.filter(id=content_object.archive.id).exists():
                content_object.delete()
                self.delete()
        elif isinstance(content_object, Place):
            if actor.id == content_object.owner.id:
                content_object.delete()
                self.delete()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                name="unique_content_id_per_object",
            ),
        ]
