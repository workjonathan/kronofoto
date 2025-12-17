from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from typing import Optional, Any, overload, Dict
from .base import ArchiveRequest, PhotoQuerySet, ArchiveReference
from fortepan_us.kronofoto.forms import BoundsSearchForm, Bounds
from django.contrib.gis.geos import Polygon
from functools import cached_property
from fortepan_us.kronofoto.models import Photo, PhotoSphere, PhotoSpherePair
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

    def get_photo_queryset(self, include_geocoded: Optional[bool]=None) -> PhotoQuerySet:
        qs = super().get_photo_queryset().order_by()
        if (self.form.is_valid() and
            self.form.cleaned_data['search_bounds'] is not None
        ):
            bounds = Polygon.from_bbox(
                self.form.cleaned_data['search_bounds'].as_tuple()
            )
            # use db functions area and intersection to calculate percentage of the intersection and include places that
            # have more than some threshold intersection with our bounds.
            # also exclude places with no intersection to potentially speed it up.
            q = Q(place__geom__within=bounds)
            if include_geocoded is not None:
                q &= Q(location_point__isnull=not include_geocoded)
            qs.filter(q)

        return qs


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
    qs = areq.get_photo_queryset()[:48]
    context["tile_url"] = tile_url
    context['form'] = areq.form
    context['photos'] = qs
    context['bounds'] = areq.map_bounds
    context['mapviewclass'] = 'current-view'
    return TemplateResponse(request, context=context, template="kronofoto/pages/map/map.html")

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
    context['tile_url'] = tile_url
    qs = areq.get_photo_queryset(include_geocoded=False)
    context['form'] = areq.form
    context['photos'] = qs[:48]
    context['bounds'] = areq.map_bounds
    context['photo'] = get_object_or_404(areq.get_photo_queryset(), id=photo)
    context['mapviewclass'] = 'current-view'
    return TemplateResponse(request, context=context, template="kronofoto/pages/map/map-detail.html")
