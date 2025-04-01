from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from typing import Optional, Any
from .base import ArchiveRequest, PhotoQuerySet, ArchiveReference
from fortepan_us.kronofoto.forms import BoundsSearchForm, Bounds
from django.contrib.gis.geos import Polygon
from functools import cached_property
from fortepan_us.kronofoto.models import Photo
from django.db.models import QuerySet, Q
from dataclasses import dataclass


class MapRequest(ArchiveRequest):
    @cached_property
    def form(self) -> BoundsSearchForm:
        return BoundsSearchForm(self.request.GET)

    @property
    def base_template(self) -> str:
        if self.hx_target == "fi-map-result":
            return "kronofoto/partials/map_partial.html"
        elif self.hx_target == "fi-map-figure":
            return "kronofoto/partials/map-detail_partial.html"
        else:
            return super().base_template

    @property
    def map_bounds(self) -> Bounds:
        return self.form.cleaned_data['map_bounds']

    def get_photo_queryset(self) -> PhotoQuerySet:
        qs = super().get_photo_queryset().order_by()
        if (self.form.is_valid() and
            self.form.cleaned_data['search_bounds'] is not None
        ):
            bounds = Polygon.from_bbox(
                self.form.cleaned_data['search_bounds'].as_tuple()
            )
            qs = qs.filter(Q(place__geom__intersects=bounds) | Q(location_point__intersects=bounds))
        return qs


def map_list(request: HttpRequest, *, short_name: Optional[str]=None, domain: Optional[str]=None, category: Optional[str]=None) -> HttpResponse:
    archive_ref = None
    if short_name:
        archive_ref = ArchiveReference(short_name, domain)
    areq = MapRequest(request=request, archive_ref=archive_ref, category=category)
    context = areq.common_context
    qs = areq.get_photo_queryset()[:48]
    context['form'] = areq.form
    context['photos'] = qs
    context['bounds'] = areq.map_bounds
    return TemplateResponse(request, context=context, template="kronofoto/pages/map/map.html")

def map_detail(request: HttpRequest, *, photo: int, short_name: Optional[str]=None, domain: Optional[str]=None, category: Optional[str]=None) -> HttpResponse:
    archive_ref = None
    if short_name:
        archive_ref = ArchiveReference(short_name, domain)
    areq = MapRequest(request=request, archive_ref=archive_ref, category=category)
    context = areq.common_context
    qs = areq.get_photo_queryset()

    context['form'] = areq.form
    context['photos'] = qs[:48]
    context['bounds'] = areq.map_bounds
    context['photo'] = get_object_or_404(qs, id=photo)
    return TemplateResponse(request, context=context, template="kronofoto/pages/map/map-detail.html")
