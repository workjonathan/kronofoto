from django.views.generic.list import BaseListView
from .jsonresponse import JSONResponseMixin
import json
from fortepan_us.kronofoto.models.tag import Tag
from fortepan_us.kronofoto.models.donor import Donor
from fortepan_us.kronofoto.models import Place, Photo
from django.db.models import Q, Exists, OuterRef, F, QuerySet
from django.db.models.functions import Upper
from django.http import HttpResponse, HttpRequest
import re
from functools import reduce
from operator import or_
from typing import Any, List, Dict

SPLIT = r"\[|\]|-| |,"
archive_id_tag = re.compile(r"\[\s*([^\[\]]*[^\[\]\s]+)\s*-\s*(\d+)\s*\]")
id_tag = re.compile(r"\[\s*(\d+)\s*\]")

def contributor_search(request: HttpRequest) -> HttpResponse:
    txts = request.GET.get('q', '').split(', ')
    donors = Donor.objects.all()
    for s in txts:
        if s:
            donors = donors.filter(Q(first_name__istartswith=s) | Q(last_name__istartswith=s))
    donors = Photo.objects.filter_donated(donors)
    results = [{'id': donor.id, 'text': str(donor)} for donor in donors[:20]]
    response = HttpResponse(content_type="application/json")
    json.dump({"results": results, "pagination": {"more": False}}, response)
    return response

def place_search(request: HttpRequest, *, require_photo: bool=True) -> HttpResponse:
    print(require_photo)
    txt = request.GET.get('q', '').upper()
    if len(txt) < 2:
        return HttpResponse("Invalid request", status=400)
    tmp = list(txt)
    tmp[-1] = chr(1 + ord(tmp[-1]))
    places = Place.objects.annotate(ufullname=Upper('fullname')).filter(ufullname__gte=txt, ufullname__lt=''.join(tmp))
    #places = Place.objects.filter(fullname__istartswith=txt)#, fullname__lt=''.join(tmp))
    # Places that match search and have at least 1 photo.
    # A place p has a photo if
        # photo.place and photo.place's ancestors include place p...
        # Photo.place is spatially within place p
        # Photo.location_point is spatially within place p
    if require_photo:
        places = places.filter(
            Exists(
                Photo.objects.filter(places__id=OuterRef('id'))
            )
        ).order_by('fullname')
    results = [{'id': place.id, 'text': str(place)} for place in places[:20]]
    response = HttpResponse(content_type="application/json")
    json.dump({"results": results, "pagination": {"more": False}}, response)
    return response

class ContributorSearchView(JSONResponseMixin, BaseListView):
    def get_queryset(self) -> QuerySet:
        if 'term' not in self.request.GET:
            return Donor.objects.none()
        txt = self.request.GET['term']
        clauses = []
        snip = 999999
        for match in re.finditer(archive_id_tag, txt):
            snip = min(snip, match.start())
            clauses.append(Q(id=int(match.group(2))))
        txt = txt[:snip]
        for s in re.split(SPLIT, txt):
            if s:
                try:
                    id = int(s)
                    clauses.append(Q(id=id))
                except ValueError:
                    clauses.append(Q(first_name__icontains=s))
                    clauses.append(Q(last_name__icontains=s))

        if clauses:
            return Donor.objects.filter(reduce(or_, clauses))[:20]

        else:
            return Donor.objects.none()

    def get_autocomplete_data(self, object: Donor) -> Dict[str, Any]:
        label = "{} [{}-{}]".format(object, object.archive.slug, object.id)
        return {'id': object.id, 'value': label, 'label': label}

    def get_data(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            self.get_autocomplete_data(object)
            for object in context['object_list']
        ]

    def render_to_response(self, context: Dict[str, Any], **kwargs: Any) -> HttpResponse:
        return self.render_to_json_response(context, safe=False, **kwargs)

class TagSearchView(JSONResponseMixin, BaseListView):
    def get_queryset(self) -> QuerySet:
        if 'term' in self.request.GET:
            return Tag.objects.filter(
                tag__icontains=self.request.GET['term'], phototag__accepted=True
            ).values('tag', 'id').distinct()[:10]
        return Tag.objects.none()

    def get_data(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            dict(id=tag['id'], value=tag['tag'], label=tag['tag'])
            for tag in context['object_list']
        ]

    def render_to_response(self, context: Dict[str, Any], **kwargs: Any) -> HttpResponse:
        return self.render_to_json_response(context, safe=False, **kwargs)
