from django.http import HttpResponse, HttpRequest, JsonResponse
from typing import Any, Protocol, Dict, List
from django.contrib.sites.shortcuts import get_current_site
from ..reverse import reverse
from django.shortcuts import get_object_or_404
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
from typing import Any, ClassVar
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from fortepan_us.kronofoto.middleware import SignatureHeaders, decode_signature, decode_signature_headers

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

def get_donor_data(*, pk: int) -> Dict[str, Any]:
    donor : Donor = get_object_or_404(Donor.objects.all(), pk=pk)
    return donor.activity_dict

@require_json_ld
def get_data(request:HttpRequest, type: str, pk: int) -> HttpResponse:
    if type == "contributor":
        object_data = get_donor_data(pk=pk)
    else:
        return HttpResponse(status=404)

    return JsonLDResponse(object_data)

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

@require_json_ld
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
