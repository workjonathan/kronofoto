from __future__ import annotations
import icontract
from typing import cast
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from urllib.parse import urlparse
from django.contrib.sites.models import Site
from django.db import models
from . import activity_dicts, activity_schema
from .archive import RemoteActor
import requests
from marshmallow.exceptions import ValidationError
from .place import Place, PlaceType
from .donor import Donor
from .photo import Photo, PhotoTag
from .archive import Archive
from .tag import Tag
from .term import Term

from fortepan_us.kronofoto.reverse import reverse, resolve

class LdIdQuerySet(models.QuerySet["LdId"]):
    def get_or_create_ld_object(
        self, ld_id: activity_dicts.LdIdUrl
    ) -> tuple["LdId" | None, bool]:
        server_domain = urlparse(ld_id).netloc
        if Site.objects.filter(domain=server_domain).exists():
            resolved = resolve(ld_id)
            if (
                resolved.match.namespaces
                == ["kronofoto", "activitypub_data", "archives", "contributors"]
                and resolved.match.url_name == "detail"
            ):
                return (
                    LdId(
                        content_object=Donor.objects.get(
                            archive__slug=resolved.match.kwargs["short_name"]
                        ),
                        id=resolved.match.kwargs["pk"],
                    ),
                    False,
                )
            return None, False
        try:
            return (self.get(ld_id=ld_id), False)
        except self.model.DoesNotExist:
            object = requests.get(
                ld_id,
                headers={
                    "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
            ).json()
            assert object["id"] == ld_id
            if object["type"] == "Contact":
                try:
                    data: activity_dicts.ActivitypubContact = (
                        activity_schema.Contact().load(object)
                    )
                    if (
                        urlparse(data["attributedTo"][0]).netloc
                        != urlparse(ld_id).netloc
                    ):
                        return None, False
                    archive, _ = Archive.objects.get_or_create_by_profile(
                        profile=data["attributedTo"][0]
                    )
                    if not archive:
                        return None, False
                    db_obj = Donor()
                    db_obj.archive = archive
                    db_obj.reconcile(data)
                    ct = ContentType.objects.get_for_model(Donor)
                    ldid, _ = self.get_or_create(
                        ld_id=object["id"],
                        defaults={"content_type": ct, "object_id": db_obj.id},
                    )
                    return ldid, True
                except ValidationError as e:
                    print(e, object)
                    return None, False
            else:
                raise NotImplementedError

    @icontract.require(lambda self, owner, object: not owner.archive_set.exists())
    @icontract.ensure(
        lambda self, owner, object, result: result[0] is None
        or (isinstance(result[0].content_object, Place) and result[0].content_object.owner.id == owner.id)
    )
    def update_or_create_ld_service_object(
        self, owner: RemoteActor, object: activity_dicts.ActivitypubLocation
    ) -> tuple["LdId" | None, bool]:
        placeid = object['id']
        try:
            ld_id = LdId.objects.get(ld_id=placeid)
            place = ld_id.content_object
            if not isinstance(place, Place) or place.owner.id != owner.id:
                return None, False
            place.geom = object['geom']
            place.place_type = PlaceType.objects.get_or_create(name=object['place_type'])[0]
            place.name = object['name']
            place.save()
            return ld_id, False
        except LdId.DoesNotExist:
            ct = ContentType.objects.get_for_model(Place)
            place = Place.objects.create(
                place_type=PlaceType.objects.get_or_create(name=object['place_type'])[0],
                name=object['name'],
                geom=object['geom'],
                owner=owner,
            )
            result = LdId.objects.update_or_create(
                ld_id=object['id'],
                defaults={"content_type": ct, "content_object": place},
            )
            return result[0], True

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
