from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from typing import Optional, Any
from .base import ArchiveRequest
from ..forms import BoundsSearchForm, Bounds
from django.contrib.gis.geos import Polygon
from functools import cached_property
from ..models import Photo
from django.db.models import QuerySet, Q
from dataclasses import dataclass


class MapRequest(ArchiveRequest):
    @cached_property
    def form(self) -> BoundsSearchForm:
        return BoundsSearchForm(self.request.GET)

    @property
    def base_template(self) -> str:
        print(f'{self.hx_target=}')
        if self.hx_target == "photo-grid":
            return "archive/map_partial.html"
        else:
            return super().base_template

    @property
    def map_bounds(self) -> Bounds:
        return self.form.cleaned_data['map_bounds']

    def get_photo_queryset(self) -> QuerySet[Photo]:
        qs = super().get_photo_queryset().order_by()
        if (self.form.is_valid() and
            self.form.cleaned_data['search_bounds'] is not None
        ):
            bounds = Polygon.from_bbox(
                self.form.cleaned_data['search_bounds'].as_tuple()
            )
            qs = qs.filter(Q(place__geom__intersects=bounds) | Q(location_point__intersects=bounds))
        return qs


def map_list(request: HttpRequest, *, short_name: Optional[str]=None, category: Optional[str]=None) -> HttpResponse:
    areq = MapRequest(request=request, short_name=short_name, category=category)
    context = areq.common_context
    qs = areq.get_photo_queryset()[:48]
    context['form'] = areq.form
    context['photos'] = qs
    context['bounds'] = areq.map_bounds
    return TemplateResponse(request, context=context, template="archive/map.html")
