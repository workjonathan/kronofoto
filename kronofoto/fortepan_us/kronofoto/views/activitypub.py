from django.http import HttpResponse, HttpRequest, JsonResponse
from typing import Any, Protocol, Dict, List
from django.contrib.sites.shortcuts import get_current_site
from ..reverse import reverse
from django.shortcuts import get_object_or_404
from fortepan_us.kronofoto.models import Archive, FollowArchiveRequest, RemoteActor, OutboxActivity, RemoteArchive
import json
import parsy # type: ignore
from django.core.cache import cache
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import base64

def decode_signature(signature: str) -> Dict[str, str]:
    quoted_string = parsy.string('"') >> parsy.regex(r'[^"]*') << parsy.string('"')
    key = parsy.regex(r'[^=]*')
    pair = parsy.seq(key << parsy.string("="), quoted_string)
    return dict(pair.sep_by(parsy.string(",")).parse(signature))

def decode_signature_headers(signature_headers: str) -> List[str]:
    return parsy.regex('[^ ]*').sep_by(parsy.whitespace).parse(signature_headers)


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
    if request.method == "POST":
        signature_parts = decode_signature(request.headers.get("Signature", ""))
        if any(key not in signature_parts for key in ["signature", "headers", "keyId"]):
            return HttpResponse(status=401)
        signature_headers = []
        for header in decode_signature_headers(signature_parts['headers']):
            if header == "(request-target)":
                signature_headers.append("(request-target): {} {}".format(request.method.lower(), request.path))
            else:
                signature_headers.append("{}: {}".format(header, request.headers.get(header)))
        data = json.loads(request.body.decode("utf-8"))
        actor, _ = RemoteActor.objects.get_or_create(profile=data['actor'])
        pubkey_str = actor.public_key()
        if not pubkey_str:
            return HttpResponse(status=401)

        public_key = load_pem_public_key(pubkey_str)
        assert isinstance(public_key, RSAPublicKey)
        try:
            public_key.verify(
                base64.b64decode(signature_parts['signature']),
                '\n'.join(signature_headers).encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        except InvalidSignature:
            return HttpResponse(status=401)
        for activity in OutboxActivity.objects.filter(
            body__id=data['object']['id'],
            body__type="Follow",
            body__actor=data['object']['actor'],
        ):
            actor, created = RemoteActor.objects.get_or_create(
                profile=data['actor'],
                defaults={
                    "actor_follows_app": False,
                    "app_follows_actor": False,
                }
            )
            RemoteArchive.objects.get_or_create(actor=actor)
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
