from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from ..reverse import reverse
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from .basetemplate import BaseTemplateMixin
from ..models.photosphere import PhotoSphere, PhotoSpherePair, MainStreetSet
from typing import Any, Dict
from djgeojson.views import GeoJSONLayerView # type: ignore
from django.db.models import OuterRef, Exists, Q, QuerySet

def photosphere_data(request: HttpRequest, pk: int) -> JsonResponse:
    object = get_object_or_404(PhotoSphere.objects.all(), pk=pk)
    links = [
        {
            "nodeId": str(link.id),
            "gps": [link.location.x, link.location.y],
            "GET": reverse("kronofoto:mainstreetview.json", kwargs={'pk': link.id}),
        }
        for link in object.links.all()
    ]
    node = {
        "id": str(object.id),
        "panorama": object.image.url,
        "sphereCorrection": {"pan": (object.heading-90)/180 * 3.1416},
        "gps": [object.location.x, object.location.y],
        "links": links,
        'data': {
            "photos": [dict(
                url=position.photo.original.url,
                height=position.photo.h700.height,
                width=position.photo.h700.width,
                azimuth=position.azimuth+object.heading-90,
                inclination=position.inclination,
                distance=position.distance,
            ) for position in PhotoSpherePair.objects.filter(photosphere__pk=object.pk)],
        },
    }
    return JsonResponse(node)

class PhotoSphereView(BaseTemplateMixin, DetailView):
    model = PhotoSphere

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        object = context['object']
        links = [
            {
                "nodeId": str(link.id),
                "gps": [link.location.x, link.location.y],
                "GET": reverse("kronofoto:mainstreetview.json", kwargs={'pk': link.id}),
            }
            for link in object.links.all()
        ]
        nodes = [{
            "id": str(object.id),
            "panorama": object.image.url,
            "sphereCorrection": {"pan": (object.heading-90)/180 * 3.1416},
            "gps": [object.location.x, object.location.y],
            "links": links,
            'data': {
                "photos": [dict(
                    url=position.photo.original.url,
                    height=position.photo.h700.height,
                    width=position.photo.h700.width,
                    azimuth=position.azimuth+object.heading-90,
                    inclination=position.inclination,
                    distance=position.distance,
                ) for position in PhotoSpherePair.objects.filter(photosphere__pk=object.pk)],
            },
        }]

        context['sphere_data'] = {
            "startNodeId": str(object.id),
            "nodes": nodes,
        }
        return context

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
