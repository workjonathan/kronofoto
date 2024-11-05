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

@dataclass
class DataPage:
    pk: int
    queryset: QuerySet
    backward: bool=False

    @cached_property
    def item_list(self) -> List[Donor]:
        if self.backward:
            filter = {"pk__lt": self.pk}
            order = "-id"
            reorder = lambda xs: list(reversed(xs))
        else:
            filter = {"pk__gt": self.pk}
            order = "id"
            reorder = list
        return reorder(self.queryset.filter(**filter).order_by(order)[:100])

    @property
    def next_page_pk(self) -> Optional[int]:
        return self.item_list[99].pk if len(self.item_list) >= 100 else None

    def page(self) -> List[Dict[str, Any]]:
        return [item.activity_dict for item in self.item_list]

class Page(forms.Form):
    pk = forms.IntegerField(required=True)

def get_donor_page(request:HttpRequest, short_name: str) -> HttpResponse:
    queryset = Donor.objects.filter(archive__slug=short_name)
    url_path = reverse("kronofoto:activitypub-donor-page", kwargs={"short_name": short_name})
    summary = "Contributor List"
    return get_data_page(request=request, queryset=queryset, url_path=url_path, summary=summary)

def get_photo_page(request:HttpRequest, short_name: str) -> HttpResponse:
    queryset = Photo.objects.filter(archive__slug=short_name)
    url_path = reverse("kronofoto:activitypub-photo-page", kwargs={"short_name": short_name})
    summary = "Photo List"
    return get_data_page(request=request, queryset=queryset, url_path=url_path, summary=summary)

def get_data_page(request: HttpRequest, queryset: QuerySet, url_path: str, summary: str) -> HttpResponse:
    object_data: Dict[str, Any] = {
        "@context": activity_stream_context,
    }
    form = Page(request.GET)
    if form.is_valid():
        pk = form.cleaned_data['pk']
        object_data['id'] = "{}?{}".format(url_path, request.GET.urlencode())
        page = DataPage(pk=pk, queryset=queryset)
        object_data['items'] = page.page()
        next_page = page.next_page_pk
        object_data['next'] = "{}?pk={}".format(url_path, next_page) if next_page is not None else None

    else:
        object_data['summary'] = summary
        object_data['id'] = url_path
        page = DataPage(pk=0, queryset=queryset)
        next_page = page.next_page_pk
        object_data['first'] = {
            "id": "{}?pk=0".format(url_path),
            'items': page.page(),
            'next': "{}?pk={}".format(url_path, next_page) if next_page is not None else None,

        }
    return JsonLDResponse(object_data)

def get_photo_data(request: HttpRequest, *, short_name: str, pk: int) -> HttpResponse:
    photo = get_object_or_404(Photo.objects.all(), pk=pk, archive__slug=short_name)
    object_data = photo.activity_dict
    object_data['@context'] = activity_stream_context
    return JsonLDResponse(object_data)

def get_donor_data(request: HttpRequest, *, short_name: str, pk: int) -> HttpResponse:
    donor : Donor = get_object_or_404(Donor.objects.all(), pk=pk, archive__slug=short_name)
    object_data = donor.activity_dict
    object_data['@context'] = activity_stream_context
    return JsonLDResponse(object_data)

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
        if data['type'] == "Accept":
            for activity in OutboxActivity.objects.filter(
                body__id=data['object']['id'],
                body__type="Follow",
                body__actor=data['object']['actor'],
            ):
                RemoteArchive.objects.get_or_create(actor=request.actor)
                return JsonLDResponse({})
        return JsonLDResponse({})
    return HttpResponse(status=401)

@require_json_ld
def service_outbox(request: HttpRequest) -> HttpResponse:
    return JsonLDResponse({})

#@require_json_ld
def archive_profile(request: HttpRequest, short_name: str) -> HttpResponse:
    archive = get_object_or_404(Archive.objects.all(), slug=short_name)
    return JsonLDResponse({
        "@context": "https://www.w3.org/ns/activitystreams",
         "type": "Organization",
         "id": reverse("kronofoto:activitypub-archive", kwargs={"short_name": short_name}),
         "name": archive.name,
         "inbox": reverse("kronofoto:activitypub-archive-inbox", kwargs={"short_name": short_name}),
         "outbox": reverse("kronofoto:activitypub-archive-outbox", kwargs={"short_name": short_name}),
    })

@require_json_ld
def archive_inbox(request: HttpRequest, short_name: str) -> HttpResponse:
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

@require_json_ld
def archive_outbox(request: HttpRequest, short_name: str) -> HttpResponse:
    archive = get_object_or_404(Archive.objects.all(), slug=short_name)
    return JsonLDResponse({})



data_urls: Any = ([], "activitypub_data")
from django.urls import path, include, register_converter, URLPattern, URLResolver

class DataEndpoint(Protocol):
    def data_page(self, request: HttpRequest, short_name: str) -> HttpResponse:
        ...
    def data(self, request: HttpRequest, short_name: str, pk: int) -> HttpResponse:
        ...

T = TypeVar("T", bound=DataEndpoint)

