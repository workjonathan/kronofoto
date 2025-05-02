from __future__ import annotations
import mapbox_vector_tile  # type: ignore
from functools import cached_property
from typing import Sequence, Union, List, Callable, Dict, Any, Optional, Tuple, TypedDict, Iterable, TypeVar, Generic
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from fortepan_us.kronofoto import models
from django.contrib.gis.db.models.functions import Transform
import mercantile # type: ignore
from dataclasses import dataclass
import icontract
from django.views.decorators.cache import cache_page

T = TypeVar("T")

class FeatureProperties(TypedDict):
    id: int

class Feature(TypedDict):
    properties: FeatureProperties
    geometry: str

class Layer(TypedDict):
    name: str
    features: list[Feature]

class Bounds:
    east: float
    west: float
    north: float
    south: float

@dataclass
class TileLayerBase:
    x: int
    y: int
    zoom: int

    @cached_property
    def bounds(self) -> Bounds:
        return mercantile.bounds(self.x, self.y, self.zoom)

    @property
    def bbox(self) -> Polygon:
        bounds = self.bounds
        poly = Polygon.from_bbox((bounds.west, bounds.south, bounds.east, bounds.north))
        poly.srid = 4326
        return poly

    @property
    def layers(self) -> list[Layer]:
        bounds = self.bounds
        bbox = Polygon.from_bbox((bounds.west, bounds.south, bounds.east, bounds.north))
        bbox.srid = 4326
        bbox.transform(3857)
        (x0, y0, x_max, y_max) = bbox.extent
        x_span = x_max - x0
        y_span = y_max - y0
        return self.get_layers(x_span=x_span, y_span=y_span, x0=x0, y0=y0)

    def get_layers(self, *, x_span: float, y_span: float, x0: float, y0: float) -> list[Layer]:
        raise NotImplementedError


    @property
    def response(self) -> HttpResponse:
        return HttpResponse(
            mapbox_vector_tile.encode(self.layers),
            headers={
                "Content-Type": "application/vnd.mapbox-vector-tile",
            },
        )

@dataclass
class PlaceMapTile(TileLayerBase):
    @cached_property
    def places(self) -> Iterable[models.Place]:

        return models.Place.objects.filter(
            geom__isnull=False,
            geom__intersects=self.bbox,
            place_type__name="US State",
        ).annotate(geom2=Transform("geom", 3857))

    def get_layers(self, *, x_span: float, y_span: float, x0: float, y0: float) -> list[Layer]:
        features_ : list[Feature] = []
        for p in self.places:
            polys = []
            for poly in p.geom2.coords:
                rings = [
                    [
                        (
                            round((c_x - x0) * 4096 / x_span),
                            round((c_y - y0) * 4096 / y_span),
                        ) for (c_x, c_y) in ring
                    ]
                    for ring in poly
                ]
                cleaned = Polygon(*rings, srid=4326).buffer(0)
                if cleaned.geom_type == "MultiPolygon" and isinstance(cleaned, MultiPolygon):
                    for shp in cleaned:
                        polys.append(shp)
                else:
                    assert cleaned.geom_type == 'Polygon', p
                    polys.append(cleaned)
            mp = MultiPolygon(polys).buffer(0)
            features_.append(
                {
                    "geometry": mp.wkt,
                    "properties": {"id": p.id},
                }
            )

        return [
            {
                "name": "mainstreets",
                "features": features_,
            },
        ]

@icontract.invariant(lambda self: 0 <= self.zoom < 35)
@dataclass
class PhotoSphereTile(TileLayerBase):
    mainstreet: int
    tour: Optional[int]


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
        ).annotate(geom=Transform("location", 3857))

    def get_layers(self, *, x_span: float, y_span: float, x0: float, y0: float) -> list[Layer]:
        features : List[Feature] = [
            {
                "geometry": Point(
                    int((obj.geom.x - x0) * 4096 / x_span),
                    int((obj.geom.y - y0) * 4096 / y_span),
                ).wkt,
                "properties": {"id": obj.id},
            }
            for obj in self.photospheres if obj.location and hasattr(obj, 'geom')
        ]
        return [
            {
                "name": "mainstreets",
                "features": features,
            },
        ]




@cache_page(60*10)
def photo_tile(request: HttpRequest, /, *, archive: Optional[str]=None, domain: Optional[str]=None, category: Optional[str]=None, zoom: int, x: int, y: int) -> HttpResponse:
    if zoom < 0 or zoom >= 35:
        return HttpResponse("invalid zoom level", status=400)
    return PlaceMapTile(
        zoom=zoom,
        x=x,
        y=y,
    ).response


def photosphere_vector_tile(request: HttpRequest, /, *, tour: Optional[int]=None, mainstreet: int, zoom: int, x: int, y: int) -> HttpResponse:
    if zoom < 0 or zoom >= 35:
        return HttpResponse("invalid zoom level", status=400)
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

