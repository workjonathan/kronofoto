from __future__ import annotations
from django.contrib.contenttypes.models import ContentType
from typing import TypedDict, NewType, Literal, List, Union, Type, cast, Dict, Tuple, Optional, NamedTuple, Callable, Any, TypeVar, Generic
from functools import cached_property
from marshmallow import Schema, fields
from django.contrib.gis.geos import MultiPolygon, Point
from dataclasses import dataclass
from fortepan_us.kronofoto.models.archive import Archive, RemoteActor, OutboxActivity, FollowArchiveRequest, FollowServiceOutbox, FollowServiceRequest
from .ldid import LdId, LdIdQuerySet
from fortepan_us.kronofoto.models.photo import Photo, PhotoTag
from fortepan_us.kronofoto.models.donor import Donor
from fortepan_us.kronofoto.models.place import Place, PlaceType
from fortepan_us.kronofoto.models.category import Category
from fortepan_us.kronofoto.models.tag import Tag
from fortepan_us.kronofoto.models.term import Term
from fortepan_us.kronofoto.reverse import reverse, resolve, ResolveResults
from urllib.parse import urlparse
import requests
from marshmallow.exceptions import ValidationError
import icontract
from django.urls.exceptions import Resolver404
from django.contrib.sites.models import Site
from django.db.models import QuerySet
import logging

T = TypeVar("T")

