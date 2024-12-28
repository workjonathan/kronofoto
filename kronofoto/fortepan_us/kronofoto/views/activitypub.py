from django.http import HttpResponse, HttpRequest, JsonResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from typing import Dict, List, Any, Optional, Type, TypeVar, Protocol, Union, NamedTuple
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import permission_required
from django.contrib.gis.db.models.functions import AsGeoJSON
from urllib.parse import urlparse
import requests
from fortepan_us.kronofoto import signed_requests
from functools import cached_property
from django.contrib.sites.shortcuts import get_current_site
from ..reverse import reverse, resolve
from django.shortcuts import get_object_or_404
from fortepan_us.kronofoto.models.photo import Photo
from fortepan_us.kronofoto.models import Archive, FollowArchiveRequest, RemoteActor, OutboxActivity, Donor
from fortepan_us.kronofoto import models
from fortepan_us.kronofoto.models import activity_dicts
from fortepan_us.kronofoto.models.archive import ArchiveSchema
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
from django.contrib.contenttypes.models import ContentType

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

#@require_json_ld
def service(request: HttpRequest) -> HttpResponse:
    site = get_current_site(request)
    return JsonLDResponse({
        "@context": "https://www.w3.org/ns/activitystreams",
         "type": "Service",
         "id": reverse("kronofoto:activitypub-main-service"),
         "name": site.name,
         "inbox": reverse("kronofoto:activitypub-main-service-inbox"),
         "outbox": reverse("kronofoto:activitypub-main-service-outbox"),
         "following": [archive.actor.profile for archive in models.Archive.objects.filter(actor__isnull=False) if archive.actor],
         "publicKey": {
            "id": models.ServiceActor.get_instance().keyId,
            "owner": reverse("kronofoto:activitypub-main-service"),
            "publicKeyPem": models.ServiceActor.get_instance().guaranteed_public_key().decode("utf-8"),
         },
    })


@dataclass
class InboxResponse:
    data: Dict[str, Any]
    status_code: int = 200

class ArchiveInboxHandler(Protocol):
    def handle(self, *, archive: Archive, object: Dict[str, Any], root_type: str) -> Optional[InboxResponse]:
        ...

class UpdateImage:
    def handle(self, *, archive: Archive, object: Dict[str, Any], root_type: str) -> Optional[InboxResponse]:
        return None

class CreateImage:
    def handle(self, *, archive: Archive, object: Dict[str, Any], root_type: str) -> Optional[InboxResponse]:
        if root_type in ('Create', 'Update') and object['type'] == "Image":
            models.LdId.objects.update_or_create_ld_object(owner=archive, object=object) # type: ignore
            return InboxResponse(data={"status": "image created"})
        return None

class DeleteObject:
    def handle(self, *, archive: Archive, object: Dict[str, Any], root_type: str) -> Optional[InboxResponse]:
        if root_type == 'Delete':
            ldids = models.LdId.objects.filter(ld_id=object.get('href'))
            for dldid in ldids:
                deletedonor = dldid.content_object
                if deletedonor and deletedonor.archive.id == archive.id:
                    deletedonor.delete()
                    dldid.delete()
            return InboxResponse(data={"status": "object deleted"})
        return None

class CreateContact:
    def handle(self, *, archive: Archive, object: Dict[str, Any], root_type: str) -> Optional[InboxResponse]:
        if root_type in ('Create', 'Update') and object['type'] == "Contact":
            models.LdId.objects.update_or_create_ld_object(owner=archive, object=object) # type: ignore
            return InboxResponse(data={"status": "contact created"})
        return None



#@require_json_ld
def service_place(request: HttpRequest, pk: int) -> HttpResponse:
    place = get_object_or_404(models.Place.objects.all().annotate(json=AsGeoJSON("geom")), pk=pk)
    return JsonLDResponse(PlaceSchema().dump(place))

