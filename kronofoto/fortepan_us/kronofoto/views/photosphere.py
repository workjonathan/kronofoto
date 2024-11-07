from django.http import HttpRequest, JsonResponse, HttpResponse
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from fortepan_us.kronofoto.templatetags.widgets import markdown
from fortepan_us.kronofoto.reverse import reverse
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from .basetemplate import BaseTemplateMixin
from fortepan_us.kronofoto.models.photosphere import PhotoSphere, PhotoSpherePair, MainStreetSet, PhotoSphereInfo
from fortepan_us.kronofoto.templatetags.widgets import image_url
from typing import Any, Dict
from djgeojson.views import GeoJSONLayerView # type: ignore
from djgeojson.serializers import Serializer as GeoJSONSerializer # type: ignore
from django.db.models import OuterRef, Exists, Q, QuerySet
from django.utils.html import format_html, format_html_join, html_safe
from django import forms
from .base import ArchiveRequest
from django.templatetags.static import static
import json

class DataParams(forms.Form):
    id = forms.IntegerField(required=True)

def info_text(request: HttpRequest) -> HttpResponse:
    query = DataParams(request.GET)
    if query.is_valid():
        object = get_object_or_404(PhotoSphereInfo.objects.all(), pk=query.cleaned_data['id'])
        return TemplateResponse(
            template="kronofoto/components/mainstreet-info.html",
            context={
                "info": object,
            },
            request=request,
        )
    else:
        return HttpResponse(status_code=400)

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
                "infoboxes": [{
                    "id": info.id,
                    "yaw": info.yaw+(90-object.heading)/180*3.1416,
                    "pitch": info.pitch,
                    "image": static("kronofoto/images/info-icon.png"),
                } for info in object.photosphereinfo_set.all()]
            },
        }
        return JsonResponse(node)
    else:
        return JsonResponse({}, status=400)

class PhotoSphereRequest(ArchiveRequest):
    @property
    def base_template(self) -> str:
        if self.hx_target == 'fi-photosphere-metadata':
            return 'kronofoto/partials/mainstreetview_partial.html'
        else:
            return super().base_template

def photosphere_view(request: HttpRequest) -> HttpResponse:
    query = DataParams(request.GET)
    if query.is_valid():
        object = get_object_or_404(PhotoSphere.objects.all(), pk=query.cleaned_data['id'])
        archiverequest = PhotoSphereRequest(request)
        context = archiverequest.common_context
        context['object'] = object
        context['hx_request'] = archiverequest.is_hx_request

        return TemplateResponse(request, "kronofoto/pages/mainstreetview.html", context=context)
    else:
        return HttpResponse("Invalid query", status=400)


class PhotoSphereView(BaseTemplateMixin, DetailView):
    model = PhotoSphere

class MainStreetDetail(BaseTemplateMixin, DetailView):
    model = MainStreetSet
    template_name = "kronofoto/pages/mainstreet-detail.html"

def mainstreet_detail(request: HttpRequest, pk: int) -> HttpResponse:
    areq = ArchiveRequest(request=request)
    template_name = "kronofoto/pages/mainstreet-detail.html"
    object = get_object_or_404(MainStreetSet.objects.all(), pk=pk)
    context = areq.common_context
    context['object'] = object
    context['points'] = json.loads(GeoJSONSerializer().serialize([
        {
            'geom': photosphere.location,
            'pk': photosphere.pk,
            'popup': format_html('<h3>{}</h3>{}<br><a href="{}?id={}">View</a>'.format(photosphere.title, photosphere.description, reverse("kronofoto:mainstreetview"), photosphere.pk)),
        }
        for photosphere in object.photosphere_set.all()
    ]))
    return TemplateResponse(
        request=request,
        template=template_name,
        context=context,
    )

class MainStreetList(BaseTemplateMixin, ListView):
    template_name = "kronofoto/pages/mainstreet-list.html"
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
