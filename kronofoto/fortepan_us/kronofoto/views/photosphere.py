from django.http import HttpRequest, JsonResponse, HttpResponse
from django.template.response import TemplateResponse
from django.contrib.sites.shortcuts import get_current_site
from django.urls import get_resolver, reverse as django_reverse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from fortepan_us.kronofoto.templatetags.widgets import markdown
from fortepan_us.kronofoto.reverse import reverse, resolve
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from .basetemplate import BaseTemplateMixin
from fortepan_us.kronofoto.models.photo import BackwardList, ForwardList, Photo, ImageData, CarouselList
from typing import Any, Dict, Optional, Union, List
from fortepan_us.kronofoto.models.photosphere import PhotoSphere, PhotoSpherePair, MainStreetSet, PhotoSphereInfo
from fortepan_us.kronofoto.templatetags.widgets import image_url
from djgeojson.views import GeoJSONLayerView # type: ignore
from djgeojson.serializers import Serializer as GeoJSONSerializer # type: ignore
from django.db.models import OuterRef, Exists, Q, QuerySet, Subquery
from django.contrib.gis.db.models.functions import Distance
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
    forward = forms.BooleanField(required=False, widget=forms.HiddenInput)
    offset = forms.IntegerField(required=True, widget=forms.HiddenInput)
    width = forms.IntegerField(required=True, widget=forms.HiddenInput)
    id = forms.IntegerField(required=True, widget=forms.HiddenInput)

@dataclass
class PhotoWrapper:
    photo: Photo
    photosphere: PhotoSphere

    @property
    def thumbnail(self) -> Optional[ImageData]:
        return self.photo.thumbnail

    def get_absolute_url(self, *args: Any, **kwargs: Any) -> str:
        return self.photosphere.get_absolute_url()

    @property
    def id(self) -> int:
        return self.photosphere.id

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
        info_template = get_template(template_name="kronofoto/components/mainstreet-info.html")
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
                    url=image_url(photo=position.photo, height=1400),
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
                    "content": info_template.render(context={"info": info}),
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
        object: PhotoSphere = get_object_or_404(PhotoSphere.objects.all(), pk=form.cleaned_data['id'])
        photo = object.photos.all()[0]
        assert object.mainstreetset
        assert object.location
        nearby = PhotoSpherePair.objects.filter(
            photosphere__mainstreetset__id=object.mainstreetset.id,
            photosphere__location__within=object.location.buffer(0.003),
            photo__year__isnull=False,
            photo__is_published=True,
        ).select_related("photo", "photosphere")
        offset = form.cleaned_data['offset']
        assert photo.year
        if form.cleaned_data['forward']:
            objects = PhotoPairForwardList(queryset=nearby, year=photo.year, id=photo.id).carousel_list(item_count=40, func=lambda pair: PhotoWrapper(photo=pair.photo, photosphere=pair.photosphere))
        else:
            objects = PhotoPairBackwardList(queryset=nearby, year=photo.year, id=photo.id).carousel_list(item_count=40, func=lambda pair: PhotoWrapper(photo=pair.photo, photosphere=pair.photosphere))
            offset -= form.cleaned_data['width'] * (1 + 40)
        context = {
            'object_list': objects,
            'positioning': {
                'width': form.cleaned_data['width'],
                'offset': offset,
            },
            'is_mainstreet': True,
        }
        return TemplateResponse(
            template="kronofoto/components/thumbnails.html",
            request=request,
            context=context,
        )


    return HttpResponse("", status=400)

@dataclass
class PhotoPairBackwardList(CarouselList):
    year: int
    id: int

    @property
    def keyset(self) -> QuerySet:
        return self.queryset.filter(Q(photo__year__lt=self.year) | Q(photo__year=self.year, photo__id__lt=self.id)).order_by('-photo__year', '-photo__id')

    @property
    def wrapped_queryset(self) -> QuerySet:
        return self.queryset.order_by('-photo__year', '-photo__id')

