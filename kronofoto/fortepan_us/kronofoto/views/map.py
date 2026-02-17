from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from typing import Optional, Any, overload, Dict
from .base import ArchiveRequest, PhotoQuerySet, ArchiveReference
from fortepan_us.kronofoto.forms import BoundsSearchForm, Bounds, ListForm, ListMemberForm
from django.forms import formset_factory
from django.contrib.gis.geos import Polygon
from django.contrib.gis.db.models.functions import Centroid
from functools import cached_property
from fortepan_us.kronofoto.models import Photo, PhotoSphere, PhotoSpherePair, Collection
from fortepan_us.kronofoto.views.vector_tiles import PhotoMapTile, TileBounds
from django.db.models import QuerySet, Q, Exists, Subquery, OuterRef
from dataclasses import dataclass
from fortepan_us.kronofoto.reverse import reverse

@dataclass
class MapRequest(ArchiveRequest):
    detail_template: str = "kronofoto/partials/map-detail_partial.html"
    @cached_property
    def form(self) -> BoundsSearchForm:
        return BoundsSearchForm(self.request.GET)

    @property
    def base_template(self) -> str:
        if self.hx_target == "fi-map-result":
            return "kronofoto/partials/map_partial.html"
        elif self.hx_target == "fi-map-figure":
            return self.detail_template
        else:
            return super().base_template

    @property
    def map_bounds(self) -> Bounds:
        return self.form.cleaned_data['map_bounds']

    def get_photo_queryset(self, *, use_spatial: bool=True, include_geocoded: Optional[bool]=None) -> PhotoQuerySet:
        if not use_spatial:
            return super().get_photo_queryset()
        qs = super().get_photo_queryset().filter(place__isnull=False).filter(place__geom__isnull=False).order_by().annotate(centroid=Centroid("place__geom"))
        q = Q()
        if (self.form.is_valid() and
            self.form.cleaned_data['search_bounds'] is not None
        ):
            bounds = Polygon.from_bbox(
                self.form.cleaned_data['search_bounds'].as_tuple()
            )
            # use db functions area and intersection to calculate percentage of the intersection and include places that
            # have more than some threshold intersection with our bounds.
            # also exclude places with no intersection to potentially speed it up.
            # Reasonable alternative: is the centroid in view? Most of the time, the centroid will not be in view if we
            # are looking at a city and the polygon is large (like the USA). Will fail for some locations.
            q &= Q(centroid__within=bounds)
            #q = Q(place__geom__within=bounds)
        if include_geocoded is not None:
            q &= Q(location_point__isnull=not include_geocoded)
        return qs.filter(q)


def map_list(request: HttpRequest, *, short_name: Optional[str]=None, domain: Optional[str]=None, category: Optional[str]=None) -> HttpResponse:
    archive_ref = None
    if short_name:
        archive_ref = ArchiveReference(short_name, domain)
    areq = MapRequest(request=request, archive_ref=archive_ref, category=category)

    context = areq.common_context
    url_kwargs = areq.url_kwargs
    tile_url = reverse(
        "kronofoto:photo-tile", kwargs=dict(**url_kwargs, **{"zoom": 0, "x": 0, "y": 0,}),
    )
    tile_url = tile_url.replace("0/0/0", "{z}/{x}/{y}")
    tile_query_params = areq.get_params.copy()
    for k in ("bounds:west", "bounds:east", "bounds:north", "bounds:south"):
        try:
            tile_query_params.pop(k)
        except KeyError:
            pass
    if tile_query_params:
        tile_url += "?" + tile_query_params.urlencode()
    qs = areq.get_photo_queryset(include_geocoded=False).prefetch_related('photosphere_set')[:48]
    context["tile_url"] = tile_url
    context['form'] = areq.form
    context['no_image'] = True
    context['photos'] = qs
    context['bounds'] = areq.map_bounds
    context['mapviewclass'] = 'current-view'
    if areq.is_hx_request and areq.hx_target == "image-viewer":
        return TemplateResponse(request, context=context, template="kronofoto/partials/map_partial.html")
    if areq.is_hx_request and areq.hx_target == "photo-grid":
        template = "kronofoto/pages/map/map.html"
    else:
        template = "kronofoto/pages/map/map.html"
    return TemplateResponse(request, context=context, template=template)

