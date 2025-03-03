from __future__ import annotations
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.template.response import TemplateResponse
from functools import cached_property
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
from typing import Any, Dict, Optional, Union, List, TypedDict, Tuple, Iterable
from fortepan_us.kronofoto.models.photosphere import PhotoSphere, PhotoSpherePair, MainStreetSet, PhotoSphereInfo
from fortepan_us.kronofoto.templatetags.widgets import image_url
from djgeojson.views import GeoJSONLayerView # type: ignore
from djgeojson.serializers import Serializer as GeoJSONSerializer # type: ignore
from django.db.models import OuterRef, Exists, Q, QuerySet, Subquery
from django_stubs_ext import WithAnnotations
from django.contrib.gis.db.models.functions import Distance
from django.conf import settings
from django import forms
from .base import ArchiveRequest
from dataclasses import dataclass
from django.utils.html import format_html, format_html_join, html_safe
from django.templatetags.static import static
import icontract
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

class LinksDict(TypedDict):
    nodeId: str
    gps: Tuple[float, float]

class ImagePlaneDict(TypedDict):
    url: str
    height: int
    width: int
    azimuth: float
    inclination: float
    distance: float
    id: int
    name: str
    href: str

class InfoBoxDict(TypedDict):
    id: int
    yaw: float
    pitch: float
    image: str
    content: str

class PhotoSphereDict(TypedDict):
    photos: List[ImagePlaneDict]
    infoboxes: List[InfoBoxDict]

class NodeData(TypedDict, total=False):
    id: str
    panorama: str
    sphereCorrection: Dict[str, float]
    gps: Tuple[float, float]
    links: List[LinksDict]
    data: PhotoSphereDict
    thumbnail: str


def photosphere_data(request: HttpRequest) -> JsonResponse:
    query = DataParams(request.GET)
    if query.is_valid():
        info_template = get_template(template_name="kronofoto/components/mainstreet-info.html")
        object = get_object_or_404(PhotoSphere.objects.all(), pk=query.cleaned_data['id'], is_published=True)
        links: List[LinksDict] = [
            {
                "nodeId": str(link.id),
                "gps": (link.location.x, link.location.y),
            }
            for link in object.links.all() if link.location is not None
        ]
        kwargs = {} if object.tour is None else {'photosphere__tour__id': object.tour.id}
        node: NodeData = {
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
                    name=position.photo.accession_number,
                    href=position.photo.get_absolute_url(),
                ) for position in PhotoSpherePair.objects.filter(photosphere__pk=object.pk, photosphere__is_published=True, **kwargs)],
                "infoboxes": [{
                    "id": info.id,
                    "yaw": info.yaw+(90-object.heading)/180*3.1416,
                    "pitch": info.pitch,
                    "image": static("kronofoto/images/info-icon.png"),
                    "content": info_template.render(context={"info": info}),
                } for info in object.photosphereinfo_set.all()]
            },
        }
        if object.photos.all().exists():
            photo = object.photos.all()[0]
            node["thumbnail"] = image_url(id=photo.id, path=photo.original.name, height=500, width=500)
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
        object: PhotoSphere = get_object_or_404(PhotoSphere.objects.all(), pk=form.cleaned_data['id'], is_published=True)
        photo = object.photos.all()[0]
        assert photo.year
        assert object.mainstreetset
        assert object.location
        kwargs = {} if object.tour is None else {'photosphere__tour__id': object.tour.id}
        nearby = PhotoSpherePair.objects.filter(
            photosphere__mainstreetset__id=object.mainstreetset.id,
            photosphere__location__within=object.location.buffer(0.003),
            photosphere__is_published=True,
            photo__year__isnull=False,
            photo__is_published=True,
            **kwargs,
        ).select_related("photo", "photosphere")
        offset = form.cleaned_data['offset']
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

class DistanceAnnotation(TypedDict):
    distance_: Any

class ClosestAnnotation(TypedDict):
    closest: Any

