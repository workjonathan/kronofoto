from __future__ import annotations
import mapbox_vector_tile  # type: ignore
from functools import cached_property
from typing import Sequence, Union, List, Callable, Dict, Any, Optional, Tuple, TypedDict, Iterable
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.contrib.gis.geos import Point, Polygon
from fortepan_us.kronofoto import models
import mercantile # type: ignore
from dataclasses import dataclass
import icontract

class PhotoSphereProperties(TypedDict):
    id: int

class PhotoSphereFeature(TypedDict):
    properties: PhotoSphereProperties
    geometry: str

class Layer(TypedDict):
    name: str
    features: list[PhotoSphereFeature]

class Bounds:
    east: float
    west: float
    north: float
    south: float

@icontract.invariant(lambda self: 0 < self.zoom < 35)
@dataclass
class PhotoSphereTile:
    x: int
    y: int
    zoom: int
    mainstreet: int
    tour: Optional[int]

    @cached_property
    def bounds(self) -> Bounds:
        return mercantile.bounds(self.x, self.y, self.zoom)

    @property
    def bbox(self) -> Polygon:
        bounds = self.bounds
        return Polygon.from_bbox((bounds.west, bounds.south, bounds.east, bounds.north))

    @property
    def photospheres(self) -> Iterable[models.PhotoSphere]:
        kwargs = {}
        if self.tour is not None:
            kwargs['tour__id'] = self.tour

        return models.PhotoSphere.objects.filter(
            location__isnull=False,
            location__intersects=self.bbox,
            mainstreetset__id=self.mainstreet,
            **kwargs
        )

    @property
    def layers(self) -> list[Layer]:
        bounds = self.bounds
        bbox = Polygon.from_bbox((bounds.west, bounds.south, bounds.east, bounds.north))
        x_span = bounds.east - bounds.west
        y_span = bounds.north - bounds.south
        x0 = bounds.west
        y0 = bounds.south
        features : List[PhotoSphereFeature] = [
            {
                "geometry": Point(
                    int((obj.location.x - x0) * 4096 / x_span),
                    int((obj.location.y - y0) * 4096 / y_span),
                ).wkt,
                "properties": {"id": obj.id},
            }
            for obj in self.photospheres if obj.location
        ]
        return [
            {
                "name": "mainstreets",
                "features": features,
            },
        ]

    @property
    def response(self) -> HttpResponse:
        return HttpResponse(
            mapbox_vector_tile.encode(self.layers),
            headers={
                "Content-Type": "application/vnd.mapbox-vector-tile",
            },
        )



def photosphere_vector_tile(request: HttpRequest, /, *, tour: Optional[int]=None, mainstreet: int, zoom: int, x: int, y: int) -> HttpResponse:
    return PhotoSphereTile(
        tour=tour,
        mainstreet=mainstreet,
        zoom=zoom,
        x=x,
        y=y,
    ).response

from django.urls import path, include, register_converter, URLPattern, URLResolver

app_name = "vector-tiles"
urlpatterns : List[Union[URLPattern, URLResolver]] = [
    path("tiles/", include([
        path("mainstreets/<int:tour>/<int:mainstreet>/<int:zoom>/<int:x>/<int:y>.mvt", photosphere_vector_tile, name="photosphere"),
        path("mainstreets/<int:mainstreet>/<int:zoom>/<int:x>/<int:y>.mvt", photosphere_vector_tile, name="photosphere"),
    ])),
]