def detail_photosphere(request: HttpRequest, *, photosphere: int, short_name: Optional[str]=None, domain: Optional[str]=None, category: Optional[str]=None) -> HttpResponse:
    archive_ref = None
    if short_name:
        archive_ref = ArchiveReference(short_name, domain)
    areq = MapRequest(request=request, archive_ref=archive_ref, category=category, detail_template="kronofoto/partials/map-detail-photosphere_partial.html")
    context = areq.common_context
    qs = areq.get_photo_queryset()
    url_kwargs = areq.url_kwargs
    tile_url = reverse(
        "kronofoto:photo-tile", kwargs=dict(**url_kwargs, **{"zoom": 0, "x": 0, "y": 0,}),
    )
    tile_url = tile_url.replace("0/0/0", "{z}/{x}/{y}")
    tile_query_params = areq.get_params.copy()
    for k in ("bounds:west", "bounds:east", "bounds:north", "bounds:south"):
        try:
            tile_query_params.pop(k)
        except KeyError:
            pass
    if tile_query_params:
        tile_url += "?" + tile_query_params.urlencode()
    context['form'] = areq.form
    context['tile_url'] = tile_url
    context['photos'] = qs[:48]
    context['bounds'] = areq.map_bounds
    context['mapviewclass'] = 'current-view'
    photospheres = PhotoSphere.objects.filter(Exists(PhotoSpherePair.objects.filter(photosphere_id=OuterRef("id"), photo__id__in=qs)), is_published=True)
    context['photosphere'] = get_object_or_404(photospheres, id=photosphere)
    return TemplateResponse(request, context=context, template="kronofoto/pages/map/map-detail-photosphere.html")

def subtile_detail(request: HttpRequest, *, zoom: int, x: int, y: int, subx: int, suby: int, short_name: Optional[str]=None, domain: Optional[str]=None, category: Optional[str]=None) -> HttpResponse:

    archive_ref = None
    if short_name:
        archive_ref = ArchiveReference(short_name, domain)
    areq = ArchiveRequest(request=request, archive_ref=archive_ref, category=category)
    pmt = PhotoMapTile(
        zoom=zoom,
        x=x,
        y=y,
        queryset=areq.get_photo_queryset(),
        url_kwargs=areq.url_kwargs,
        get_params=areq.get_params,
    )
    tb = TileBounds(*pmt.bbox(3857).extent)
    poly = tb.get_polygon(subx, suby)
    photos = areq.get_photo_queryset().filter(location_point__within=poly)
    context = areq.common_context
    context['photos'] = photos
    return TemplateResponse(request=request, template="kronofoto/components/map/bubble_detail.html", context=context)

def map_detail(request: HttpRequest, *, photo: int, short_name: Optional[str]=None, domain: Optional[str]=None, category: Optional[str]=None) -> HttpResponse:
    archive_ref = None
    if short_name:
        archive_ref = ArchiveReference(short_name, domain)
    areq = MapRequest(request=request, archive_ref=archive_ref, category=category)
    context = areq.common_context
    url_kwargs = areq.url_kwargs
    tile_url = reverse(
        "kronofoto:photo-tile", kwargs=dict(**url_kwargs, **{"zoom": 0, "x": 0, "y": 0,}),
    )
    tile_url = tile_url.replace("0/0/0", "{z}/{x}/{y}")
    tile_query_params = areq.get_params.copy()
    for k in ("bounds:west", "bounds:east", "bounds:north", "bounds:south"):
        try:
            tile_query_params.pop(k)
        except KeyError:
            pass
    if tile_query_params:
        tile_url += "?" + tile_query_params.urlencode()
    context["list_url"] = "{}?{}".format(reverse("kronofoto:map", kwargs={k: v for (k,v) in url_kwargs.items() if k != "photo"}), areq.get_params.urlencode())
    context['no_image'] = False
    context['tile_url'] = tile_url
    qs = areq.get_photo_queryset(include_geocoded=False).prefetch_related("photosphere_set")
    context['form'] = areq.form
    context['new_list_form'] = ListForm()
    context['old_list_form'] = formset_factory(ListMemberForm, extra=0)(initial=[
        {
            'membership': bool(o.membership), # type: ignore
            'collection': o.id, # type: ignore
            'name': o.name, # type: ignore
            'photo': photo,
        }
        for o in (Collection.objects.filter(owner=request.user).count_photo_instances(photo=photo) if not request.user.is_anonymous else Collection.objects.filter(id__in=[]))
    ])
    context['photos'] = qs[:48]
    context['bounds'] = areq.map_bounds
    context['photo'] = get_object_or_404(areq.get_photo_queryset(use_spatial=False).select_related("donor", "archive", "category", "place", "scanner", "photographer").prefetch_related("terms", "phototag_set"), id=photo)
    context['mapviewclass'] = 'current-view'
    if areq.is_hx_request and areq.hx_target == "image-viewer":
        template = "kronofoto/partials/map-detail_partial.html"
    else:
        template = "kronofoto/pages/map/map-detail.html"
    return TemplateResponse(request, context=context, template=template)
