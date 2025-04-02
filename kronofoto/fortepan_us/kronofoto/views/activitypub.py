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
from fortepan_us.kronofoto.models.activity_schema import ObjectSchema, PlaceSchema, Contact, Image, ActivitySchema, Collection, CollectionPage, ActorCollectionSchema, ArchiveSchema, ServiceActorSchema
from fortepan_us.kronofoto.models.activity_schema import ArchiveSchema
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
from marshmallow.exceptions import ValidationError
import logging

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
    data = activity_dicts.ServiceActorValue(
        #"@context": "https://www.w3.org/ns/activitystreams",
        id=reverse("kronofoto:activitypub-main-service"),
        name=site.name,
        inbox=reverse("kronofoto:activitypub-main-service-inbox"),
        outbox=reverse("kronofoto:activitypub-main-service-outbox"),
        following=[actor.profile for actor in models.RemoteActor.objects.filter(app_follows_actor=True)],
        followers=[actor.profile for actor in models.RemoteActor.objects.filter(actor_follows_app=True)],
        places=reverse("kronofoto:activitypub-main-service-places"),
        publicKey={
            "id": models.ServiceActor.get_instance().keyId,
            "owner": reverse("kronofoto:activitypub-main-service"),
            "publicKeyPem": models.ServiceActor.get_instance().guaranteed_public_key().decode("utf-8"),
        },
    ).dump()
    return JsonLDResponse(data)


#@require_json_ld
def service_place(request: HttpRequest, pk: int) -> HttpResponse:
    place = get_object_or_404(models.Place.objects.all().annotate(json=AsGeoJSON("geom")), pk=pk)
    return JsonLDResponse(PlaceSchema().dump(activity_dicts.PlaceValue.from_place(place)))

def places_page(request: HttpRequest) -> HttpResponse:
    form = Page(request.GET)
    if form.is_valid():
        queryset = models.Place.objects.filter(pk__gt=form.cleaned_data['pk'], owner=None).order_by('id')[:100]
        schema : Union[CollectionPage, Collection] = CollectionPage()
        object_data = schema.dump(activity_dicts.CollectionPageValue.from_place_queryset(queryset))
        return JsonLDResponse(object_data)
    else:
        queryset = models.Place.objects.all().order_by('id')[:100]
        schema = Collection()
        cv = activity_dicts.CollectionValue(
            id=reverse("kronofoto:activitypub-main-service-places"),
            summary="Photo List",
            first=activity_dicts.CollectionPageValue.from_place_queryset(queryset)
        )
        object_data = schema.dump(cv)
        return JsonLDResponse(object_data)

from fortepan_us.kronofoto.models.activity_dicts import JsonError