@dataclass
class register:
    namespace: str
    data_urls: Any
    def __call__(self, cls: Type[T]) -> Type[T]:
        data_urls[0].append(
            path(self.namespace, include(([
                    path("", cls.data_page, name="page"),
                    path("/<int:pk>", cls.data, name="detail"),
                ],
                self.namespace,
            ))
        ))
        return cls

@dataclass
class register2:
    model: Any
    data_urls: Any
    def __call__(self, cls: Any) -> Any:
        print(cls)
        return cls

from marshmallow import Schema, fields, pre_dump, post_load, pre_load
from django.contrib.sites.models import Site


class Image(Schema):
    id = fields.Url()
    type = fields.Constant("Image")
    attributedTo = fields.List(fields.Url())
    content = fields.Str()
    url = fields.Url(relative=True)

    @pre_dump
    def extract_fields_from_object(self, object: Photo, **kwargs: Any) -> Dict[str, Any]:
        return {
            "id": reverse("kronofoto:activitypub_data:photos:detail", kwargs={"short_name": object.archive.slug, "pk": object.id}),
            "attributedTo": [reverse("kronofoto:activitypub-archive", kwargs={"short_name": object.archive.slug})],
            "content": object.caption,
            "url": object.original.url,
        }

    @post_load
    def extract_fields_from_dict(self, data: Dict[str, Any], **kwargs: Any) -> Photo:
        resolved = resolve(data['id'])
        if Site.objects.filter(domain=resolved.domain).exists() and resolved.match.url_name == "detail":
            return Photo.objects.get(pk=resolved.match.kwargs['pk'])
        return Photo(
            caption=data['content'],
        )

class Contact(Schema):
    id = fields.Url()
    type = fields.Constant("Contact")
    attributedTo = fields.List(fields.Url())
    name = fields.Str()
    firstName = fields.Str()
    lastName = fields.Str()

    @pre_dump
    def extract_fields_from_object(self, object: Donor, **kwargs: Any) -> Dict[str, Any]:
        return {
            "id": reverse("kronofoto:activitypub_data:contributors:detail", kwargs={"short_name": object.archive.slug, "pk": object.id}),
            "attributedTo": [reverse("kronofoto:activitypub-archive", kwargs={"short_name": object.archive.slug})],
            "name": object.display_format(),
            "firstName": object.first_name,
            "lastName": object.last_name,
        }

    @post_load
    def extract_fields_from_dict(self, data: Dict[str, Any], **kwargs: Any) -> Donor:
        resolved = resolve(data['id'])
        if Site.objects.filter(domain=resolved.domain).exists() and resolved.match.url_name == "detail":
            return Donor.objects.get(pk=resolved.match.kwargs['pk'])
        return Donor()

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


class CollectionPage(Schema):
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


class PagedCollection(Schema):
    id = fields.Str()
    summary = fields.Str()
    first = fields.Nested(CollectionPage)

    @pre_dump
    def extract_fields_from_object(self, object: QuerySet, **kwargs: Any) -> Dict[str, Any]:
        return {
            "id": self.context['url'],
            "summary": self.context['summary'],
            'first': object
        }


class ArchiveActor:

    @register("contributors", data_urls)
    class DonorData:

        @classmethod
        def data_page(cls, request: HttpRequest, short_name: str) -> HttpResponse:
            form = Page(request.GET)
            if form.is_valid():
                queryset = Donor.objects.filter(archive__slug=short_name, pk__gt=form.cleaned_data['pk']).order_by('id')
                schema : Union[CollectionPage, PagedCollection] = CollectionPage()
                schema.context['slug'] = short_name
                schema.context['url'] = reverse("kronofoto:activitypub_data:contributors:page", kwargs={"short_name": short_name})
                object_data = schema.dump(queryset[:100])
                return JsonLDResponse(object_data)
            else:
                queryset = Donor.objects.filter(archive__slug=short_name).order_by('id')
                schema = PagedCollection()
                schema.context['slug'] = short_name
                schema.context['url'] = reverse("kronofoto:activitypub_data:contributors:page", kwargs={"short_name": short_name})
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
                schema : Union[CollectionPage, PagedCollection] = CollectionPage()
                schema.context['slug'] = short_name
                schema.context['url'] = reverse("kronofoto:activitypub_data:photos:page", kwargs={"short_name": short_name})
                object_data = schema.dump(queryset[:100])
                return JsonLDResponse(object_data)
            else:
                queryset = Photo.objects.filter(archive__slug=short_name).order_by('id')
                schema = PagedCollection()
                schema.context['slug'] = short_name
                schema.context['url'] = reverse("kronofoto:activitypub_data:photos:page", kwargs={"short_name": short_name})
                schema.context['summary'] = "Photo List"
                object_data = schema.dump(queryset[:100])
                return JsonLDResponse(object_data)

        @staticmethod
        def data(request: HttpRequest, short_name: str, pk: int) -> HttpResponse:
            object : Photo = get_object_or_404(Photo.objects.all(), pk=pk, archive__slug=short_name)
            object_data = Image().dump(object)
            return JsonLDResponse(object_data)