@dataclass
class ValidPhotoSphereView:
    pk: int
    request: HttpRequest

    @cached_property
    def object(self) -> PhotoSphere:
        return get_object_or_404(PhotoSphere.objects.all(), pk=self.pk, is_published=True)

    @cached_property
    def domain(self) -> str:
        return get_current_site(self.request).domain

    @cached_property
    def all_nearby(self) -> "QuerySet[WithAnnotations[PhotoSpherePair, DistanceAnnotation]]":
        assert self.object.location is not None
        kwargs = {} if self.object.tour is None else {'photosphere__tour__id': self.object.tour.id}
        return PhotoSpherePair.objects.filter(
            photosphere__mainstreetset__id=OuterRef("id"),
            photosphere__is_published=True,
            photosphere__location__within=self.object.location.buffer(0.003),
            photo__year__isnull=False,
            photo__is_published=True,
            **kwargs,
        ).annotate(distance_=Distance("photosphere__location", self.object.location)).order_by("distance_")

    @cached_property
    @icontract.ensure(lambda self, result: self.object.tour is None or result.count() > 10 or all((sphere := PhotoSpherePair.objects.get(id=r.closest).photosphere, sphere.is_published and (sphere.tour is not None) and (sphere.tour.id == self.object.tour.id))[-1] for r in result))
    def nearby_mainstreets(self) -> Iterable["WithAnnotations[MainStreetSet, ClosestAnnotation]"]:
        all_nearby = self.all_nearby
        return MainStreetSet.objects.filter(Exists(all_nearby)).annotate(closest=Subquery(all_nearby.values("id")[:1])).order_by("name")

    @cached_property
    def nearby(self) -> QuerySet[PhotoSpherePair]:
        assert self.object.mainstreetset is not None
        assert self.object.location is not None
        kwargs = {} if self.object.tour is None else {'photosphere__tour__id': self.object.tour.id}
        return PhotoSpherePair.objects.filter(
            photosphere__is_published=True,
            photosphere__mainstreetset__id=self.object.mainstreetset.id,
            photosphere__location__within=self.object.location.buffer(0.003),
            photo__year__isnull=False,
            photo__is_published=True,
            **kwargs,
        ).select_related("photo", "photosphere")

    @cached_property
    def photo(self) -> Photo | None:
        if self.object.photos.exists():
            photo = self.object.photos.all()[0]
        elif self.nearby.exists():
            photo = self.nearby[0].photo
        else:
            photo = None
        return photo

    @property
    @icontract.ensure(lambda self, result: getattr(result, "context_data", None) is None or result.context_data['object'].tour is None or str(result.context_data['object'].tour.id) in result.context_data['mainstreet_tiles'])
    def response(self) -> HttpResponse:
        object = self.object
        resolver = get_resolver()
        if object.tour is None:
            u = django_reverse("kronofoto:vector-tiles:photosphere", kwargs=dict(zoom=1, mainstreet=1, x=1, y=1))
        else:
            u = django_reverse("kronofoto:vector-tiles:photosphere", kwargs=dict(tour=1, zoom=1, mainstreet=1, x=1, y=1))
        info = resolver.resolve(u)
        if object.mainstreetset is None:
            return HttpResponse("bad configuration: missing mainstreet set", status=400)
        pattern = "/" + info.route.replace("<int:zoom>", "{z}").replace(
            "<int:x>", "{x}"
        ).replace("<int:y>", "{y}").replace("<int:mainstreet>", str(object.mainstreetset.id))
        if object.tour is not None:
            pattern = pattern.replace("<int:tour>", str(object.tour.id))
        tile_set = "{}//{}{}".format(settings.KF_URL_SCHEME, self.domain, pattern)
        archiverequest = PhotoSphereRequest(self.request)
        context = archiverequest.common_context
        context['object'] = object
        context['hx_request'] = archiverequest.is_hx_request
        context['mainstreet_tiles'] = tile_set

        context['thumbnails_form'] = MainstreetThumbnails(initial={
            "mainstreet": object.mainstreetset.id,
        })
        if not object.location:
            return HttpResponse("bad configuration: missing location", status=400)
        context['mainstreet_links'] = [
            {
                "set": set,
                "photosphere_href": PhotoSpherePair.objects.get(id=set.closest).photosphere.get_absolute_url(),
            }
            for set in self.nearby_mainstreets
        ]
        photo = self.photo
        nearby = self.nearby
        if photo:
            setattr(photo, "active", True)
            if photo.year is not None:
                backlist : List = PhotoPairBackwardList(queryset=nearby, id=photo.id, year=photo.year).carousel_list(item_count=20, func=lambda pair: PhotoWrapper(photo=pair.photo, photosphere=pair.photosphere))
                forwardlist : List = PhotoPairForwardList(queryset=nearby, id=photo.id, year=photo.year).carousel_list(item_count=20, func=lambda pair: PhotoWrapper(photo=pair.photo, photosphere=pair.photosphere))
                context['prev_photo'] = backlist[0]
                context['next_photo'] = forwardlist[0]
                backlist.reverse()
                context['photos'] = backlist
                context['photos'].append(PhotoWrapper(photo=photo, photosphere=object))
                context['photos'] += forwardlist

        response = TemplateResponse(self.request, "kronofoto/pages/mainstreetview.html", context=context)
        assert object.location
        if archiverequest.is_hx_request:
            response['HX-Trigger'] = json.dumps({
                "kronofoto:map:marker:change": {
                    "x": object.location.x if object.location else 0,
                    "y": object.location.y if object.location else 0,
                }
            })
        return response



def photosphere_view(request: HttpRequest) -> HttpResponse:
    query = DataParams(request.GET)
    if query.is_valid():
        return ValidPhotoSphereView(
            pk=query.cleaned_data['id'],
            request=request,
        ).response
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
