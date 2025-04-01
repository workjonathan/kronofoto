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
    #def get_or_create_ld_object(
    #    self, ld_id: activity_dicts.LdIdUrl
    #) -> tuple["LdId" | None, bool]:
    #    return LdObjectGetOrCreator(queryset=self, ld_id=ld_id).object

    #@icontract.ensure(
    #    lambda self, owner, object, result: result[0] is None
    #    or (isinstance(result[0].content_object, Place) and result[0].content_object.owner.id == owner.id)
    #)
    #def update_or_create_ld_service_object(
    #    self, owner: RemoteActor, object: activity_dicts.PlaceValue
    #) -> tuple["LdId" | None, bool]:
    #    return PlaceUpserter(queryset=self, owner=owner, object=object).result

    #@icontract.require(
    #    lambda self, owner, object: owner.type == Archive.ArchiveType.REMOTE
    #)
    #@icontract.ensure(
    #    lambda self, owner, object, result: result[0] is None
    #    or not isinstance(result[0].content_object, Donor)
    #    or object["type"] == "Contact"
    #)
    #@icontract.ensure(
    #    lambda self, owner, object, result: result[0] is None
    #    or not isinstance(result[0].content_object, Photo)
    #    or object["type"] == "Image"
    #)
    #def update_or_create_ld_object(
    #    self, owner: "Archive", object: activity_dicts.PhotoValue | activity_dicts.DonorValue
    #) -> tuple["LdId" | None, bool]:
    #    "This function is valid for object['id'] that are external domains only."
    #    "This function is only valid for Contact/Donor and Image/Photo, which should be all that is needed."
    #    ldid = None
    #    try:
    #        ldid = self.get(ld_id=object.id)
    #        db_obj = ldid.content_object
    #        if db_obj and db_obj.archive.id != owner.id:
    #            db_obj = None
    #        else:
    #            created = False
    #    except self.model.DoesNotExist:
    #        if isinstance(object, activity_dicts.DonorValue):
    #            db_obj = Donor()
    #            db_obj.archive = owner
    #            created = True
    #        else:
    #            db_obj = Photo()
    #            db_obj.archive = owner
    #            created = True
    #    if not db_obj:
    #        return (None, False)
    #    if isinstance(db_obj, Donor) and isinstance(object, activity_dicts.DonorValue):
    #        db_obj.reconcile(object)
    #        ct = ContentType.objects.get_for_model(Donor)
    #    elif isinstance(db_obj, Photo) and isinstance(object, activity_dicts.PhotoValue):
    #        if object.contributor:
    #            donor, _ = self.get_or_create_ld_object(activity_dicts.str_to_ldidurl(object.contributor))
    #        else:
    #            donor = None
    #        if not donor or not donor.content_object:
    #            return None, False
    #        db_obj.reconcile(object, donor.content_object)
    #        ct = ContentType.objects.get_for_model(Photo)
    #        db_obj.save()
    #        for tag in object.tags:
    #            new_tag, _ = Tag.objects.get_or_create(tag=tag)
    #            PhotoTag.objects.get_or_create(
    #                tag=new_tag, photo=db_obj, accepted=True
    #            )
    #        for term in object.terms:
    #            db_obj.terms.add(Term.objects.get_or_create(term=term)[0])
    #    ldid, _ = self.get_or_create(
    #        ld_id=object.id, defaults={"content_type": ct, "object_id": db_obj.id}
    #    )
    #    return ldid, created


class LdId(models.Model):
    ld_id = models.URLField(unique=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    objects = LdIdQuerySet.as_manager()

    def delete_if_can(self, actor: RemoteActor) -> None:
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
