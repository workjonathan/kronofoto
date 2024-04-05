from django.http import HttpResponse, HttpRequest, QueryDict, JsonResponse
from typing import Optional
from .base import ArchiveRequest, require_valid_archive
from django.core.serializers import serialize
import json
from django.urls import reverse
from ..models import Key, Archive, Tag, PhotoTag
from django.shortcuts import get_object_or_404
import hmac
from django.core.exceptions import PermissionDenied
from datetime import datetime, timedelta
from ..models import Photo, Place
from django.db.models import Prefetch
from collections import defaultdict

def hmac_auth(func):
    def do_auth(request, *args, **kwargs):
        if 'Authorization' in request.headers:
            try:
                token, timestamp, sig = request.headers['Authorization'].split(" ")
                key = Key.objects.get(token=token)
                signer = hmac.new(key.key.encode('utf-8'), digestmod="sha256")
                signer.update(request.method.encode('utf-8'))
                signer.update(timestamp.encode('utf-8'))
                signer.update(request.get_full_path().encode('utf-8'))
                if sig == signer.hexdigest():
                    if abs(datetime.fromisoformat(timestamp) - datetime.now()) < timedelta(minutes=5):
                        request.user = key.user
            except:
                pass
        return func(request, *args, **kwargs)
    return do_auth



@hmac_auth
@require_valid_archive
def datadump(request: HttpRequest, short_name: Optional[str]=None) -> HttpResponse:
    size = 200
    try:
        after = int(request.GET.get('after', 0))
    except ValueError:
        after = 0
    photos = Photo.objects.filter(archive__slug=short_name, id__gt=after).select_related('donor', 'photographer', 'scanner').prefetch_related('terms', 'place').order_by('id')[:size+1]
    phototags = defaultdict(list)
    for t in PhotoTag.objects.filter(photo__in=photos, accepted=True).select_related('tag', 'photo'):
        phototags[t.photo.id].append(t.tag)
    if not request.user.has_perm('archive.archive.{}.view'.format(short_name)):
        raise PermissionDenied
    field = lambda name: lambda p: getattr(p, name)
    const = lambda value: lambda p: value

    def tags(p):
        terms = [term.term for term in p.terms.all()]
        tags = [tag.tag for tag in phototags[p.id]]
        return "^^".join(terms+tags)

    def names(p):
        associated = []
        if p.donor:
            associated.append("{}|Contributor".format(p.donor))
        if p.photographer:
            associated.append("{}|Photographer".format(p.photographer))
        if p.scanner:
            associated.append("{}|Scanner".format(p.scanner))
        return "^^".join(associated)

    place_cache = {}
    def place(p):
        if not p.place:
            return ""
        if p.place.id not in place_cache:
            place_cache[p.place.id] = "^^".join(p2.name for p2 in p.place.get_ancestors(ascending=True, include_self=True))
        return place_cache[p.place.id]

    def coords(p):
        if p.location_point:
            return "{}|{}".format(p.location_point.y, p.location_point.x)
        else:
            return ""

    map = {
        'ID': field('id'),
        'member_of': const(""),
        'member_of_existing_entity_id': const(""),
        'publish': const("Y"),
        "model": const("Image"),
        'rights_statement': const('NO COPYRIGHT - UNITED STATES'),
        'held_by': const(""),
        'title': const(""),
        'digital_file': lambda p: p.original.url,
        'media_use': const("Original File"),
        'digital_origin': const("digitized other analog"),
        'creative_commons': const("Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)"),
        'resource_type': const("Image"),
        'description': field('caption'),
        'local_identifier': const(""),
        'family_name': const(""),
        'persons': names,
        'organizations': const(""),
        'origin_information': lambda p: "||{year}{circa}".format(year=p.year, circa="?" if p.circa else ""),
        'language': const(""),
        'genre': const(""),
        'subject': tags,
        'temporal_subject': const(""),
        'geographic_subject': place,
        'notes': const(""),
        'record_information': const(""),
        'coordinates': coords,
    }
    data = [{k: mapper(p) for (k, mapper) in map.items()} for p in photos]
    response = HttpResponse("", content_type="application/json")
    if len(data) > size:
        json.dump({
            "results": data[:size],
            "next": "{}?after={}".format(
                reverse("kronofoto:data-dump", kwargs={"short_name": short_name}),
                photos[photos.count()-1].id,
            )
        }, response)
    else:
        json.dump({
            "results": data[:size],
            "next": None,
        }, response)

    return response
