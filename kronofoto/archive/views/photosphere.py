from django.http import HttpRequest, JsonResponse, HttpResponse
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from ..reverse import reverse
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from .basetemplate import BaseTemplateMixin
from ..models.photosphere import PhotoSphere, PhotoSpherePair, MainStreetSet
from archive.templatetags.widgets import image_url
from typing import Any, Dict
from djgeojson.views import GeoJSONLayerView # type: ignore
from django.db.models import OuterRef, Exists, Q, QuerySet
from django import forms
from .base import ArchiveRequest

class DataParams(forms.Form):
    id = forms.IntegerField(required=True)


def photosphere_data(request: HttpRequest) -> JsonResponse:
    query = DataParams(request.GET)
    if query.is_valid():
        object = get_object_or_404(PhotoSphere.objects.all(), pk=query.cleaned_data['id'])
        links = [
            {
                "nodeId": str(link.id),
                "gps": [link.location.x, link.location.y], # type: ignore
            }
            for link in object.links.all()
        ]
        node = {
            "id": str(object.id),
            "panorama": object.image.url,
            "sphereCorrection": {"pan": (object.heading-90)/180 * 3.1416},
            "gps": [object.location.x, object.location.y], # type: ignore
            "links": links,
            'data': {
                "photos": [dict(
                    url=image_url(id=position.photo.id, path=position.photo.original.name, height=1400),
                    height=position.photo.h700.height if position.photo.h700 else 700,
                    width=position.photo.h700.width if position.photo.h700 else 400,
                    azimuth=position.azimuth+object.heading-90,
                    inclination=position.inclination,
                    distance=position.distance,
                ) for position in PhotoSpherePair.objects.filter(photosphere__pk=object.pk)],
            },
        }
        return JsonResponse(node)
    else:
        return JsonResponse({}, status=400)

class PhotoSphereRequest(ArchiveRequest):
    @property
    def base_template(self) -> str:
        if self.hx_target == 'fi-photosphere-metadata':
            return 'archive/photosphere_partial.html'
        else:
            return super().base_template

def photosphere_view(request: HttpRequest) -> HttpResponse:
    query = DataParams(request.GET)
    if query.is_valid():
        object = get_object_or_404(PhotoSphere.objects.all(), pk=query.cleaned_data['id'])
        archiverequest = PhotoSphereRequest(request)
        context = archiverequest.common_context
        context['object'] = object

        return TemplateResponse(request, "archive/photosphere_detail.html", context=context)
    else:
        return HttpResponse("Invalid query", status=400)


class PhotoSphereView(BaseTemplateMixin, DetailView):
    model = PhotoSphere

class MainStreetDetail(BaseTemplateMixin, DetailView):
    model = MainStreetSet

class MainStreetList(BaseTemplateMixin, ListView):
    model = MainStreetSet
    def get_queryset(self) -> QuerySet:
        return MainStreetSet.objects.filter(Exists(PhotoSphere.objects.filter(Q(mainstreetset__id=OuterRef('pk')))))


class MainStreetGeojson(GeoJSONLayerView):
    model = PhotoSphere
    geometry_field = 'location'
    with_modelname = False
    properties = ['title', 'description']
    def get_queryset(self) -> QuerySet:
        return PhotoSphere.objects.filter(mainstreetset__id=self.kwargs['pk'])
