from django.http import HttpResponse, HttpRequest, JsonResponse
from typing import Dict, List, Any, Optional, Type, TypeVar, Protocol, Union
from functools import cached_property
from django.contrib.sites.shortcuts import get_current_site
from ..reverse import reverse, resolve
from django.shortcuts import get_object_or_404
from fortepan_us.kronofoto.models.photo import Photo
from fortepan_us.kronofoto.models import Archive, FollowArchiveRequest, RemoteActor, OutboxActivity, RemoteArchive, Donor
import json
import parsy # type: ignore
from django.core.cache import cache
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import base64
from dataclasses import dataclass, field
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from fortepan_us.kronofoto.middleware import SignatureHeaders, decode_signature, decode_signature_headers
from django import forms

activity_stream_context = "https://www.w3.org/ns/activitystreams"

def JsonLDResponse(*args: Any, **kwargs: Any) -> JsonResponse:
    resp = JsonResponse(*args, **kwargs)
    resp['Content-Type'] = 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
    return resp



class ViewFunction(Protocol):
    def __call__(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        ...

def require_json_ld(func: ViewFunction) -> ViewFunction:
    def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.headers.get("Accept", "") != 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"':
            return HttpResponse(status=406)
        return func(request, *args, **kwargs)
    return wrapped

from django.db.models import QuerySet

class Page(forms.Form):
    pk = forms.IntegerField(required=True)

#@require_json_ld
def get_data(request:HttpRequest, type: str, pk: int) -> HttpResponse:
    if type == "contributors":
        pass
    else:
        return HttpResponse(status=404)

    #object_data['@context'] = activity_stream_context
    return JsonLDResponse({})

@require_json_ld
def service(request: HttpRequest) -> HttpResponse:
    site = get_current_site(request)
    return JsonLDResponse({
        "@context": "https://www.w3.org/ns/activitystreams",
         "type": "Service",
         "id": reverse("kronofoto:activitypub-main-service"),
         "name": site.name,
         "inbox": reverse("kronofoto:activitypub-main-service-inbox"),
         "outbox": reverse("kronofoto:activitypub-main-service-outbox"),
    })

@require_json_ld
def service_inbox(request: HttpRequest) -> HttpResponse:
    if not hasattr(request, 'actor') or not isinstance(request.actor, RemoteActor):
        return HttpResponse(status=401)
    if request.method == "POST":
        data = json.loads(request.body)
        deserialized = ActivitySchema().load(data)
        if deserialized['type'] == "Accept":
            for activity in OutboxActivity.objects.filter(
                body__id=data['object']['id'],
                body__type="Follow",
                body__actor=data['object']['actor'],
            ):
                RemoteArchive.objects.get_or_create(actor=request.actor)
                return JsonLDResponse({})
        if deserialized['type'] == 'Create':
            if not request.actor.app_follows_actor:
                return HttpResponse(status=401)
            object = deserialized['object']
            object.archive = RemoteArchive.objects.get(actor=request.actor)
            object.save()
        return JsonLDResponse({})
    return HttpResponse(status=401)

@require_json_ld
def service_outbox(request: HttpRequest) -> HttpResponse:
    return JsonLDResponse({})

#@require_json_ld



data_urls: Any = ([], "activitypub_data")
from django.urls import path, include, register_converter, URLPattern, URLResolver

class DataEndpoint(Protocol):
    def data_page(self, request: HttpRequest, short_name: str) -> HttpResponse:
        ...
    def data(self, request: HttpRequest, short_name: str, pk: int) -> HttpResponse:
        ...

class ActorEndpoint(Protocol):
    @property
    def data_urls(self) -> List[Any]:
        ...
    def profile(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        ...
    def inbox(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        ...
    def outbox(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        ...

T = TypeVar("T", bound=DataEndpoint)

@dataclass
class register:
    namespace: str
    data_urls: Any
    def __call__(self, cls: Type[T]) -> Type[T]:
        self.data_urls.append(
            path("/"+ self.namespace, include(([
                    path("", cls.data_page, name="page"),
                    path("/<int:pk>", cls.data, name="detail"),
                ],
                self.namespace,
            ))
        ))
        return cls


from marshmallow import Schema, fields, pre_dump, post_load, pre_load
from django.contrib.sites.models import Site

class ObjectSchema(Schema):
    _context = fields.Raw(data_key="@context")
    id = fields.Url(required=False)
    type = fields.Str()
    attributedTo = fields.List(fields.Url())
    url = fields.Url(relative=True)
    content = fields.Str()

class LinkSchema(Schema):
    href = fields.Url()


class Image(ObjectSchema):
    id = fields.Url()

    @pre_dump
    def extract_fields_from_object(self, object: Photo, **kwargs: Any) -> Dict[str, Any]:
        return {
            "id": reverse("kronofoto:activitypub_data:archives:photos:detail", kwargs={"short_name": object.archive.slug, "pk": object.id}),
            "attributedTo": [reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object.archive.slug})],
            "content": object.caption,
            "url": object.original.url,
            "type": "Image",
        }

    @post_load
    def extract_fields_from_dict(self, data: Dict[str, Any], **kwargs: Any) -> Photo:
        resolved = resolve(data['id'])
        if Site.objects.filter(domain=resolved.domain).exists() and resolved.match.url_name == "detail":
            return Photo.objects.get(pk=resolved.match.kwargs['pk'])
        return Photo(
            caption=data['content'],
        )

class Contact(ObjectSchema):
    id = fields.Url()
    attributedTo = fields.List(fields.Url())
    name = fields.Str()
    firstName = fields.Str()
    lastName = fields.Str()

    @pre_dump
    def extract_fields_from_object(self, object: Donor, **kwargs: Any) -> Dict[str, Any]:
        return {
            "id": reverse("kronofoto:activitypub_data:archives:contributors:detail", kwargs={"short_name": object.archive.slug, "pk": object.id}),
            "attributedTo": [reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object.archive.slug})],
            "name": object.display_format(),
            "firstName": object.first_name,
            "lastName": object.last_name,
            "type": "Contact",
        }

    @post_load
    def extract_fields_from_dict(self, data: Dict[str, Any], **kwargs: Any) -> Donor:
        resolved = resolve(data['id'])
        if Site.objects.filter(domain=resolved.domain).exists() and resolved.match.url_name == "detail":
            return Donor.objects.get(pk=resolved.match.kwargs['pk'])
        return Donor(first_name=data['firstName'], last_name=data['lastName'])

