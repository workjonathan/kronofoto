from __future__ import annotations
from marshmallow import Schema, fields, pre_dump, post_load, pre_load, EXCLUDE, post_dump
from marshmallow import validate
from marshmallow.exceptions import ValidationError
from typing import Any, Dict, Union, TypeVar, List, Optional
from fortepan_us.kronofoto import models
from fortepan_us.kronofoto.reverse import reverse
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.db.models import QuerySet
from . import activity_dicts
import json
import icontract

T = TypeVar("T")


class RingIsClosed(validate.Validator):
    def __call__(self, value: List[T]) -> List[T]:
        if len(value) > 0 and value[0] != value[-1]:
            raise validate.ValidationError("This shape must be closed (the first value and last value should be equal).")
        return value

class ObjectSchema(Schema):
    _context = fields.Raw(data_key="@context")
    id = fields.Url(required=True)
    # type = fields.Str()
    attributedTo = fields.List(fields.Url())
    url = fields.Url(relative=True, required=False)
    content = fields.Str()

class ActorSchema(Schema):
    type = fields.Str() #("Organization")
    id = fields.Url(relative=True, required=True)
    name = fields.Str(required=True)
    publicKey = fields.Dict(keys=fields.Str(), values=fields.Str(), required=True)

    inbox = fields.Url(relative=True)
    outbox = fields.Url(relative=True)
    following = fields.List(fields.Url(), required=True)
    followers = fields.List(fields.Url(), required=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.ActorValue:
        return activity_dicts.ActorValue(
            **{k:v for k, v in data.items() if k not in ['type']}
        )

class ServiceActorSchema(Schema):
    type = fields.Constant("PlaceService")
    id = fields.Url(relative=True, required=True)
    name = fields.Str(required=True)
    publicKey = fields.Dict(keys=fields.Str(), values=fields.Str(), required=True)

    inbox = fields.Url(relative=True, required=True)
    outbox = fields.Url(relative=True, required=True)
    places = fields.Url(relative=True, required=True)
    following = fields.List(fields.Url(), required=True)
    followers = fields.List(fields.Url(), required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.ServiceActorValue:
        return activity_dicts.ServiceActorValue(
            **{k: v for (k, v) in data.items() if k not in ['type']}
        )

class ArchiveSchema(Schema):
    type = fields.Constant("ArchiveActor")
    id = fields.Url(relative=True, required=True)
    name = fields.Str(required=True)
    slug = fields.Str(required=True)
    publicKey = fields.Dict(keys=fields.Str(), values=fields.Str(), required=True)

    inbox = fields.Url(relative=True, required=True)
    outbox = fields.Url(relative=True, required=True)
    contributors = fields.Url(relative=True, required=True)
    photos = fields.Url(relative=True, required=True)
    following = fields.Url(relative=True, required=True)
    followers = fields.Url(relative=True, required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.ArchiveValue:
        return activity_dicts.ArchiveValue(
            **{k: v for (k, v) in data.items() if k not in ['type']}
        )

    class Meta:
        unknown = EXCLUDE

    @pre_dump
    def extract_fields_from_object(
        self, object: "models.Archive", **kwargs: Any
    ) -> activity_dicts.ArchiveDict:
        return {
            "id": activity_dicts.str_to_ldidurl(
                reverse(
                    "kronofoto:activitypub_data:archives:actor",
                    kwargs={"short_name": object.slug},
                )
            ),
            "name": object.name,
            "slug": object.slug,
            "inbox": activity_dicts.str_to_url(
                reverse(
                    "kronofoto:activitypub_data:archives:inbox",
                    kwargs={"short_name": object.slug},
                )
            ),
            "outbox": activity_dicts.str_to_url(
                reverse(
                    "kronofoto:activitypub_data:archives:outbox",
                    kwargs={"short_name": object.slug},
                )
            ),
            "contributors": activity_dicts.str_to_url(
                reverse(
                    "kronofoto:activitypub_data:archives:contributors:page",
                    kwargs={"short_name": object.slug},
                )
            ),
            "photos": activity_dicts.str_to_url(
                reverse(
                    "kronofoto:activitypub_data:archives:photos:page",
                    kwargs={"short_name": object.slug},
                )
            ),
            "followers": activity_dicts.str_to_url(
                reverse(
                    "kronofoto:activitypub_data:archives:followers",
                    kwargs={"short_name": object.slug},
                )
            ),
            "following": activity_dicts.str_to_url(
                reverse(
                    "kronofoto:activitypub_data:archives:following",
                    kwargs={"short_name": object.slug},
                )
            ),
            "publicKey": {
                "id": object.keyId,
                "owner": reverse(
                    "kronofoto:activitypub_data:archives:actor",
                    kwargs={"short_name": object.slug},
                ),
                "publicKeyPem": object.guaranteed_public_key(),  # type: ignore
            },
        }


class GeomField(fields.Field):
    def _serialize(
        self, value: Any, attr: Any, obj: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        elif isinstance(value, MultiPolygon):
            return MultiPolygonSchema().dump(value)
        elif isinstance(value, Point):
            return PointSchema().dump(value)

        else:
            raise ValueError(value)

    def _deserialize(self, value: Dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        if value["type"] in [
            "MultiPolygon",
        ]:
            return MultiPolygonSchema().load(value)
        elif value['type'] in ['Point']:
            return PointSchema().load(value)
        raise ValueError(value["type"])

class PointSchema(Schema):
    type = fields.Constant("Point", required=True)
    coordinates = fields.Tuple((fields.Float(), fields.Float()), required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> Point:
        return Point(*data['coordinates'])

    @pre_dump
    def extract_fields_from_object(
        self, object: "Point", **kwargs: Any
    ) -> Dict[str, Any]:
        return {
            "type": "Point",
            "coordinates": object.coords,
        }

class MultiPolygonSchema(Schema):
    type = fields.Constant("MultiPolygon", required=True)
    coordinates = fields.List(
        fields.List(
            fields.List(
                fields.Tuple((
                    fields.Float(),
                    fields.Float(),
                )),
                validate=[validate.Length(min=4), RingIsClosed()],
            ),
            validate=validate.Length(min=1)
        ),
        validate=validate.Length(min=1),
        required=True,
    )

    @pre_dump
    def extract_fields_from_object(
        self, object: "MultiPolygon", **kwargs: Any
    ) -> Dict[str, Any]:
        return {
            "type": "MultiPolygon",
            "coordinates": object.coords,
        }

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> MultiPolygon:
        return MultiPolygon([Polygon(*poly) for poly in data['coordinates']])


class PlaceSchema(Schema):
    id = fields.Url(required=True)
    name = fields.Str(required=True)
    attributedTo = fields.List(fields.Url(), required=True)
    parent = fields.Url(relative=True)
    geom = GeomField()
    placeType = fields.Str(required=True)
    fullName = fields.Str(required=True)
    type = fields.Constant("Location", required=True)

    class Meta:
        unknown = EXCLUDE

    @post_dump
    def remove_nones(self, data: Dict[str, Any], many: bool, **kwargs: Any) -> Dict[str, Any]:
        return {k: v for (k,v) in data.items() if v is not None}
    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.PlaceValue:
        return activity_dicts.PlaceValue(
            id=data['id'],
            name=data['name'],
            fullName=data['fullName'],
            parent=data.get('parent'),
            attributedTo=data['attributedTo'],
            placeType=data['placeType'],
            geom=data.get('geom'),
        )

    #@pre_dump
    def extract_fields_from_object(
        self, object: "models.Place", **kwargs: Any
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        data["id"] = reverse(
            "kronofoto:activitypub-main-service-places", kwargs={"pk": object.id}
        )
        data["name"] = object.name
        if object.geom:
            data["geom"] = json.loads(object.geom.json)
        if object.parent:
            data["parent"] = reverse(
                "kronofoto:activitypub-main-service-places",
                kwargs={"pk": object.parent.id},
            )
        return data


class LinkSchema(Schema):
    href = fields.Url()

class AttachmentSchema(Schema):
    type = fields.Constant("Page", required=True)
    name = fields.Str(required=True)
    url = fields.Url(required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.PageValue:
        return activity_dicts.PageValue(
            name=data['name'],
            url=data['url'],
        )

class CategorySchema(Schema):
    slug = fields.Str(required=True)
    name = fields.Str(required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.CategoryValue:
        return activity_dicts.CategoryValue(**data)


class Image(Schema):
    id = fields.Url(required=True)
    url = fields.Url(relative=True, required=False)
    content = fields.Str(required=True)
    category = fields.Nested(CategorySchema, required=True)
    type = fields.Constant("Image", required=True)
    year = fields.Integer()
    circa = fields.Boolean(required=True)
    is_published = fields.Boolean(required=True)
    contributor = fields.Url(relative=True)
    terms = fields.List(fields.Str)
    tags = fields.List(fields.Str)
    place = fields.Url(relative=True)
    height = fields.Integer(required=True)
    width = fields.Integer(required=True)
    attachment = fields.List(
        fields.Nested(AttachmentSchema),
        required=True,
        validate=[validate.Length(min=1),
    ])

    class Meta:
        unknown = EXCLUDE

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.PhotoValue:
        return activity_dicts.PhotoValue(**{
            k: v for (k, v) in data.items() if k not in ['type']
        })

    @post_dump
    def remove_nones(self, data: Dict[str, Any], many: bool, **kwargs: Any) -> Dict[str, Any]:
        return {k: v for (k,v) in data.items() if v is not None}

    #@pre_dump
    def extract_fields_from_object(
        self, object: "models.Photo", **kwargs: Any
    ) -> Dict[str, Any]:
        data = {
            "id": reverse(
                "kronofoto:activitypub_data:archives:photos:detail",
                kwargs={"short_name": object.archive.slug, "pk": object.id},
            ),
            "attributedTo": [
                reverse(
                    "kronofoto:activitypub_data:archives:actor",
                    kwargs={"short_name": object.archive.slug},
                )
            ],
            "content": object.caption,
            "year": object.year,
            "url": object.original.url,
            "category": object.category,
            "circa": object.circa,
            "is_published": object.is_published,
            "type": "Image",
            "terms": [t.term for t in object.terms.all()],
            "tags": [t.tag for t in object.get_accepted_tags()],
        }
        if object.place:
            data["place"] = reverse(
                "kronofoto:activitypub-main-service-places",
                kwargs={"pk": object.place.id},
            )
        if object.donor:
            data["contributor"] = reverse(
                "kronofoto:activitypub_data:archives:contributors:detail",
                kwargs={"short_name": object.donor.archive.slug, "pk": object.donor.id},
            )
        return data


class Contact(Schema):
    id = fields.Url(required=True)
    type = fields.Constant("Contact", required=True)
    attributedTo = fields.List(fields.Url(), required=True)
    name = fields.Str()
    firstName = fields.Str(required=True)
    lastName = fields.Str(required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.DonorValue:
        return activity_dicts.DonorValue(**{
            k: v for (k, v) in data.items() if k not in ["type"]
        })

    #@pre_dump
    def extract_fields_from_object(
        self, object: "models.Donor", **kwargs: Any
    ) -> activity_dicts.ActivitypubContact:
        return {
            "id": activity_dicts.str_to_ldidurl(
                reverse(
                    "kronofoto:activitypub_data:archives:contributors:detail",
                    kwargs={"short_name": object.archive.slug, "pk": object.id},
                )
            ),
            "attributedTo": [
                activity_dicts.str_to_ldidurl(
                    reverse(
                        "kronofoto:activitypub_data:archives:actor",
                        kwargs={"short_name": object.archive.slug},
                    )
                )
            ],
            "name": object.display_format(),
            "firstName": object.first_name,
            "lastName": object.last_name,
            "type": "Contact",
        }


class PageItem(fields.Field):
    def _serialize(
        self,
        value: Union["models.Donor", "models.Photo"],
        attr: Any,
        obj: Any,
        **kwargs: Any
    ) -> Dict[str, Any]:
        if isinstance(value, models.Donor):
            return Contact().dump(value)
        else:
            return Image().dump(value)

    def _deserialize(
        self, value: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Union[Contact, Image]:
        if value["type"] == "Contact":
            return Contact().load(value)
        return Image().load(value)


class KronofotoObjectField(fields.Field):
    def _serialize(
        self,
        value: Any,
        attr: Any,
        obj: Any,
        **kwargs: Any
    ) -> Dict[str, Any]:
        if isinstance(value, activity_dicts.PhotoValue):
            return Image().dump(value)
        elif isinstance(value, activity_dicts.DonorValue):
            return Contact().dump(value)
        elif isinstance(value, activity_dicts.PlaceValue):
            return PlaceSchema().dump(value)
        raise ValueError(value)

    def _deserialize(
        self, value: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> activity_dicts.PhotoValue | activity_dicts.DonorValue:
        if value["type"] in ["Image"]:
            return Image(context=self.context).load(value)
        if value["type"] in ["Contact"]:
            return Contact(context=self.context).load(value)
        if value["type"] in ["Location"]:
            return PlaceSchema(context=self.context).load(value)
        raise ValidationError(value["type"])

class ObjectOrLinkField(fields.Field):
    def _serialize(
        self,
        value: Union["models.Donor", "models.Photo"],
        attr: Any,
        obj: Any,
        **kwargs: Any
    ) -> Dict[str, Any]:
        if isinstance(value, models.Donor):
            return Contact().dump(value)
        elif isinstance(value, models.Photo):
            return Image().dump(value)
        else:
            return value

    def _deserialize(
        self, value: Union[str, Dict[str, Any]], *args: Any, **kwargs: Any
    ) -> Any:
        return None
        #if isinstance(value, str):
        #    return LinkSchema(context=self.context).load({"href": value})
        #if value["type"] in [
        #    "Accept",
        #    "Follow",
        #]:
        #    return ActivitySchema(context=self.context).load(value)
        #if value["type"] in [
        #    "Image",
        #]:
        #    return Image(context=self.context).load(value)
        #if value["type"] in [
        #    "Contact",
        #]:
        #    return Contact(context=self.context).load(value)
        #raise ValueError(value["type"])


class Collection(Schema):
    _context = fields.Raw(data_key="@context")
    id = fields.Url(required=True)
    summary = fields.Str(required=True)
    first = fields.Nested(lambda: CollectionPage(), required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.CollectionValue:
        return activity_dicts.CollectionValue(
            id=data['id'],
            summary=data["summary"],
            first=data['first'],
        )

    #@pre_dump
    def extract_fields_from_object(
        self,
        object: "Union[QuerySet[models.Photo], QuerySet[models.Donor]]",
        **kwargs: Any
    ) -> Dict[str, Any]:
        return {
            "id": self.context["url"],
            "summary": self.context["summary"],
            "first": object,
        }


class CollectionPage(Schema):
    id = fields.Url(required=True)
    next = fields.Url(required=False)
    items = fields.List(KronofotoObjectField, required=True)

    @post_dump
    def remove_nones(self, data: Dict[str, Any], many: bool, **kwargs: Any) -> Dict[str, Any]:
        return {k: v for (k,v) in data.items() if v is not None}

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.CollectionPageValue:
        return activity_dicts.CollectionPageValue(
            id=data['id'],
            next=data.get("next"),
            items=data['items'],
        )

    #@pre_dump
    #def extract_fields_from_object(
    #    self,
    #    object: activity_dicts.CollectionPageValue,
    #    **kwargs: Any
    #) -> Dict[str, Any]:
    #    next = (
    #        "{}?pk={}".format(
    #            self.context["url"],
    #            object[99].pk,
    #        )
    #        if object.count() == 100
    #        else None
    #    )
    #    return {
    #        "id": "{}?pk=0".format(self.context["url"]),
    #        "items": object,
    #        "next": next,
    #    }


class DeleteActivitySchema(Schema):
    _context = fields.Raw(data_key="@context")
    type = fields.Constant("Delete", required=True)
    id = fields.Url(required=True)
    actor = fields.Url(required=True)
    object = fields.Url(required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.DeleteValue:
        return activity_dicts.DeleteValue(
            id=data['id'],
            actor=data['actor'],
            object=data['object'],
        )

class CreateActivitySchema(Schema):
    _context = fields.Raw(data_key="@context")
    type = fields.Constant("Create", required=True)
    id = fields.Url(required=True)
    actor = fields.Url(required=True)
    object = KronofotoObjectField(required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.CreateValue:
        return activity_dicts.CreateValue(
            id=data['id'],
            actor=data['actor'],
            object=data['object'],
        )

class UpdateActivitySchema(Schema):
    _context = fields.Raw(data_key="@context")
    type = fields.Constant("Update", required=True)
    id = fields.Url(required=True)
    actor = fields.Url(required=True)
    object = KronofotoObjectField(required=True)
    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.UpdateValue:
        return activity_dicts.UpdateValue(
            id=data['id'],
            actor=data['actor'],
            object=data['object'],
        )

class FollowActivitySchema(Schema):
    _context = fields.Raw(data_key="@context")
    type = fields.Constant("Follow", required=True)
    id = fields.Url(required=True)
    actor = fields.Url(required=True)
    object = fields.Url(required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.FollowValue:
        return activity_dicts.FollowValue(
            id=data['id'],
            actor=data['actor'],
            object=data['object'],
        )

class AcceptActivitySchema(Schema):
    _context = fields.Raw(data_key="@context")
    type = fields.Constant("Accept", required=True)
    id = fields.Url(required=True)
    actor = fields.Url(required=True)
    object = fields.Nested(FollowActivitySchema, required=True)

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.AcceptValue:
        return activity_dicts.AcceptValue(
            id=data['id'],
            actor=data['actor'],
            object=data['object'],
        )

class ActivitySchema:
    schemas = {
        "Delete": DeleteActivitySchema(),
        "Create": CreateActivitySchema(),
        "Update": UpdateActivitySchema(),
        "Follow": FollowActivitySchema(),
        "Accept": AcceptActivitySchema(),
    }
    def load(self, data: Dict[str, Any]) -> activity_dicts.ActivitypubValue | None:
        type_ = data.get("type")
        if type_ in self.schemas:
            try:
                return self.schemas[type_].load(data)
            except ValidationError:
                pass
        return None

    def dump(self, thing: Any) -> Dict[str, Any] | None:
        type_ = thing.get("type")
        if type_ in self.schemas:
            try:
                return self.schemas[type_].dump(thing)
            except ValidationError:
                pass
        return None


class ActorCollectionSchema(Schema):
    _context = fields.Raw(data_key="@context")
    id = fields.Url(required=True)
    attributedTo = fields.List(fields.Url())
    url = fields.Url(relative=True, required=False)
    content = fields.Str()
    items = fields.List(ObjectOrLinkField)
    totalItems = fields.Integer()

    @pre_dump
    def extract_fields_from_object(self, object: Any, **kwargs: Any) -> Dict[str, Any]:
        return {
            "totalItems": object.count(),
            "items": [actor.profile for actor in object],
        }
