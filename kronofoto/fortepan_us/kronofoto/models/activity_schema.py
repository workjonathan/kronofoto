from marshmallow import Schema, fields, pre_dump, post_load, pre_load, EXCLUDE
from marshmallow import validate
from typing import Any, Dict, Union, TypeVar, List
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


class GeomField(fields.Field):
    def _serialize(
        self, value: Any, attr: Any, obj: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        return MultiPolygonSchema().dump(value)

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

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> MultiPolygon:
        return MultiPolygon([Polygon(*poly) for poly in data['coordinates']])


class PlaceSchema(ObjectSchema):
    name = fields.Str(required=True)
    attributedTo = fields.List(fields.Url(), required=True)
    parent = fields.Url(relative=True)
    geom = GeomField()
    placeType = fields.Str(required=True)
    fullName = fields.Str(required=True)
    type = fields.Constant("Location", required=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> activity_dicts.PlaceValue:
        return activity_dicts.PlaceValue(
            name=data['name'],
            fullName=data['fullName'],
            parent=data.get('parent'),
            attributedTo=data['attributedTo'],
            placeType=data['placeType'],
            geom=data.get('geom'),
        )

    @pre_dump
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


class CategorySchema(Schema):
    slug = fields.Str()
    name = fields.Str()


class Image(ObjectSchema):
    id = fields.Url()
    category = fields.Nested(CategorySchema)
    year = fields.Integer()
    circa = fields.Boolean()
    is_published = fields.Boolean()
    contributor = fields.Url(relative=True)
    terms = fields.List(fields.Str)
    tags = fields.List(fields.Str)
    place = fields.Url(relative=True)

    @pre_dump
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
                kwargs={"short_name": object.archive.slug, "pk": object.donor.id},
            )
        return data


class Contact(ObjectSchema):
    id = fields.Url()
    type = fields.Constant("Contact")
    attributedTo = fields.List(fields.Url())
    name = fields.Str()
    firstName = fields.Str()
    lastName = fields.Str()

    @pre_dump
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
        if isinstance(value, str):
            return LinkSchema(context=self.context).load({"href": value})
        if value["type"] in [
            "Accept",
            "Follow",
        ]:
            return ActivitySchema(context=self.context).load(value)
        if value["type"] in [
            "Image",
        ]:
            return Image(context=self.context).load(value)
        if value["type"] in [
            "Contact",
        ]:
            return Contact(context=self.context).load(value)
        raise ValueError(value["type"])


class Collection(ObjectSchema):
    summary = fields.Str()
    first = fields.Nested(lambda: CollectionPage())

    @pre_dump
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


class CollectionPage(Collection):
    id = fields.Url()
    next = fields.Url(required=False, allow_none=True)
    items = fields.List(PageItem)

    @pre_dump
    def extract_fields_from_object(
        self,
        object: "Union[QuerySet[models.Photo], QuerySet[models.Donor]]",
        **kwargs: Any
    ) -> Dict[str, Any]:
        next = (
            "{}?pk={}".format(
                self.context["url"],
                object[99].pk,
            )
            if object.count() == 100
            else None
        )
        return {
            "id": "{}?pk=0".format(self.context["url"]),
            "items": object,
            "next": next,
        }


class ActivitySchema(ObjectSchema):
    actor = fields.Url()
    object = ObjectOrLinkField()
    to = fields.List(fields.Url())

    @pre_dump
    def extract_fields_from_object(
        self, object: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        if isinstance(object["actor"], models.Archive):
            object["actor"] = reverse(
                "kronofoto:activitypub_data:archives:actor",
                kwargs={"short_name": object["actor"].slug},
            )
        return object

    @pre_load
    def preload(
        self, data: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        self.fields["object"].context.setdefault("root_type", data["type"])
        return data

    @post_load
    def extract_fields_from_dict(
        self, data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        data["actor"] = models.RemoteActor.objects.get_or_create(profile=data["actor"])[
            0
        ]
        return data


class ActorCollectionSchema(ObjectSchema):
    items = fields.List(ObjectOrLinkField)
    totalItems = fields.Integer()

    @pre_dump
    def extract_fields_from_object(self, object: Any, **kwargs: Any) -> Dict[str, Any]:
        return {
            "totalItems": object.count(),
            "items": [actor.profile for actor in object],
        }