class PageItem(fields.Field):
    def _serialize(self, value: Union[Donor, Photo], attr: Any, obj: Any, **kwargs: Any) -> Dict[str, Any]:
        if isinstance(value, Donor):
            return Contact().dump(value)
        else:
            return Image().dump(value)
    def _deserialize(self, value: Dict[str, Any], *args: Any, **kwargs: Any) -> Union[Contact, Image]:
        if value['type'] == "Contact":
            return Contact().load(value)
        return Image().load(value)

class ObjectOrLinkField(fields.Field):
    def _serialize(self, value: Union[Donor, Photo], attr: Any, obj: Any, **kwargs: Any) -> Dict[str, Any]:
        if isinstance(value, Donor):
            return Contact().dump(value)
        else:
            return Image().dump(value)
    def _deserialize(self, value: Union[str, Dict[str, Any]], *args: Any, **kwargs: Any) -> Any:
        if isinstance(value, str):
            return LinkSchema().load({"href": value})
        if value['type'] in ["Accept", "Follow",]:
            return ActivitySchema().load(value)
        if value['type'] in ["Contact",]:
            return Contact().load(value)
        raise ValueError(value['type'])


class Collection(ObjectSchema):
    summary = fields.Str()
    first = fields.Nested(lambda: CollectionPage())

    @pre_dump
    def extract_fields_from_object(self, object: QuerySet, **kwargs: Any) -> Dict[str, Any]:
        return {
            "id": self.context['url'],
            "summary": self.context['summary'],
            'first': object
        }

class CollectionPage(Collection):
    id = fields.Url()
    next = fields.Url(required=False, allow_none=True)
    items = fields.List(PageItem)

    @pre_dump
    def extract_fields_from_object(self, object: QuerySet, **kwargs: Any) -> Dict[str, Any]:
        next = "{}?pk={}".format(
            self.context['url'],
            object[99].pk,
        ) if object.count() == 100 else None
        return {
            "id": "{}?pk=0".format(self.context['url']),
            'items': object,
            "next": next,
        }

U = TypeVar("U", bound=ActorEndpoint)

@dataclass
class register_actor:
    path: str
    namespace: str
    data_urls: Any
    def __call__(self, cls: Type[U]) -> Type[U]:
        data_urls[0].append(
            path(self.path, include(([# type: ignore
                    path("", cls.profile, name="actor"),
                    path("/inbox", cls.inbox, name="inbox"),
                    path("/outbox", cls.outbox, name="outbox"),
                ] + cls.data_urls,
                self.namespace,
            ))
        ))

        return cls

