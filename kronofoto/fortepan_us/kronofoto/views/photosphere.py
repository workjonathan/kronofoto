from django.http import HttpRequest, JsonResponse, HttpResponse
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from fortepan_us.kronofoto.templatetags.widgets import markdown
from fortepan_us.kronofoto.reverse import reverse
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from .basetemplate import BaseTemplateMixin
from fortepan_us.kronofoto.models.photo import BackwardList, ForwardList, Photo, ImageData
from typing import Any, Dict, Optional
from fortepan_us.kronofoto.models.photosphere import PhotoSphere, PhotoSpherePair, MainStreetSet, PhotoSphereInfo
from fortepan_us.kronofoto.templatetags.widgets import image_url
from djgeojson.views import GeoJSONLayerView # type: ignore
from djgeojson.serializers import Serializer as GeoJSONSerializer # type: ignore
from django.db.models import OuterRef, Exists, Q, QuerySet
from django.conf import settings
from django import forms
from .base import ArchiveRequest
from dataclasses import dataclass
from django.utils.html import format_html, format_html_join, html_safe
from django.templatetags.static import static
import json

class DataParams(forms.Form):
    id = forms.IntegerField(required=True)

class MainstreetThumbnails(forms.Form):
    mainstreet = forms.IntegerField(required=True, widget=forms.HiddenInput)
    forward = forms.BooleanField(required=False, widget=forms.HiddenInput)
    offset = forms.IntegerField(required=True, widget=forms.HiddenInput)
    width = forms.IntegerField(required=True, widget=forms.HiddenInput)
    id = forms.IntegerField(required=True, widget=forms.HiddenInput)

@dataclass
class PhotoWrapper:
    photo: Photo
    mainstreetset: MainStreetSet

    @property
    def thumbnail(self) -> Optional[ImageData]:
        return self.photo.thumbnail

    def get_absolute_url(self, *args: Any, **kwargs: Any) -> str:
        pairs = PhotoSpherePair.objects.filter(photo__id=self.photo.id, photosphere__id=OuterRef("pk"))
        return PhotoSphere.objects.get(Exists(pairs), mainstreetset=self.mainstreetset).get_absolute_url()
        return "{}?{}".format(reverse("kronofoto:mainstreetview"), PhotoSphere.objects.get(Exists(pairs), mainstreetset=self.mainstreetset).id)

    @property
    def id(self) -> int:
        return self.photo.id

    @property
    def active(self) -> bool:
        return hasattr(self.photo, "active") and self.photo.active

    @property
    def year(self) -> Optional[int]:
        return self.photo.year

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
                    id=position.photo.id,
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

def photosphere_carousel(request: HttpRequest) -> HttpResponse:
    form = MainstreetThumbnails(request.GET)
    if form.is_valid():
        photos = Photo.objects.filter(photosphere__mainstreetset__id=form.cleaned_data['mainstreet'], year__isnull=False, is_published=True)
        photo = get_object_or_404(Photo.objects.all(), pk = form.cleaned_data['id'])
        offset = form.cleaned_data['offset']
        if form.cleaned_data['forward']:
            objects = ForwardList(queryset=photos, year=photo.year, id=photo.id).carousel_list(item_count=40)
        else:
            objects = BackwardList(queryset=photos, year=photo.year, id=photo.id).carousel_list(item_count=40)
            offset -= form.cleaned_data['width'] * (1 + 40)
        context = {
            'object_list': objects,
            'positioning': {
                'width': form.cleaned_data['width'],
                'offset': offset,
            },
        }
        return TemplateResponse(
            template="kronofoto/components/thumbnails.html",
            request=request,
            context=context,
        )


    return HttpResponse("", status=400)


def photosphere_view(request: HttpRequest) -> HttpResponse:
    query = DataParams(request.GET)
    if query.is_valid():
        object = get_object_or_404(PhotoSphere.objects.all(), pk=query.cleaned_data['id'])
        archiverequest = PhotoSphereRequest(request)
        context = archiverequest.common_context
        context['object'] = object
        context['hx_request'] = archiverequest.is_hx_request

        Photo = object._meta.get_field("photos").related_model
        assert not isinstance(Photo, str) and hasattr(Photo, "objects")
        if not object.mainstreetset:
            return HttpResponse("bad configuration: missing mainstreet set", status=400)
        context['thumbnails_form'] = MainstreetThumbnails(initial={
            "mainstreet": object.mainstreetset.id,
        })
        photos = Photo.objects.filter(photosphere__mainstreetset__id=object.mainstreetset.id, year__isnull=False, is_published=True)
        if object.photos.exists():
            photo = object.photos.all()[0]
            photo.active = True
            if photo.year is not None:
                backlist = BackwardList(queryset=photos, year=photo.year, id=photo.id).carousel_list(item_count=20)
                forwardlist = ForwardList(queryset=photos, year=photo.year, id=photo.id).carousel_list(item_count=20)
                context['prev_photo'] = PhotoWrapper(photo=backlist[0], mainstreetset=object.mainstreetset) if backlist else None
                context['next_photo'] = PhotoWrapper(photo=forwardlist[0], mainstreetset=object.mainstreetset) if forwardlist else None
                backlist.reverse()
                context['photos'] = [PhotoWrapper(photo=photo, mainstreetset=object.mainstreetset) for photo in backlist + [photo] + forwardlist]

        response = TemplateResponse(request, "kronofoto/pages/mainstreetview.html", context=context)
        assert object.location
        if archiverequest.is_hx_request:
            response['HX-Trigger'] = json.dumps({
                "kronofoto:map:marker:change": {
                    "x": object.location.x if object.location else 0,
                    "y": object.location.y if object.location else 0,
                }
            })
        return response
    else:
        return HttpResponse("Invalid query", status=400)

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
