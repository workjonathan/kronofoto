import mapbox_vector_tile  # type: ignore
from typing import Sequence, Union, List, Callable, Dict, Any, Optional, Tuple
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.contrib.gis.geos import Point, Polygon
from fortepan_us.kronofoto import models
import mercantile # type: ignore

def photosphere_vector_tile(request: HttpRequest, mainstreet: int, zoom: int, x: int, y: int) -> HttpResponse:
    bounds = mercantile.bounds(x, y, zoom)
    bbox = Polygon.from_bbox((bounds.west, bounds.south, bounds.east, bounds.north))
    x_span = bounds.east - bounds.west
    y_span = bounds.north - bounds.south
    x0 = bounds.west
    y0 = bounds.south
    features = [
        {
            "geometry": Point(
                int((obj.location.x - x0) * 4096 / x_span),
                int((obj.location.y - y0) * 4096 / y_span),
            ).wkt,
            "properties": {"id": obj.id},
        }
        for obj in models.PhotoSphere.objects.filter(
            location__isnull=False,
            location__intersects=bbox,
            mainstreetset__id=mainstreet
        ) if obj.location
    ]
    layers = [
        {
            "name": "mainstreets",
            "features": features,
        },
    ]
    return HttpResponse(
        mapbox_vector_tile.encode(layers),
        headers={
            "Content-Type": "application/vnd.mapbox-vector-tile",
        },
    )

from django.urls import path, include, register_converter, URLPattern, URLResolver

app_name = "vector-tiles"
urlpatterns : List[Union[URLPattern, URLResolver]] = [
    path("tiles/", include([
        path("mainstreets/<int:mainstreet>/<int:zoom>/<int:x>/<int:y>.mvt", photosphere_vector_tile, name="photosphere"),
    ])),
]