@dataclass
class RemoteActorGetOrCreate:
    """Handle Remote Actor get or create."""
    queryset: QuerySet["RemoteActor"]
    profile: str

    @cached_property
    def is_local(self) -> bool:
        """Determine whether the requested LD ID is a local URL or not.

        Returns:
            bool: True if the URL is a local URL.
        """
        server_domain = urlparse(self.profile).netloc
        return Site.objects.filter(domain=server_domain).exists()

    @cached_property
    def local_actor(self) -> RemoteActor | None:
        """Get a locally cached RemoteActor, if it is available.

        Returns:
            RemoteActor | None: The RemoteActor if available. Otherwise None.
        """
        try:
            return self.queryset.get(profile=self.profile)
        except RemoteActor.DoesNotExist:
            return None

    def do_request(self) -> requests.Response:
        """Request a actor definition from a remote server.

        Returns:
            requests.Response: The Response corresponding to the profile url.
        """
        return requests.get(
            self.profile,
            headers={
                "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
        )

    def parse_json(self, data: Dict[str, Any]) -> ActorValue | None:
        """Parse and validate a dict to a ActorValue.

        Args:
            data (dict[str, Any]): A data object definition of an Actor.

        Returns:
            ActorValue | None: None if `data` is not in the right form. All required fields must be in `data` and of the correct type.
        """
        try:
            from fortepan_us.kronofoto.models.activity_schema import ActorSchema
            return ActorSchema().load(data)
        except ValidationError as e:
            print(e, data)
            return None


    def create_remoteactor(self) -> RemoteActor:
        """Creates and saves a remote actor for this profile.

        Returns:
            RemoteActor: A RemoteActor object for this profile.
        """
        return RemoteActor.objects.create(profile=self.profile)

    @property
    def actor(self) -> Tuple[RemoteActor | None, bool]:
        """Get the RemoteActor for the requested profile.

        The profile URL must be a remote URL. If the actor is already in the
        database, the record will be looked up and returned. If the actor is
        unknown, it will be requested. If the resulting JSON definition is
        valid, it will be saved for next time.

        Returns:
            (RemoteActor | None, bool): The first value is None if the profile is not for a valid actor. The second value is True if the RemoteActor was created as a result of this operation.
        """
        if self.is_local: # I don't think this should happen. At least, not in the course of processing a valid object.
            return None, False

        local_actor = self.local_actor
        if local_actor:
            return (local_actor, False)

        resp = self.do_request()
        if resp.status_code == 200:
            data = resp.json()
            parsed = self.parse_json(data)
            if parsed and parsed.id == self.profile:
                return self.create_remoteactor(), True
            else:
                return None, False
        else:
            return None, False

@dataclass
class LdDonorGetOrCreator:
    """Handle getting or creating Donors by LD-ID. Mostly creating though.
    """
    queryset: "LdIdQuerySet"
    ld_id: str
    data: DonorValue

    @cached_property
    def archive(self) -> Archive | None:
        """Get the Archive referenced in the data.

        Returns:
            Archive | None: The Archive object, or None if there is no attributedTo value or the Archive fails to load.
        """
        if len(self.data.attributedTo) > 0:
            return Archive.objects.get_or_create_by_profile(
                profile=self.data.attributedTo[0]
            )[0]
        else:
            return None

    def reconcile(self, db_obj: Donor) -> None:
        """Reconcile the data with the database."""
        self.data.reconcile(db_obj)

    @icontract.require(lambda self, db_obj: db_obj.id >= 1)
    def ldid(self, db_obj: Donor) -> "LdId":
        """Get or Create an LdId object for this Donor.

        Args:
            db_obj (Donor): The `Donor` object which should already be saved to the database.

        Returns:
            LdId: The LdId object for this Donor.
        """
        ct = ContentType.objects.get_for_model(Donor)
        ldid, _ = self.queryset.get_or_create(
            ld_id=self.data.id,
            defaults={"content_type": ct, "object_id": db_obj.id},
        )
        return ldid

    @property
    @icontract.ensure(lambda self, result: result[1] == (result[0] is not None))
    @icontract.ensure(lambda self, result: result[0] is None or result[0].content_object is not None)
    def object(self) -> tuple["LdId" | None, bool]:
        """Get the LdId object that references a Donor having the same values as
        `data` at the requested LD-ID.

        Returns:
            (LdId | None, bool): The first value is the LdId, or None if the associated Archive cannot be loaded. The second value will be True if the Donor was created as result of this call.
        """
        if (
            len(self.data.attributedTo) == 0 or
            urlparse(self.data.attributedTo[0]).netloc
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
    """Handle getting or creating Places.
    """
    queryset: "LdIdQuerySet"
    ld_id: str
    data: PlaceValue

    @cached_property
    def actor(self) -> RemoteActor | None:
        """Load an Actor referenced in the attributedTo field.

        Returns:
            RemoteActor | None: A RemoteActor or None if it cannot be loaded.
        """
        return RemoteActor.objects.get_or_create_by_profile(
            profile=self.data.attributedTo[0]
        )[0]

    def ldid(self, db_obj: Place) -> "LdId":
        """Create an LdId object for the given Place.

        Args:
            db_obj (Place): A Place object.

        Returns:
            LdId: An LdId object with a reference to this Place.
        """
        return LdId.objects.create(ld_id=self.data.id, content_object=db_obj)

    @property
    def object(self) -> tuple["LdId" | None, bool]:
        """Get an LdId object for this Place.

        Returns:
            (LdId | None, bool): The first value is the LdId object for this Place. It will be None if the owner's domain does not match the Place's domain, or the owner cannot be loaded or the parent cannot be loaded. The second will be True if the Place was created as a result of this call.
        """
        if urlparse(self.data.attributedTo[0]).netloc != urlparse(self.ld_id).netloc:
            return None, False
        actor = self.actor
        if not actor:
            return None, False
        db_obj = Place()
        db_obj.owner = actor
        if self.data.parent is not None:
            parent, created = LdObjectGetOrCreator(queryset=self.queryset, ld_id=self.data.parent).object
            if parent and parent.content_object:
                db_obj.parent = parent.content_object
        db_obj.place_type = PlaceType.objects.get_or_create(name=self.data.placeType)[0]
        db_obj.geom = self.data.geom
        db_obj.fullname = self.data.fullName
        db_obj.save()

        return self.ldid(db_obj), True

@dataclass
class LdObjectGetOrCreator:
    """Handle Getting or Creating a variety of objects.
    """
    queryset: "LdIdQuerySet"
    ld_id: str

    @cached_property
    def is_local(self) -> bool:
        """Determine whether the LD ID is local.

        Returns:
            bool: True if the LD ID refers to our own urls.
        """
        server_domain = urlparse(self.ld_id).netloc
        return Site.objects.filter(domain=server_domain).exists()

    @property
    def resolved(self) -> ResolveResults | None:
        """For local urls, attempt to resolve the URL and extract url
        parameters.

        Returns:
            ResolveResult | None: If the LD ID URL cannot be parsed, it will be None. Otherwise, the parsed URL data.
        """
        try:
            return resolve(self.ld_id)
        except Resolver404:
            return None

    @cached_property
    @icontract.ensure(lambda self, result: not result or result.archive.type == Archive.ArchiveType.LOCAL)
    def resolved_donor(self) -> Donor | None:
        """For a Resolved Donor URL, find the referenced Donor.

        Returns:
            Donor | None: A Local Donor matching the archive and ID from the LD ID URL. It will be None if there is no such Donor.
        """
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
        """Get the requested LdId if it exists.

        Returns:
            LdId | None: None if there is no such LD ID saved yet. Otherwise it is the LdId for the LD ID.
        """
        try:
            return self.queryset.get(ld_id=self.ld_id)
        except self.queryset.model.DoesNotExist:
            return None

    @cached_property
    @icontract.ensure(lambda self, result: not result or result.owner == None)
    def resolved_place(self) -> Place | None:
        """Get the Place referenced in the resolved local LD ID if it exists.

        Returns:
            Place | None: The Local Place referenced by in the ID ID url params.
        """
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
        """Make a GET request to the LD ID URL.

        Returns:
            dict[str, Any]: The request is made and the JSON is parsed to a dictionary.
        """
        return requests.get(
            self.ld_id,
            headers={
                "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
        ).json()

    @property
    @icontract.ensure(lambda self, result: (not result[1] or result[0] is not None) and (result[0] is None or result[0].content_object is not None))
    def object(self) -> tuple["LdId" | None, bool]:
        """Get an object by LD ID URL. It can be either a Donor or a Place.

        If the URL is local, parse the url and extract url parameters. Use them
        to find the right object and kind of object in the database, if it
        exists. In this case, the LdId object returned will not be from the
        database and should not be saved.

        If the URL is not local, attempt to find the object from the database to
        avoid making a network request in the event that the object is already
        known to the application.

        If the LdId object is not found, or the LdId object does not point to a
        valid object, a network request is made. The network request may fail or
        not load a JSON or not be structured correctly. If so, return None.
        Otherwise the data is saved to the database and returned.

        Returns:
            (LdId | None, bool): The first is the LdId that points to the database object. It will be None if the function fails to load the object for various reasons. The second will be True if the object was created as a result of the call.
        """
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
        """Attempt to parse `object` as a PlaceValue.

        Args:
            object (dict[str, Any]): An object, most likely from JSON.

        Returns:
            LdPlaceGetOrCreator | None: It will be None if `object` could not be parsed as a PlaceValue.
        """
        try:
            from . import activity_schema
            data: PlaceValue = (
                activity_schema.PlaceSchema().load(object)
            )
            return LdPlaceGetOrCreator(ld_id=self.ld_id, data=data, queryset=self.queryset)
        except ValidationError as e:
            print(e, object)
            return None

    def donorgetorcreate(self, object: dict[str, Any]) -> LdDonorGetOrCreator | None:
        """Attempt to parse `object` as a DonorValue.

        Args:
            object (dict[str, Any]): An object, most likely from JSON.

        Returns:
            LdDonorGetOrCreator | None: It will be None if `object` could not be parsed as a DonorValue.
        """
        try:
            from . import activity_schema
            data: DonorValue = (
                activity_schema.Contact().load(object)
            )
            return LdDonorGetOrCreator(ld_id=self.ld_id, data=data, queryset=self.queryset)
        except ValidationError as e:
            print(e, object)
            return None

@dataclass
class NewLdIdPlace:
    """Logic to handle adding a new Place from an Actor."""
    queryset: "LdIdQuerySet"
    owner: RemoteActor
    object: PlaceValue
    place_upserter: "PlaceUpserter"

    @property
    def result(self) -> tuple["LdId", Literal[True]]:
        """Get the Place's LdId.

        Returns:
            (LdId, bool): The first value is the LdId referencing a new Place. The second value is True because it will always create a new Place.
        """
        ct = ContentType.objects.get_for_model(Place)
        place = Place.objects.create(
            place_type=self.place_upserter.place_type,
            name=self.object.name,
            geom=self.object.geom,
            owner=self.owner,
            parent=self.place_upserter.parent,
            fullname=self.object.fullName,
        )
        result = self.queryset.update_or_create(
            ld_id=self.object.id,
            defaults={"content_type": ct, "content_object": place},
        )
        return result[0], True

@dataclass
class UpdateLdIdPlace:
    ld_id: "LdId"
    owner: RemoteActor
    object: PlaceValue
    place_upserter: "PlaceUpserter"

    @property
    @icontract.ensure(lambda self, result: (
        ldid := result[0],
        ldid is None or (isinstance(ldid.content_object, Place) and self.owner.id == ldid.content_object.owner.id)
        )[-1]
    )
    def result(self) -> tuple["LdId" | None, Literal[False]]:
        """Update a Place and return the LdId referencing it.

        Returns:
            (LdId | None, bool): The first value is the LdId of the updated Place. It will be None if `owner` does not have the right to update the Place. The second value will be False because this object does not create Places.
        """
        place = self.ld_id.content_object
        if not isinstance(place, Place) or place.owner is None or place.owner.id != self.owner.id:
            return None, False
        place.geom = self.object.geom
        place.place_type = self.place_upserter.place_type
        place.name = self.object.name
        place.parent = self.place_upserter.parent
        place.fullname = self.object.fullName
        place.save()
        return self.ld_id, False

@dataclass
class PlaceUpserter:
    "Update or Create a Place from a PlaceValue."
    queryset: "LdIdQuerySet"
    owner: RemoteActor
    object: PlaceValue

    @cached_property
    def place_type(self) -> PlaceType:
        """Get a PlaceType object matching the type of our `object`.

        Returns:
            PlaceType: A PlaceType of the same type given in the `object`.
        """
        return PlaceType.objects.get_or_create(name=self.object.placeType)[0]

    @cached_property
    def parent(self) -> Place | None:
        """If our `object` has a parent, get or create it by the LD ID.

        Returns:
            Place | None: The parent Place, or None if there is no Parent, or it could not be loaded.
        """
        parent = self.object.parent
        if parent:
            ldid, created = LdObjectGetOrCreator(queryset=self.queryset, ld_id=parent).object
            if ldid is not None and isinstance(ldid.content_object, Place):
                return ldid.content_object
        return None

    @cached_property
    def upserter(self) -> UpdateLdIdPlace | NewLdIdPlace:
        """Get the Place reconciliation strategy.

        Returns
            UpdateLdIdPlace | NewLdIdPlace: The strategy that will be used to save the `object` to the database.
        """
        try:
            placeid = self.object.id
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
        """Get the LdId that references a Place described in the `object`.

        Returns:
            (LdId | None, bool): The first value is the LdId referencing the Place. It will be None if the `owner` does not have privileges to update an existing Place. The second value will be True if the Place was created as a result of this call.
        """
        return self.upserter.result


class JsonError(Exception):
    """Exception class for communicating errors to views."""
    def __init__(self, message: str, status: int):
        self.message = message
        self.status = status
        super().__init__(f'{status}: {message}')


Url = NewType("Url", str)


def str_to_url(s: str) -> Url:
    return cast(Url, s)


LdIdUrl = NewType("LdIdUrl", Url)


def str_to_ldidurl(s: str) -> LdIdUrl:
    return cast(LdIdUrl, s)

ActivitypubCategory = TypedDict(
    "ActivitypubCategory",
    {
        "slug": str,
        "name": str,
    },
    total=True,
)

ActivitypubObject = TypedDict(
    "ActivitypubObject",
    {
        "@context": str,
        "id": LdIdUrl,
        # "type": str,
        "attributedTo": List[LdIdUrl],
        "url": Url,
        "content": str,
    },
    total=False,
)

@dataclass
class ArchiveValue:
    id: str
    name: str
    slug: str
    publicKey: Dict[str, str]

    inbox: str
    outbox: str
    contributors: str
    photos: str
    following: List[str]
    followers: List[str]


class ArchiveDict(ActivitypubObject, total=False):
    type: Literal["Organization"]
    name: str
    slug: str
    publicKey: Dict[str, str]

    inbox: Url
    outbox: Url
    contributors: Url
    photos: Url
    following: Url
    followers: Url


class ActivitypubContact(ActivitypubObject):
    type: Literal["Contact"]
    name: str
    firstName: str
    lastName: str


class ActivitypubImage(ActivitypubObject, total=False):
    category: ActivitypubCategory
    type: Literal["Image"]
    year: int
    circa: bool
    is_published: bool
    contributor: LdIdUrl
    terms: List[str]
    tags: List[str]
    place: LdIdUrl

@dataclass
class CategoryValue:
    """A parsed Category."""
    slug: str
    name: str

    def get_or_create(self) -> Category:
        """Get or Create a category with these values.

        Returns:
            Category: A Category with this name and slug.
        """
        return Category.objects.get_or_create(slug=self.slug, defaults={"name": self.name})[0]

def require_archive(func: Callable[[Any, Archive], str]) -> Callable[[Any, RemoteActor], str]:
    """A decorator to turn a function that takes an Archive into a function that
    takes a Remote actor.
    """
    def _(self: Any, actor: RemoteActor) -> str:
        try:
            return func(self, Archive.objects.get(actor=actor))
        except Archive.DoesNotExist:
            raise JsonError("Actor is not the correct type.", status=401)

    return _

@dataclass
class PageValue:
    """A parsed Page"""
    name: str
    url: str

@dataclass
class PhotoValue:
    """A parsed Photo"""
    id: str
    content: str
    category: CategoryValue
    circa: bool
    is_published: bool
    terms: List[str]
    tags: List[str]
    height: int
    width: int
    license: str
    attachment: List[PageValue]
    year: Optional[int]=None
    contributor: Optional[str] = None
    url: Optional[str] = None
    place: Optional[str] = None

    @staticmethod
    def from_photo(photo: Photo) -> PhotoValue:
        """Create a PhotoValue from a Photo object.

        Args:
            photo (Photo): The Photo to convert to a PhotoValue.

        Returns:
            PhotoValue: A PhotoValue representation of the Photo.
        """
        donor = None
        if photo.donor:
            donor = photo.donor.ldid()
        place = None
        width, height = photo.get_image_dimensions()
        if photo.place:
            place = photo.place.ldid()
        return PhotoValue(
            id=photo.ldid(),
            content=photo.caption,
            category=CategoryValue(
                name=photo.category.name,
                slug=photo.category.slug,
            ),
            attachment=[PageValue(name=photo.accession_number, url=photo.get_archive_url())],
            circa=photo.circa,
            height=height,
            width=width,
            license=photo.license,
            is_published=photo.is_published,
            terms=[t.term for t in photo.terms.all()],
            tags=[t.tag for t in photo.get_accepted_tags()],
            year=photo.year,
            contributor=donor,
            place=place,
            url=photo.original.url,
            #attributedTo=[
            #    reverse(
            #        "kronofoto:activitypub_data:archives:actor",
            #        kwargs={"short_name": photo.archive.slug},
            #    )
            #],
        )

    def upsert(self, actor: Archive) -> str:
        """Either add or update a photo record in the database.

        If the photo is already known and is owned by another actor, this
        operation will raise an exception.

        Args:
            actor (Archive): The actor attempting to update the Photo.

        Returns:
            str: "created" if created, else "updated"
        """
        try:
            ldid = LdId.objects.get(ld_id=self.id)
            if ldid.content_object is None:
                photo = Photo()
            elif not isinstance(ldid.content_object, Photo):
                if hasattr(ldid.content_object, "is_owned_by") and actor.actor is not None and ldid.content_object.is_owned_by(actor):
                    ldid.content_object.delete()
                    photo = Photo()
                else:
                    raise JsonError("An object with that id exists and could not be deleted.", status=400)
            else:
                photo = ldid.content_object
                if actor.actor is None or not photo.is_owned_by(actor.actor):
                    raise JsonError("An object with that id is owned by different actor.", status=401)
        except LdId.DoesNotExist:
            photo = Photo()
        photo.donor = None
        photo.caption = self.content
        photo.category = self.category.get_or_create()
        photo.circa = self.circa
        photo.is_published = self.is_published
        photo.year = self.year
        photo.remote_image = self.url
        photo.archive = actor
        photo.license = self.license
        photo.original_width = self.width
        photo.original_height = self.height
        if len(self.attachment) >= 1:
            photo.remote_page = self.attachment[0].url

        if self.contributor is not None:
            ldcontributor, created = LdObjectGetOrCreator(ld_id=self.contributor, queryset=LdId.objects.all()).object
            if ldcontributor and isinstance(ldcontributor.content_object, Donor):
                photo.donor = ldcontributor.content_object

        if self.place is not None:
            ldplace, created = LdObjectGetOrCreator(ld_id=self.place, queryset=LdId.objects.all()).object
            if ldplace and isinstance(ldplace.content_object, Place):
                photo.place = ldplace.content_object
        photo.save()

        for tag in self.tags:
            new_tag, _ = Tag.objects.get_or_create(tag=tag)
            PhotoTag.objects.get_or_create(
                tag=new_tag, photo=photo, accepted=True
            )
        for term in self.terms:
            photo.terms.add(Term.objects.get_or_create(term=term)[0])

        ct = ContentType.objects.get_for_model(Photo)
        ldid, created = LdId.objects.get_or_create(
            ld_id=self.id, defaults={"content_type": ct, "object_id": photo.id}
        )
        return "created" if created else "updated"

    @require_archive
    def create(self, actor: Archive) -> str:
        """Wrapper for upsert.

        Args:
            actor (Archive): The actor attempting to create a photo.
        Returns:
            str: "created" if created, else "updated"
        """
        return self.upsert(actor)

    @require_archive
    def update(self, actor: Archive) -> str:
        """Wrapper for upsert.

        Args:
            actor (Archive): The actor attempting to update a photo.
        Returns:
            str: "created" if created, else "updated"
        """
        return self.upsert(actor)

@dataclass
class DonorValue:
    "A parsed donor"
    id: str
    attributedTo: List[str]
    name: Optional[str]
    firstName: str
    lastName: str

    @staticmethod
    def from_donor(donor: Donor) -> DonorValue:
        """Extract a DonorValue from a Donor

        Args:
            donor (Donor): A Donor.

        Returns:
            DonorValue: The DonorValue having the same values as `donor`.
        """
        return DonorValue(
            id=donor.ldid(),
            attributedTo=[donor.archive.ldid()],
            name=str(donor),
            firstName=donor.first_name,
            lastName=donor.last_name,
        )

    def reconcile(self, donor: Donor) -> None:
        """Copy these values to a Donor.

        Args:
            donor (Donor): The donor that should be updated to have these values.
        """
        donor.first_name = self.firstName
        donor.last_name = self.lastName
        donor.save()

    def upsert(self, actor: Archive) -> str:
        """Update or create a Donor from this value.

        If the donor already exists and is owned by a different actor, this will
        raise an exception.

        Args:
            actor (Archive): The actor attempting to update or create the Donor.

        Returns:
            str: "created" if created else "updated"
        """
        try:
            ldid = LdId.objects.get(ld_id=self.id)
            if ldid.content_object is None:
                obj = Donor()
            elif not isinstance(ldid.content_object, Donor):
                if hasattr(ldid.content_object, "is_owned_by") and actor.actor is not None and ldid.content_object.is_owned_by(actor):
                    ldid.content_object.delete()
                    obj = Donor()
                else:
                    raise JsonError("An object with that id exists and could not be deleted.", status=400)
            else:
                obj = ldid.content_object
                if actor.actor is None or not obj.is_owned_by(actor.actor):
                    raise JsonError("An object with that id is owned by different actor.", status=401)
        except LdId.DoesNotExist:
            obj = Donor()
        obj.archive = actor
        self.reconcile(obj)
        ct = ContentType.objects.get_for_model(Donor)
        ldid, created = LdId.objects.get_or_create(
            ld_id=self.id, defaults={"content_type": ct, "object_id": obj.id}
        )
        return "created" if created else "updated"

    @require_archive
    def create(self, actor: Archive) -> str:
        """A wrapper for upsert."""
        return self.upsert(actor)

    @require_archive
    def update(self, actor: Archive) -> str:
        """A wrapper for upsert."""
        return self.upsert(actor)

@dataclass
class PlaceValue:
    "A parsed Place"
    id: str
    name: str
    attributedTo: List[str]
    parent: Optional[LdIdUrl]
    placeType: str
    fullName: str
    geom: Optional[Union[Point, MultiPolygon]]

    @staticmethod
    def from_place(place: Place) -> PlaceValue:
        """Make a PlaceValue out of a Place.

        Args:
            place (Place): A Place to make a PlaceValue from.

        Returns:
            PlaceValue: A PlaceValue describing the given Place.
        """
        return PlaceValue(
            id=place.ldid(),
            attributedTo=[reverse("kronofoto:activitypub-main-service")],
            name=place.name,
            parent=place.parent.ldid() if place.parent else None,
            placeType=place.place_type.name,
            fullName=place.fullname,
            geom=place.geom,
        )

    def upsert(self, actor: RemoteActor) -> str:
        """Create or Update a Place.

        Args:
            actor (RemoteActor): The actor attempting to create or update the Place.

        Returns:
            (str): "created if created else "updated"
        """
        val, created = PlaceUpserter(queryset=LdId.objects.all(), owner=actor, object=self).result
        return "created" if created else "updated"

    def create(self, actor: RemoteActor) -> str:
        "A wrapper for upsert."
        return self.upsert(actor)

    def update(self, actor: RemoteActor) -> str:
        "A wrapper for upsert."
        return self.upsert(actor)

@dataclass
class CollectionPageValue(Generic[T]):
    "Represents a parsed Activity Stream Collection."
    id: str
    next: Optional[str]
    items: List[T]

    def get_next(self) -> "Optional[CollectionPageValue[T]]":
        from fortepan_us.kronofoto.models.activity_schema import CollectionPage
        if self.next:
            return CollectionPage().load(
                requests.get(
                    self.next,
                    headers={
                        "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    },
                ).json()
            )
        else:
            return None

    @staticmethod
    def from_donor_queryset(qs: QuerySet[Donor], short_name: str) -> CollectionPageValue[DonorValue]:
        id = reverse("kronofoto:activitypub_data:archives:contributors:page", kwargs={"short_name": short_name})
        return CollectionPageValue(
            id=id,
            next="{}?pk={}".format(id, qs[99].pk) if qs.count() == 100 else None,
            items=[DonorValue.from_donor(donor) for donor in qs]
        )

    @staticmethod
    def from_photo_queryset(qs: QuerySet[Photo], short_name: str) -> CollectionPageValue[PhotoValue]:
        id = reverse("kronofoto:activitypub_data:archives:photos:page", kwargs={"short_name": short_name})
        return CollectionPageValue(
            id=id,
            next="{}?pk={}".format(id, qs[99].pk) if qs.count() == 100 else None,
            items=[PhotoValue.from_photo(obj) for obj in qs]
        )

    @staticmethod
    def from_place_queryset(qs: QuerySet[Place]) -> CollectionPageValue[PlaceValue]:
        id = reverse("kronofoto:activitypub-main-service-places")
        return CollectionPageValue(
            id=id,
            next="{}?pk={}".format(id, qs[99].pk) if qs.count() == 100 else None,
            items=[PlaceValue.from_place(obj) for obj in qs]
        )


@dataclass
class CollectionValue(Generic[T]):
    id: str
    summary: str
    first: CollectionPageValue[T]

@dataclass
class ActorValue:
    id: str
    name: str
    publicKey: Dict[str, str]
    inbox: str
    outbox: str
    following: List[str]
    followers: List[str]

@dataclass
class ServiceActorValue(ActorValue):
    places: str

    def dump(self) -> Dict[str, Any]:
        from .activity_schema import ServiceActorSchema
        return ServiceActorSchema().dump(self)

@dataclass
class DeleteValue:
    id: str
    actor: str
    object: str

    def dump(self) -> Dict[str, Any]:
        from .activity_schema import DeleteActivitySchema
        return DeleteActivitySchema().dump(self)

    def handle_archive(self, actor: RemoteActor, archive: Archive) -> str:
        raise JsonError("This inbox doesn't do this.", status=400)


    def handle(self, actor: RemoteActor) -> str:
        if actor.app_follows_actor:
            try:
                ldid = LdId.objects.get(ld_id=self.object)
                if not ldid.content_object:
                    ldid.delete()
                    return "deleted"
                elif hasattr(ldid.content_object, "is_owned_by") and ldid.content_object.is_owned_by(actor):
                    ldid.content_object.delete()
                    ldid.delete()
                    return "deleted"
            except LdId.DoesNotExist:
                pass
            return "not deleted"
        else:
            raise JsonError("Not following this actor.", status=401)

@dataclass
class CreateValue:
    id: str
    actor: str
    object: Union[PhotoValue, DonorValue, PlaceValue]

    def dump(self) -> Dict[str, Any]:
        from .activity_schema import CreateActivitySchema
        return CreateActivitySchema().dump(self)

    def handle(self, actor: RemoteActor) -> str:
        if actor.app_follows_actor:
            return self.object.create(actor)
        else:
            raise JsonError("Not following this actor.", status=401)

    def handle_archive(self, actor: RemoteActor, archive: Archive) -> str:
        raise JsonError("This inbox doesn't do this.", status=400)

@dataclass
class UpdateValue:
    id: str
    actor: str
    object: Union[PhotoValue, DonorValue, PlaceValue]

    def dump(self) -> Dict[str, Any]:
        from .activity_schema import UpdateActivitySchema
        return UpdateActivitySchema().dump(self)

    def handle(self, actor: RemoteActor) -> str:
        if actor.app_follows_actor:
            return self.object.update(actor)
        else:
            logging.info("not following {actor} so not upserting {data}".format(actor=actor.profile, data=str(self.object)))
            raise JsonError("Not following this actor.", status=401)

    def handle_archive(self, actor: RemoteActor, archive: Archive) -> str:
        raise JsonError("This inbox doesn't do this.", status=400)

@dataclass
class FollowValue:
    id: str
    actor: str
    object: str
    def handle(self, actor: RemoteActor) -> str:
        FollowServiceRequest.objects.update_or_create(remote_actor=actor, request_id=self.id)
        return "stored"

    def handle_archive(self, actor: RemoteActor, archive: Archive) -> str:
        FollowArchiveRequest.objects.update_or_create(remote_actor=actor, archive=archive, defaults={"request_id": self.id})
        return "stored"

    def dump(self) -> Dict[str, Any]:
        from .activity_schema import FollowActivitySchema
        return FollowActivitySchema().dump(self)

@dataclass
class AcceptValue:
    id: str
    actor: str
    object: FollowValue

    def profile(self, location: str) -> Dict[str, Any]:
        return requests.get(
            location,
            headers={
                "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
        ).json()

    def handle_archive(self, actor: RemoteActor, archive: Archive) -> str:
        raise JsonError("This inbox doesn't do this.", status=400)

    def dump(self) -> Dict[str, Any]:
        from .activity_schema import AcceptActivitySchema
        return AcceptActivitySchema().dump(self)

    def handle(self, actor: RemoteActor) -> str:
        followobject = self.object
        remoteactor = RemoteActor.objects.get_or_create(profile=followobject.object)[0]
        remoteactor.app_follows_actor = True
        remoteactor.save()
        count, _ = FollowServiceOutbox.objects.filter(remote_actor_profile=remoteactor.profile).delete()
        if count >= 1:
            return "created"
        outboxactivities = OutboxActivity.objects.filter(
            body__type="Follow",
            body__object=remoteactor.profile,
        )
        for activity in outboxactivities:
            profile = self.profile(activity.body['object'])
            server_domain = urlparse(activity.body['object']).netloc
            Archive.objects.get_or_create(type=Archive.ArchiveType.REMOTE, actor=actor, slug=profile['slug'], server_domain=server_domain, name=profile['name'])
            outboxactivities.delete()
            return "created"
        return "not created"

class ActivitypubLocation(ActivitypubObject, total=False):
    name: str
    parent: Optional[LdIdUrl]
    type: Literal["Location"]
    geom: Union[None, Point, MultiPolygon]
    place_type: str


ActivitypubValue = Union[DeleteValue, CreateValue, UpdateValue, FollowValue, AcceptValue]
ActivitypubData = Union[ActivitypubImage, ActivitypubContact]

class Activity(TypedDict):
    actor: LdIdUrl
    object: Union[ActivitypubData, "ActivityTypes"]

class FollowActivity(Activity):
    type: Literal['Follow']

class AcceptActivity(Activity):
    type: Literal['Accept']

ActivityTypes = Union[FollowActivity, AcceptActivity]
