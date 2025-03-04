from __future__ import annotations
import icontract
from functools import cached_property
from typing import cast, Any
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from urllib.parse import urlparse
from django.contrib.sites.models import Site
from django.db import models
from . import activity_dicts, activity_schema
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

@dataclass
class LdDonorGetOrCreator:
    queryset: "LdIdQuerySet"
    ld_id: activity_dicts.LdIdUrl
    data: activity_dicts.ActivitypubContact

    @cached_property
    def archive(self) -> Archive | None:
        if len(self.data.get("attributedTo", [])) > 0:
            return Archive.objects.get_or_create_by_profile(
                profile=self.data["attributedTo"][0]
            )[0]
        else:
            return None

    def reconcile(self, db_obj: Donor) -> None:
        db_obj.reconcile(self.data)

    def ldid(self, db_obj: Donor) -> "LdId":
        ct = ContentType.objects.get_for_model(Donor)
        ldid, _ = self.queryset.get_or_create(
            ld_id=self.data["id"],
            defaults={"content_type": ct, "object_id": db_obj.id},
        )
        return ldid

    @property
    @icontract.ensure(lambda self, result: result[1] == (result[0] is not None))
    @icontract.ensure(lambda self, result: result[0] is None or result[0].content_object is not None)
    def object(self) -> tuple["LdId" | None, bool]:
        if (
            len(self.data.get("attributedTo", [])) == 0 or
            urlparse(self.data["attributedTo"][0]).netloc
            != urlparse(self.ld_id).netloc
        ):
            return None, False
        archive = self.archive
        if not archive:
            return None, False
        db_obj = Donor()
        db_obj.archive = archive
        self.reconcile(db_obj)

        return self.ldid(db_obj), True

@dataclass
class LdPlaceGetOrCreator:
    queryset: "LdIdQuerySet"
    ld_id: activity_dicts.LdIdUrl
    data: activity_dicts.ActivitypubLocation

