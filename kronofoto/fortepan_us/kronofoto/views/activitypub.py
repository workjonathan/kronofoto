from django.http import HttpResponse, HttpRequest, JsonResponse
from typing import Any, Protocol
from django.contrib.sites.shortcuts import get_current_site
from ..reverse import reverse
from django.shortcuts import get_object_or_404
from fortepan_us.kronofoto.models import Archive

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
    return HttpResponse(status=401)

@require_json_ld
def archive_outbox(request: HttpRequest, short_name: str) -> HttpResponse:
    archive = get_object_or_404(Archive.objects.all(), slug=short_name)
    return JsonLDResponse({})