@dataclass
class PhotoPairForwardList(CarouselList):
    year: int
    id: int

    @property
    def keyset(self) -> QuerySet:
        return self.queryset.filter(Q(photo__year__gt=self.year) | Q(photo__year=self.year, photo__id__gt=self.id)).order_by('photo__year', 'photo__id')

    @property
    def wrapped_queryset(self) -> QuerySet:
        return self.queryset.order_by('photo__year', 'photo__id')

def photosphere_view(request: HttpRequest) -> HttpResponse:
    query = DataParams(request.GET)
    if query.is_valid():
        object = get_object_or_404(PhotoSphere.objects.all(), pk=query.cleaned_data['id'])
        resolver = get_resolver()
        u = django_reverse("kronofoto:vector-tiles:photosphere", kwargs=dict(zoom=1, mainstreet=1, x=1, y=1))
        info = resolver.resolve(u)
        assert object.mainstreetset
        pattern = "/" + info.route.replace("<int:zoom>", "{z}").replace(
            "<int:x>", "{x}"
        ).replace("<int:y>", "{y}").replace("<int:mainstreet>", str(object.mainstreetset.id))
        tile_set = "{}//{}{}".format(settings.KF_URL_SCHEME, get_current_site(request).domain, pattern)
        archiverequest = PhotoSphereRequest(request)
        context = archiverequest.common_context
        context['object'] = object
        context['hx_request'] = archiverequest.is_hx_request
        context['mainstreet_tiles'] = tile_set

        Photo = object._meta.get_field("photos").related_model
        assert not isinstance(Photo, str) and hasattr(Photo, "objects")
        if not object.mainstreetset:
            return HttpResponse("bad configuration: missing mainstreet set", status=400)
        context['thumbnails_form'] = MainstreetThumbnails(initial={
            "mainstreet": object.mainstreetset.id,
        })
        assert object.location
        all_nearby = PhotoSpherePair.objects.filter(
            photosphere__mainstreetset__id=OuterRef("id"),
            photosphere__location__within=object.location.buffer(0.003),
            photo__year__isnull=False,
            photo__is_published=True,
        ).annotate(distance_=Distance("photosphere__location", object.location)).order_by("distance_")
        context['mainstreet_links'] = [
            {
                "set": set,
                "photosphere_href": PhotoSpherePair.objects.get(id=set.closest).photosphere.get_absolute_url(),
            }
            for set in MainStreetSet.objects.filter(Exists(all_nearby)).annotate(closest=Subquery(all_nearby.values("id")[:1])).order_by("name")
        ]
        nearby = PhotoSpherePair.objects.filter(
            photosphere__mainstreetset__id=object.mainstreetset.id,
            photosphere__location__within=object.location.buffer(0.003),
            photo__year__isnull=False,
            photo__is_published=True,
        ).select_related("photo", "photosphere")
        if object.photos.exists():
            photo = object.photos.all()[0]
        elif nearby.exists():
            photo = nearby[0].photo
        else:
            photo = None
        if photo:
            photo.active = True # type: ignore
            if photo.year is not None:
                backlist : List = PhotoPairBackwardList(queryset=nearby, id=photo.id, year=photo.year).carousel_list(item_count=20, func=lambda pair: PhotoWrapper(photo=pair.photo, photosphere=pair.photosphere))
                forwardlist : List = PhotoPairForwardList(queryset=nearby, id=photo.id, year=photo.year).carousel_list(item_count=20, func=lambda pair: PhotoWrapper(photo=pair.photo, photosphere=pair.photosphere))
                context['prev_photo'] = backlist[0]
                context['next_photo'] = forwardlist[0]
                backlist.reverse()
                context['photos'] = backlist
                context['photos'].append(PhotoWrapper(photo=photo, photosphere=object))
                context['photos'] += forwardlist

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