class ActivitySchema(ObjectSchema):
    actor = fields.Url()
    object = ObjectOrLinkField()
    to = fields.List(fields.Url())

    @pre_dump
    def extract_fields_from_object(self, object: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        return {
            "summary": f"{object['actor'].name} created something",
            "object": object['object'],
            "actor": reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object['actor'].slug}),
            "type": object['type'],
            "to": object['to'],
        }

    @post_load
    def extract_fields_from_dict(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        data['actor'] = RemoteActor.objects.get_or_create(profile=data['actor'])[0]
        return data


class ArchiveSchema(Schema):
    type = fields.Constant("Organization")
    id = fields.Url(relative=True)
    name = fields.Str()
    publicKey = fields.Dict(keys=fields.Str(), values=fields.Str())
    inbox = fields.Url(relative=True)
    outbox = fields.Url(relative=True)
    contributors = fields.Url(relative=True)
    photos = fields.Url(relative=True)

    @pre_dump
    def extract_fields_from_object(self, object: Archive, **kwargs: Any) -> Dict[str, Any]:
        return {
            "id": reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object.slug}),
            "name": object.name,
            "inbox": reverse("kronofoto:activitypub_data:archives:inbox", kwargs={"short_name": object.slug}),
            "outbox": reverse("kronofoto:activitypub_data:archives:outbox", kwargs={"short_name": object.slug}),
            "contributors": reverse("kronofoto:activitypub_data:archives:contributors:page", kwargs={"short_name": object.slug}),
            "photos": reverse("kronofoto:activitypub_data:archives:photos:page", kwargs={"short_name": object.slug}),
            "publicKey": {
                "id": object.keyId,
                "owner": reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object.slug}),
                "publicKeyPem": object.guaranteed_public_key(),
            },
        }

@register_actor("archives/<slug:short_name>", "archives", data_urls)
class ArchiveActor:
    data_urls: Any = []
    @staticmethod
    def profile(request: HttpRequest, short_name: str) -> HttpResponse:
        archive = get_object_or_404(Archive.objects.all(), slug=short_name)
        return JsonLDResponse(ArchiveSchema().dump(archive))

    #@require_json_ld
    @staticmethod
    def inbox(request: HttpRequest, short_name: str) -> HttpResponse:
        if not hasattr(request, 'actor') or not isinstance(request.actor, RemoteActor):
            return HttpResponse(status=401)
        archive = get_object_or_404(Archive.objects.all(), slug=short_name)
        if request.method == "POST":
            data = json.loads(request.body.decode("utf-8"))
            actor, created = RemoteActor.objects.get_or_create(
                profile=data['actor'],
                defaults={
                    "actor_follows_app": False,
                    "app_follows_actor": False,
                }
            )
            FollowArchiveRequest.objects.create(remote_actor=actor, request_body=data, archive=archive)
            return JsonLDResponse({})
        else:
            return HttpResponse(status=401)

    #@require_json_ld
    @staticmethod
    def outbox(request: HttpRequest, short_name: str) -> HttpResponse:
        archive = get_object_or_404(Archive.objects.all(), slug=short_name)
        return JsonLDResponse({})

    @register("contributors", data_urls)
    class DonorData:

        @classmethod
        def data_page(cls, request: HttpRequest, short_name: str) -> HttpResponse:
            form = Page(request.GET)
            if form.is_valid():
                queryset = Donor.objects.filter(archive__slug=short_name, pk__gt=form.cleaned_data['pk']).order_by('id')
                schema : Union[CollectionPage, Collection] = CollectionPage()
                schema.context['slug'] = short_name
                schema.context['url'] = reverse("kronofoto:activitypub_data:archives:contributors:page", kwargs={"short_name": short_name})
                object_data = schema.dump(queryset[:100])
                return JsonLDResponse(object_data)
            else:
                queryset = Donor.objects.filter(archive__slug=short_name).order_by('id')
                schema = Collection()
                schema.context['slug'] = short_name
                schema.context['url'] = reverse("kronofoto:activitypub_data:archives:contributors:page", kwargs={"short_name": short_name})
                schema.context['summary'] = "Contributor List"
                object_data = schema.dump(queryset[:100])
                return JsonLDResponse(object_data)

        @staticmethod
        def data(request: HttpRequest, short_name: str, pk: int) -> HttpResponse:
            donor : Donor = get_object_or_404(Donor.objects.all(), pk=pk, archive__slug=short_name)
            object_data = Contact().dump(donor)
            return JsonLDResponse(object_data)

    @register("photos", data_urls)
    class PhotoData:

        @staticmethod
        def data_page(request: HttpRequest, short_name: str) -> HttpResponse:
            form = Page(request.GET)
            if form.is_valid():
                queryset = Photo.objects.filter(archive__slug=short_name, pk__gt=form.cleaned_data['pk']).order_by('id')
                schema : Union[CollectionPage, Collection] = CollectionPage()
                schema.context['slug'] = short_name
                schema.context['url'] = reverse("kronofoto:activitypub_data:archives:photos:page", kwargs={"short_name": short_name})
                object_data = schema.dump(queryset[:100])
                return JsonLDResponse(object_data)
            else:
                queryset = Photo.objects.filter(archive__slug=short_name).order_by('id')
                schema = Collection()
                schema.context['slug'] = short_name
                schema.context['url'] = reverse("kronofoto:activitypub_data:archives:photos:page", kwargs={"short_name": short_name})
                schema.context['summary'] = "Photo List"
                object_data = schema.dump(queryset[:100])
                return JsonLDResponse(object_data)

        @staticmethod
        def data(request: HttpRequest, short_name: str, pk: int) -> HttpResponse:
            object : Photo = get_object_or_404(Photo.objects.all(), pk=pk, archive__slug=short_name)
            object_data = Image().dump(object)
            return JsonLDResponse(object_data)