@dataclass
class LdObjectGetOrCreator:
    queryset: "LdIdQuerySet"
    ld_id: activity_dicts.LdIdUrl

    @cached_property
    def is_local(self) -> bool:
        server_domain = urlparse(self.ld_id).netloc
        return Site.objects.filter(domain=server_domain).exists()

    @property
    def resolved(self) -> ResolveResults | None:
        try:
            return resolve(self.ld_id)
        except Resolver404:
            return None

    @cached_property
    @icontract.ensure(lambda self, result: not result or result.archive.type == Archive.ArchiveType.LOCAL)
    def resolved_donor(self) -> Donor | None:
        assert self.resolved
        try:
            return Donor.objects.get(
                archive__slug=self.resolved.match.kwargs["short_name"],
                archive__type=Archive.ArchiveType.LOCAL,
                pk=self.resolved.match.kwargs['pk'],
            )
        except Donor.DoesNotExist:
            return None

    @cached_property
    def existing_ldid(self) -> "LdId" | None:
        try:
            return self.queryset.get(ld_id=self.ld_id)
        except self.queryset.model.DoesNotExist:
            return None

    @cached_property
    @icontract.ensure(lambda self, result: not result or result.owner == None)
    def resolved_place(self) -> Place | None:
        assert self.resolved
        try:
            return Place.objects.get(
                pk=self.resolved.match.kwargs['pk'],
                owner__isnull=True,
            )
        except Place.DoesNotExist:
            return None

    @cached_property
    def remote_data(self) -> dict[str, Any]:
        return requests.get(
            self.ld_id,
            headers={
                "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
        ).json()

    @property
    @icontract.ensure(lambda self, result: (not result[1] or result[0] is not None) and (result[0] is None or result[0].content_object is not None))
    def object(self) -> tuple["LdId" | None, bool]:
        if self.is_local:
            if (
                self.resolved and
                self.resolved.match.namespaces
                == ["kronofoto", "activitypub_data", "archives", "contributors"]
                and self.resolved.match.url_name == "detail"
            ):
                donor = self.resolved_donor
                if donor is not None:
                    return (
                        LdId(
                            content_object=self.resolved_donor,
                        ),
                        False,
                    )
            elif (
                self.resolved and
                self.resolved.match.namespaces
                == ["kronofoto"]
                and self.resolved.match.url_name == "activitypub-main-service-places"
            ):
                content_object = self.resolved_place
                if content_object is not None:
                    return (
                        LdId(
                            content_object=content_object,
                        ),
                        False,
                    )
            return None, False

        local = self.existing_ldid
        if local is not None:
            if local.content_object is not None:
                return (local, False)
            else:
                local.delete()

        object = self.remote_data
        if object is None or not isinstance(object, dict) or object.get("id") != self.ld_id:
            return (None, False)

        if object.get("type") == "Contact":
            getter = self.donorgetorcreate(object)
            if getter:
                return getter.object
            else:
                return None, False
        if object.get("type") == "Location":
            getter = self.placegetorcreate(object)
            if getter:
                return getter.object
            else:
                return None, False
        else:
            return None, False

    def placegetorcreate(self, object: dict[str, Any]) -> Any | None:
        try:
            data: activity_dicts.ActivitypubLocation = (
                activity_schema.PlaceSchema().load(object)
            )
            return LdPlaceGetOrCreator(ld_id=self.ld_id, data=data, queryset=self.queryset)
        except ValidationError as e:
            print(e, object)
            return None

    def donorgetorcreate(self, object: dict[str, Any]) -> LdDonorGetOrCreator | None:
        try:
            data: activity_dicts.ActivitypubContact = (
                activity_schema.Contact().load(object)
            )
            return LdDonorGetOrCreator(ld_id=self.ld_id, data=data, queryset=self.queryset)
        except ValidationError as e:
            print(e, object)
            return None

@dataclass
class NewLdIdPlace:
    queryset: "LdIdQuerySet"
    owner: RemoteActor
    object: activity_dicts.ActivitypubLocation
    place_upserter: "PlaceUpserter"

    @property
    def result(self) -> tuple["LdId" | None, bool]:
        ct = ContentType.objects.get_for_model(Place)
        place = Place.objects.create(
            place_type=self.place_upserter.place_type,
            name=self.object['name'],
            geom=self.object['geom'],
            owner=self.owner,
            parent=self.place_upserter.parent,
        )
        result = self.queryset.update_or_create(
            ld_id=self.object['id'],
            defaults={"content_type": ct, "content_object": place},
        )
        return result[0], True

@dataclass
class UpdateLdIdPlace:
    ld_id: "LdId"
    owner: RemoteActor
    object: activity_dicts.ActivitypubLocation
    place_upserter: "PlaceUpserter"

    @property
    @icontract.ensure(lambda self, result: not result[1])
    @icontract.ensure(lambda self, result: (
        ldid := result[0],
        ldid is None or (isinstance(ldid.content_object, Place) and self.owner.id == ldid.content_object.owner.id)
        )[-1]
    )
    def result(self) -> tuple["LdId" | None, bool]:
        place = self.ld_id.content_object
        if not isinstance(place, Place) or place.owner is None or place.owner.id != self.owner.id:
            return None, False
        place.geom = self.object.get('geom')
        place.place_type = self.place_upserter.place_type
        place.name = self.object.get('name')
        place.parent = self.place_upserter.parent
        place.save()
        return self.ld_id, False

@dataclass
class PlaceUpserter:
    queryset: "LdIdQuerySet"
    owner: RemoteActor
    object: activity_dicts.ActivitypubLocation

    @cached_property
    def place_type(self) -> PlaceType:
        return PlaceType.objects.get_or_create(name=self.object['place_type'])[0]

    @cached_property
    def parent(self) -> Place | None:
        parent = self.object.get("parent")
        if parent:
            ldid, created = self.queryset.get_or_create_ld_object(parent)
            if ldid is not None and isinstance(ldid.content_object, Place):
                return ldid.content_object
        return None

    @cached_property
    def upserter(self) -> UpdateLdIdPlace | NewLdIdPlace:
        try:
            placeid = self.object['id']
            return UpdateLdIdPlace(
                ld_id=self.queryset.get(ld_id=placeid),
                owner=self.owner,
                object=self.object,
                place_upserter=self,
            )
        except self.queryset.model.DoesNotExist:
            return NewLdIdPlace(
                owner=self.owner,
                queryset=self.queryset,
                object=self.object,
                place_upserter=self,
            )



    @property
    def result(self) -> tuple["LdId" | None, bool]:
        return self.upserter.result

class LdIdQuerySet(models.QuerySet["LdId"]):
    def get_or_create_ld_object(
        self, ld_id: activity_dicts.LdIdUrl
    ) -> tuple["LdId" | None, bool]:
        return LdObjectGetOrCreator(queryset=self, ld_id=ld_id).object

    @icontract.ensure(
        lambda self, owner, object, result: result[0] is None
        or (isinstance(result[0].content_object, Place) and result[0].content_object.owner.id == owner.id)
    )
    def update_or_create_ld_service_object(
        self, owner: RemoteActor, object: activity_dicts.ActivitypubLocation
    ) -> tuple["LdId" | None, bool]:
        return PlaceUpserter(queryset=self, owner=owner, object=object).result

    @icontract.require(
        lambda self, owner, object: owner.type == Archive.ArchiveType.REMOTE
    )
    @icontract.ensure(
        lambda self, owner, object, result: result[0] is None
        or not isinstance(result[0].content_object, Donor)
        or object["type"] == "Contact"
    )
    @icontract.ensure(
        lambda self, owner, object, result: result[0] is None
        or not isinstance(result[0].content_object, Photo)
        or object["type"] == "Image"
    )
    def update_or_create_ld_object(
        self, owner: "Archive", object: activity_dicts.ActivitypubData
    ) -> tuple["LdId" | None, bool]:
        "This function is valid for object['id'] that are external domains only."
        "This function is only valid for Contact/Donor and Image/Photo, which should be all that is needed."
        ldid = None
        try:
            ldid = self.get(ld_id=object["id"])
            db_obj = ldid.content_object
            if db_obj and db_obj.archive.id != owner.id:
                db_obj = None
            else:
                created = False
        except self.model.DoesNotExist:
            if object["type"] == "Contact":
                db_obj = Donor()
                db_obj.archive = owner
                created = True
            elif object["type"] == "Image":
                db_obj = Photo()
                db_obj.archive = owner
                created = True
        if not db_obj:
            return (None, False)
        if isinstance(db_obj, Donor) and object["type"] == "Contact":
            db_obj.reconcile(object)
            ct = ContentType.objects.get_for_model(Donor)
        elif isinstance(db_obj, Photo) and object["type"] == "Image":
            donor, _ = self.get_or_create_ld_object(object["contributor"])
            if not donor or not donor.content_object:
                return None, False
            db_obj.reconcile(object, donor.content_object)
            ct = ContentType.objects.get_for_model(Photo)
            db_obj.save()
            for tag in object["tags"]:
                new_tag, _ = Tag.objects.get_or_create(tag=tag)
                PhotoTag.objects.get_or_create(
                    tag=new_tag, photo=db_obj, accepted=True
                )
            for term in object["terms"]:
                db_obj.terms.add(Term.objects.get_or_create(term=term)[0])
        ldid, _ = self.get_or_create(
            ld_id=object["id"], defaults={"content_type": ct, "object_id": db_obj.id}
        )
        return ldid, created


class LdId(models.Model):
    ld_id = cast(
        "models.Field[activity_dicts.LdIdUrl, activity_dicts.LdIdUrl]",
        models.URLField(unique=True),
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    objects = LdIdQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                name="unique_content_id_per_object",
            ),
        ]