@dataclass
class ServiceInboxResponder:
    body: bytes
    actor: RemoteActor

    def data(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.body)
            if not isinstance(data, dict):
                raise JsonError("body must be a json object", status=400)
            return data
        except json.decoder.JSONDecodeError:
            raise JsonError("JSON decoding failed!", status=400)
        except UnicodeDecodeError as e:
            raise JsonError("UTF-8 decoding failed!", status=400)

    def parsed_data(self) -> activity_dicts.ActivitypubValue:
        schema = ActivitySchema()
        data = schema.load(self.data())
        if data is not None:
            return data
        raise JsonError("validation failed", status=400)

    def profile(self, location: str) -> Dict[str, Any]:
        return requests.get(
            location,
            headers={
                "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
        ).json()

    @cached_property
    def actor_is_known(self) -> bool:
        return Archive.objects.filter(actor=self.actor).exists()

    def archive_response(self, archive: Archive) -> JsonResponse:
        try:
            deserialized = self.parsed_data()
            return JsonLDResponse({"status": deserialized.handle_archive(self.actor, archive)})
        except JsonError as e:
            return JsonResponse({"error": e.message}, status=e.status)

    @property
    def post_response(self) -> JsonResponse:
        try:
            deserialized = self.parsed_data()
            return JsonLDResponse({"status": deserialized.handle(self.actor)})
        except JsonError as e:
            return JsonResponse({"error": e.message}, status=e.status)

@csrf_exempt
@require_json_ld
def service_inbox(request: HttpRequest) -> HttpResponse:
    if not hasattr(request, 'actor') or not isinstance(request.actor, RemoteActor):
        logging.info("service inbox unauthorized")
        return HttpResponse(status=401)
    if request.method == "POST":
        return ServiceInboxResponder(body=request.body, actor=request.actor).post_response
    return HttpResponse(status=401)

@require_json_ld
def service_outbox(request: HttpRequest) -> HttpResponse:
    return JsonLDResponse({})

class FollowForm(forms.Form):
    address = forms.URLField()

class SendFollowRequest(FollowForm):
    inbox = forms.URLField()

@permission_required("kronofoto.archive.modify")
def placeservice_follow_send(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SendFollowRequest(request.POST)
        if form.is_valid():
            activity = activity_dicts.FollowValue(
                id=reverse("kronofoto:activitypub-main-service")+"#follow",
                object=form.cleaned_data['address'],
                actor=reverse("kronofoto:activitypub-main-service"),
            ).dump()

            _, created = models.FollowServiceOutbox.objects.update_or_create(remote_actor_profile=form.cleaned_data['address'])
            service_actor = models.ServiceActor.get_instance()

            post_response = signed_requests.post(
                form.cleaned_data['inbox'],
                data=json.dumps(activity),
                headers={
                    "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
                private_key=service_actor.private_key,
                keyId=service_actor.keyId,
            )
            if post_response.status_code != 200:
                logging.info('{code} {body!r} received from {address} for {data}'.format(code=post_response.status_code, address=form.cleaned_data['address'], data=activity, body=post_response.content))

    return HttpResponseRedirect(reverse("kronofoto:activitypub_data:service-follow-config"))

@permission_required("kronofoto.archive.create")
def service_follow_send(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SendFollowRequest(request.POST)
        if form.is_valid():
            activity = activity_dicts.FollowValue(
                id=reverse("kronofoto:activitypub-main-service")+"#follow",
                object=form.cleaned_data['address'],
                actor=reverse("kronofoto:activitypub-main-service"),
            ).dump()

            models.OutboxActivity.objects.create(body=activity)
            service_actor = models.ServiceActor.get_instance()

            post_response = signed_requests.post(
                form.cleaned_data['inbox'],
                data=json.dumps(activity),
                headers={
                    "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
                private_key=service_actor.private_key,
                keyId=service_actor.keyId,
            )
            if post_response.status_code != 200:
                logging.info('{code} {body!r} received from {address} for {data}'.format(code=post_response.status_code, address=form.cleaned_data['address'], data=activity, body=post_response.content))

    return HttpResponseRedirect(reverse("kronofoto:activitypub_data:service-follow-config"))

@permission_required("kronofoto.archive.create")
def service_follows(request: HttpRequest) -> HttpResponse:
    template = "kronofoto/pages/service.html"
    context : Dict[str, Any] = {}
    if request.method == "POST":
        form = FollowForm(request.POST)
        if form.is_valid():
            try:
                actor_data = requests.get(form.cleaned_data['address']).json()
                actor_type = actor_data.get('type')
                try:
                    if actor_type == 'ArchiveActor':
                        template = "kronofoto/pages/service-archive-info.html"
                        archivevalue = ArchiveSchema().load(actor_data)
                        context['archivevalue'] = archivevalue
                        try:
                            archive = Archive.objects.get(actor__profile=archivevalue.id)
                            context['archive'] = archive
                        except Archive.DoesNotExist:
                            context['form'] = SendFollowRequest(data={"address": archivevalue.id, "inbox": archivevalue.inbox,})
                    elif actor_type == 'PlaceService':
                        template = "kronofoto/pages/service-placeservice-info.html"
                        servicevalue = ServiceActorSchema().load(actor_data)
                        context['servicevalue'] = servicevalue
                        try:
                            actor = RemoteActor.objects.get(profile=servicevalue.id, app_follows_actor=True)
                            context['actor'] = actor
                        except RemoteActor.DoesNotExist:
                            context['form'] = SendFollowRequest(data={"address": servicevalue.id, "inbox": servicevalue.inbox,})
                    else:
                        context['form'] = FollowForm()
                        context['error'] = "unknown schema: {}".format(actor_type)
                except ValidationError:
                    context['error'] = "validation error"
                    context['form'] = FollowForm()
            except json.decoder.JSONDecodeError:
                context['error'] = "json decode error"
                context['form'] = FollowForm()
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
def service_view(request: HttpRequest) -> HttpResponse:
    template = "kronofoto/pages/service_view.html"
    context : Dict[str, Any] = {}
    context['requests'] = models.FollowServiceRequest.objects.all()
    if request.method == "POST":
        form = FollowReactForm(request.POST)
        print(form)
        if form.is_valid():
            followrequest = get_object_or_404(models.FollowServiceRequest.objects.all(), pk=form.cleaned_data['follow'])
            if 'accept' in request.POST:
                actor_data = requests.get(followrequest.remote_actor.profile, headers={
                    "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                }).json()
                activity = activity_dicts.AcceptValue(
                    id=followrequest.request_id,
                    actor=reverse("kronofoto:activitypub-main-service"),
                    object=activity_dicts.FollowValue(
                        id=followrequest.request_id,
                        actor=followrequest.remote_actor.profile,
                        object=reverse("kronofoto:activitypub-main-service"),
                    ),
                ).dump()
                service = models.ServiceActor.get_instance()
                resp = signed_requests.post(
                    actor_data['inbox'],
                    data=json.dumps(activity),
                    headers={
                        "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                        'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    },
                    private_key=service.private_key,
                    keyId=service.keyId,
                )
                if resp.status_code == 200:
                    followrequest.remote_actor.actor_follows_app = True
                    followrequest.remote_actor.save()
                    followrequest.delete()
                else:
                    logging.info('{code} {body!r} received from {address} for {data}'.format(code=resp.status_code, address=actor_data['inbox'], data=activity, body=resp.content))

    return TemplateResponse(
        request=request,
        template=template,
        context=context,
    )

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
                activity = activity_dicts.AcceptValue(
                    id=followrequest.request_id,
                    actor=reverse("kronofoto:activitypub_data:archives:actor", kwargs={"short_name": archive.slug}),
                    object=activity_dicts.FollowValue(
                        id=followrequest.request_id,
                        actor=followrequest.remote_actor.profile,
                        object=followrequest.archive.ldid(),
                    ),
                ).dump()
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
                else:
                    logging.info('{code} {body!r} received from {address} for {data}'.format(code=resp.status_code, address=actor_data['inbox'], data=activity, body=resp.content))

    return TemplateResponse(
        request=request,
        template=template,
        context=context,
    )


from django.urls import path, include, register_converter, URLPattern, URLResolver
data_urls: Any = ([
    path("remotearchives/add", service_follows, name="service-follow-config"),
    path("remotearchives/send", service_follow_send, name="service-follow-send"),
    path("remoteservices/send", placeservice_follow_send, name="placeservice-follow-send"),
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
            return ServiceInboxResponder(body=request.body, actor=request.actor).archive_response(archive)
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
            print(request.GET)
            if form.is_valid():
                queryset = Donor.objects.filter(archive__slug=short_name, pk__gt=form.cleaned_data['pk']).order_by('id')[:100]
                schema : Union[CollectionPage, Collection] = CollectionPage()
                object_data = schema.dump(activity_dicts.CollectionPageValue.from_donor_queryset(queryset, short_name=short_name))
                return JsonLDResponse(object_data)
            else:
                queryset = Donor.objects.filter(archive__slug=short_name).order_by('id')[:100]
                schema = Collection()
                cv = activity_dicts.CollectionValue(
                    id=reverse("kronofoto:activitypub_data:archives:contributors:page", kwargs={"short_name": short_name}),
                    summary="Contributor List",
                    first=activity_dicts.CollectionPageValue.from_donor_queryset(queryset, short_name=short_name),
                )
                object_data = schema.dump(cv)
                return JsonLDResponse(object_data)

        @staticmethod
        def data(request: HttpRequest, short_name: str, pk: int) -> HttpResponse:
            donor : Donor = get_object_or_404(Donor.objects.all(), pk=pk, archive__slug=short_name)
            object_data = Contact().dump(activity_dicts.DonorValue.from_donor(donor))
            return JsonLDResponse(object_data)

    @register("photos", data_urls)
    class PhotoData:

        @staticmethod
        def data_page(request: HttpRequest, short_name: str) -> HttpResponse:
            form = Page(request.GET)
            if form.is_valid():
                queryset = Photo.objects.filter(archive__slug=short_name, pk__gt=form.cleaned_data['pk']).order_by('id')[:100]
                schema : Union[CollectionPage, Collection] = CollectionPage()
                object_data = schema.dump(activity_dicts.CollectionPageValue.from_photo_queryset(queryset, short_name=short_name))
                return JsonLDResponse(object_data)
            else:
                queryset = Photo.objects.filter(archive__slug=short_name).order_by('id')[:100]
                schema = Collection()
                cv = activity_dicts.CollectionValue(
                    id=reverse("kronofoto:activitypub_data:archives:photos:page", kwargs={"short_name": short_name}),
                    summary="Photo List",
                    first=activity_dicts.CollectionPageValue.from_photo_queryset(queryset, short_name=short_name)
                )
                object_data = schema.dump(cv)
                return JsonLDResponse(object_data)

        @staticmethod
        def data(request: HttpRequest, short_name: str, pk: int) -> HttpResponse:
            object : Photo = get_object_or_404(Photo.objects.all(), pk=pk, archive__slug=short_name)
            object_data = Image().dump(activity_dicts.PhotoValue.from_photo(object))
            return JsonLDResponse(object_data)