@csrf_exempt
@require_json_ld
def service_inbox(request: HttpRequest) -> HttpResponse:
    if not hasattr(request, 'actor') or not isinstance(request.actor, RemoteActor):
        return HttpResponse(status=401)
    if request.method == "POST":
        data = json.loads(request.body)
        schema = ActivitySchema()
        schema.context['actor'] = request.actor
        deserialized = schema.load(data)
        if deserialized['type'] == "Accept":
            for activity in OutboxActivity.objects.filter(
                body__type="Follow",
                body__actor=deserialized['object']['actor'].profile,
            ):
                profile = requests.get(
                    activity.body['object'],
                    headers={
                        "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                        'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    },
                ).json()
                server_domain = urlparse(activity.body['object']).netloc
                Archive.objects.get_or_create(type=Archive.ArchiveType.REMOTE, actor=request.actor, slug=profile['slug'], server_domain=server_domain, name=profile['name'])
                return JsonLDResponse({})
        if not request.actor.app_follows_actor and not Archive.objects.filter(actor=request.actor).exists():
            return JsonResponse({"error": "Not following this actor"}, status=401)
        root_type = deserialized.get('type')
        object = deserialized.get('object', {})
        object_type = object.get('type')
        archive = Archive.objects.get(actor=request.actor)
        if root_type in ("Create", "Update"):
            models.LdId.objects.update_or_create_ld_object(owner=archive, object=object)
            return JsonLDResponse({"status": "created"})
        else:
            handlers : List[ArchiveInboxHandler] = [CreateContact(), DeleteObject(), UpdateImage(), CreateImage()]
            for handler in handlers:
                response = handler.handle(archive=archive, object=object, root_type=root_type)
                if response:
                    return JsonLDResponse(response.data, status=response.status_code)
    return HttpResponse(status=401)

@require_json_ld
def service_outbox(request: HttpRequest) -> HttpResponse:
    return JsonLDResponse({})

class FollowForm(forms.Form):
    address = forms.URLField()

@permission_required("kronofoto.archive.create")
def service_follows(request: HttpRequest) -> HttpResponse:
    template = "kronofoto/pages/service.html"
    context : Dict[str, Any] = {}
    if request.method == "POST":
        form = FollowForm(request.POST)
        if form.is_valid():
            actor_data = requests.get(form.cleaned_data['address']).json()
            activity = ActivitySchema().dump({
                "object": form.cleaned_data['address'],
                "type": "Follow",
                "actor": reverse("kronofoto:activitypub-main-service"),
                "_context": activity_stream_context,
            })
            models.OutboxActivity.objects.create(body=activity)
            service_actor = models.ServiceActor.get_instance()
            signed_requests.post(
                actor_data['inbox'],
                data=json.dumps(activity),
                headers={
                    "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
                private_key=service_actor.private_key,
                keyId=service_actor.keyId,
            )

            #return HttpResponseRedirect("/")
    else:
        context['form'] = FollowForm()

    return TemplateResponse(
        request=request,
        template=template,
        context=context,
    )

class FollowReactForm(forms.Form):
    follow = forms.IntegerField(required=True)

@permission_required("kronofoto.archive.change")
def archive_view(request: HttpRequest, short_name: str) -> HttpResponse:
    template = "kronofoto/pages/archive_view.html"
    context : Dict[str, Any] = {}
    archive = get_object_or_404(models.Archive.objects.all(), slug=short_name)
    context['archive'] = archive
    if request.method == "POST":
        form = FollowReactForm(request.POST)
        if form.is_valid():
            followrequest = get_object_or_404(models.FollowArchiveRequest.objects.all(), pk=form.cleaned_data['follow'])
            if 'accept' in request.POST:
                actor_data = requests.get(followrequest.remote_actor.profile, headers={
                    "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                }).json()
                activity = ActivitySchema().dump({
                    "object": followrequest.request_body,
                    "type": "Accept",
                    "actor": reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": archive.slug}),
                    "_context": activity_stream_context,
                })
                resp = signed_requests.post(
                    actor_data['inbox'],
                    data=json.dumps(activity),
                    headers={
                        "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                        'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    },
                    private_key=archive.private_key,
                    keyId=archive.keyId,
                )
                if resp.status_code == 200:
                    followrequest.remote_actor.archives_followed.add(archive)
                    followrequest.delete()
    return TemplateResponse(
        request=request,
        template=template,
        context=context,
    )


from django.urls import path, include, register_converter, URLPattern, URLResolver
data_urls: Any = ([
    path("remotearchives/add", service_follows),
    path("archives/<slug:short_name>/show", archive_view),
], "activitypub_data")

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
    def following(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        ...
    def followers(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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

class GeomField(fields.Field):
    def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Dict[str, Any]:
        return MultiPolygonSchema().dump(value)

    def _deserialize(self, value: Dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        if value['type'] in ["MultiPolygon",]:
            return MultiPolygonSchema().load(value)
        raise ValueError(value['type'])

class MultiPolygonSchema(Schema):
    type = fields.Constant("MultiPolygon")
    coordinates = fields.List(fields.List(fields.List(fields.List(fields.Float()))))

class PlaceSchema(ObjectSchema):
    name = fields.Str()
    parent = fields.Url(relative=True)
    geom = GeomField()

    @pre_dump
    def extract_fields_from_object(self, object: models.Place, **kwargs: Any) -> Dict[str, Any]:
        data : Dict[str, Any] = {}
        data['id'] = reverse("kronofoto:activitypub-main-service-places", kwargs={"pk": object.id})
        data['name'] = object.name
        if object.geom:
            data['geom'] = json.loads(object.geom.json)
        if object.parent:
            data['parent'] = reverse("kronofoto:activitypub-main-service-places", kwargs={"pk": object.parent.id})
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
    def extract_fields_from_object(self, object: Photo, **kwargs: Any) -> Dict[str, Any]:
        data = {
            "id": reverse("kronofoto:activitypub_data:archives:photos:detail", kwargs={"short_name": object.archive.slug, "pk": object.id}),
            "attributedTo": [reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object.archive.slug})],
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
            data['place'] = reverse("kronofoto:activitypub-main-service-places", kwargs={"pk": object.place.id})
        if object.donor:
            data["contributor"] = reverse("kronofoto:activitypub_data:archives:contributors:detail", kwargs={'short_name': object.archive.slug, "pk": object.donor.id})
        return data

    #@post_load
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
    def extract_fields_from_object(self, object: Donor, **kwargs: Any) -> activity_dicts.ActivitypubContact:
        return {
            "id": activity_dicts.str_to_ldidurl(reverse("kronofoto:activitypub_data:archives:contributors:detail", kwargs={"short_name": object.archive.slug, "pk": object.id})),
            "attributedTo": [activity_dicts.str_to_ldidurl(reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object.archive.slug}))],
            "name": object.display_format(),
            "firstName": object.first_name,
            "lastName": object.last_name,
            "type": "Contact",
        }

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
        elif isinstance(value, Photo):
            return Image().dump(value)
        else:
            return value

    def _deserialize(self, value: Union[str, Dict[str, Any]], *args: Any, **kwargs: Any) -> Any:
        if isinstance(value, str):
            return LinkSchema(context=self.context).load({"href": value})
        if value['type'] in ["Accept", "Follow",]:
            return ActivitySchema(context=self.context).load(value)
        if value['type'] in ["Image",]:
            return Image(context=self.context).load(value)
        if value['type'] in ["Contact",]:
            return Contact(context=self.context).load(value)
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
                    path("/followers", cls.followers, name="followers"),
                    path("/following", cls.following, name="following"),
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
        if isinstance(object['actor'], models.Archive):
            object['actor'] = reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": object['actor'].slug})
        return object

    @pre_load
    def preload(self, data: Dict[str, Any], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        self.fields['object'].context.setdefault("root_type", data['type'])
        return data

    @post_load
    def extract_fields_from_dict(self, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        data['actor'] = RemoteActor.objects.get_or_create(profile=data['actor'])[0]
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



@register_actor("archives/<slug:short_name>", "archives", data_urls)
class ArchiveActor:
    data_urls: Any = []
    @staticmethod
    def profile(request: HttpRequest, short_name: str) -> HttpResponse:
        archive = get_object_or_404(Archive.objects.all(), slug=short_name)
        return JsonLDResponse(ArchiveSchema().dump(archive))

    @staticmethod
    def following(request: HttpRequest, short_name: str) -> HttpResponse:
        archive = get_object_or_404(Archive.objects.all(), slug=short_name)
        return JsonLDResponse(ActorCollectionSchema().dump(
            archive.remoteactor_set.none()
        ))

    @staticmethod
    def followers(request: HttpRequest, short_name: str) -> HttpResponse:
        archive = get_object_or_404(Archive.objects.all(), slug=short_name)
        return JsonLDResponse(ActorCollectionSchema().dump(
            archive.remoteactor_set.all()
        ))

    #@require_json_ld
    @staticmethod
    @csrf_exempt
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
