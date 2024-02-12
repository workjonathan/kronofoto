from django.http import HttpResponse, HttpRequest, QueryDict, JsonResponse
from typing import Optional
from .base import ArchiveRequest, require_valid_archive
from django.core.serializers import serialize
import json
from ..models import Key
import hmac

def hmac_auth(func):
    def do_auth(request, *args, **kwargs):
        if 'Authorization' in request.headers:
            try:
                token, timestamp, sig = request.headers['Authorization'].split(" ")
                key = Key.objects.get(token=token)
                signer = hmac.new(key.key, digestmod="sha256")
                signer.update(request.method)
                signer.update(timestamp)
                signer.update(request.get_full_path())
                if sig == signer.hexdigest():
                    if abs(datetime.fromisoformat(timestamp) - datetime.now()) < timedelta(minutes=5):
                        request.user = key.user
            except:
                pass
        return func(request, *args, **kwargs)
    return do_auth



@hmac_auth
@require_valid_archive
def datadump(request: HttpRequest, short_name: Optional[str]=None, category: Optional[str]=None) -> HttpResponse:
    photos = ArchiveRequest(request=request, short_name=short_name, category=category).get_photo_queryset().select_related('donor', 'photographer', 'scanner').prefetch_related("terms", "tags").order_by('id')[:200]
    field = lambda name: lambda p: getattr(p, name)
    const = lambda value: lambda p: value

    def tags(p):
        terms = [term.term for term in p.terms.all()]
        tags = [tag.tag for tag in p.get_accepted_tags()]
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

    def place(p):
        if not p.place:
            return ""
        place = p.place
        names = []
        while place:
            names.append(place.name)
            place = place.parent
        return "^^".join(names)

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
    json.dump(data, response)
    return response
    return HttpResponse(json.dumps(data), content_type="application/json")
