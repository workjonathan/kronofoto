from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from .basetemplate import BaseTemplateMixin
from ..models.photosphere import PhotoSphere, PhotoSpherePair, MainStreetSet
from typing import Any, Dict
from djgeojson.views import GeoJSONLayerView # type: ignore
from django.db.models import OuterRef, Exists, Q, QuerySet

class PhotoSphereView(BaseTemplateMixin, DetailView):
    model = PhotoSphere

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        object = context['object']
        context['sphere_data'] = dict(
            sphere_image_url=object.image.url,
            photos=[dict(
                url=position.photo.original.url,
                height=position.photo.original.height,
                width=position.photo.original.width,
                azimuth=position.azimuth,
                inclination=position.inclination,
                distance=position.distance,
             ) for position in PhotoSpherePair.objects.filter(photosphere__pk=object.pk)],
        )
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
