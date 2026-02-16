from __future__ import annotations
import mapbox_vector_tile  # type: ignore
from functools import cached_property
from typing import Sequence, Union, List, Callable, Dict, Any, Optional, Tuple, TypedDict, Iterable, TypeVar, Generic
from django.http import HttpResponse, HttpRequest, JsonResponse, QueryDict
from django.conf import settings
from typing_extensions import Annotated
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from fortepan_us.kronofoto import models
from django.contrib.gis.db.models.functions import Transform
from django.views.decorators.vary import vary_on_headers
import mercantile # type: ignore
from dataclasses import dataclass
import icontract
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from fortepan_us.kronofoto.reverse import reverse
from .base import ArchiveRequest, ArchiveReference

T = TypeVar("T")

class FeatureProperties(TypedDict, total=False):
    id: int
    count: int
    href: str
    popup_href: str
    thumb: str

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
    """Base for mapbox vector tile rendering"""
    x: int
    y: int
    zoom: int

    @cached_property
    def bounds(self) -> Bounds:
        """Returns bounds for these map tile coordinates.

        Returns:
            Bounds: The extent of this tile in EPSG:4326.
        """
        return mercantile.bounds(self.x, self.y, self.zoom)

    def bbox(self, srid: int=4326) -> Polygon:
        """The bounds of this tile as a Polygon.

        Returns:
            Polygon: A polygon for the tile extent in EPSG:4326.
        """
        bounds = self.bounds
        poly = Polygon.from_bbox((bounds.west, bounds.south, bounds.east, bounds.north))
        poly.srid = 4326
        if srid != 4326:
            poly.transform(srid)
        return poly

    @property
    def layers(self) -> list[Layer]:
        """Gets layers associated with this tile.

        The tile bounds must be converted to EPSG:3857, along with the contents
        of the tile. This delegates to the get_layers function, which must be
        implemented by subclasses.

        Returns:
            list[Layer]: Layers consist of a name and features. Features consist of geometry and properties.
        """
        bounds = self.bounds
        bbox = Polygon.from_bbox((bounds.west, bounds.south, bounds.east, bounds.north))
        bbox.srid = 4326
        bbox.transform(3857)
        (x0, y0, x_max, y_max) = bbox.extent
        x_span = x_max - x0
        y_span = y_max - y0
        return self.get_layers(x_span=x_span, y_span=y_span, x0=x0, y0=y0)

    def get_layers(self, *, x_span: float, y_span: float, x0: float, y0: float) -> list[Layer]:
        """Gets the layers for this mapbox vector tile. Implementors must
        implement this to define the data source and convert the geometry into
        the tile space.

        Every mapbox vector tile has a coordinate system that ranges in integer
        values from (0, 0) to (4096, 4096), allowing much more efficient use of
        bits. Implementors must take care to convert geometry into this
        coordinate system according to the boundaries defined by the arguments.

        Args:
            x_span (float): The width of this tile in EPSG:3857.
            y_span (float): The height of this tile in EPSG:3857.
            x0 (float): The x value corresponding to this tile's (0, 0) in EPSG:3857.
            y0 (float): The y value corresponding to this tile's (0, 0) in EPSG:3857.

        Returns:
            list[Layer]: A layer consists of a name and geometry represented in only integer values ranging from 0 to 4096, as well as properties.

        Raises:
            NotImplementedError: If not implemented by base classes.
        """
        raise NotImplementedError


    @property
    def response(self) -> HttpResponse:
        """Get an HttpResponse containing a mapbox vector tile for these x, y, and z.

        Returns:
            HttpResponse: A HttpResponse with a body consisting of this mapbox vector tile and with the correct mime type.
        """
        return HttpResponse(
            mapbox_vector_tile.encode(self.layers),
            headers={
                "Content-Type": "application/vnd.mapbox-vector-tile",
            },
        )

@dataclass
class PlaceMapTile(TileLayerBase):
    "PlaceMapTiles appear on the map view. Places are visible as polygons."

    @cached_property
    def places(self) -> Iterable[models.Place]:
        """Returns the Places that should be included in this tile.

        Returns:
            Iterable[models.Place]: Places that should be visible in this tile, with a geom2 field which is the geometry reprojected in EPSG:3857.
        """
        return models.Place.objects.zoom(level=self.zoom).filter(
            geom__isnull=False,
            geom__intersects=self.bbox(),
        ).annotate(geom2=Transform("geom", 3857))

    def get_layers(self, *, x_span: float, y_span: float, x0: float, y0: float) -> list[Layer]:
        def _() -> list[Feature]:
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
            return features_

        features_ = cache.get_or_set(f"kronofoto:PlaceMapTile(x={self.x}, y={self.y}, zoom={self.zoom})", _, 60*10)
        if features_ is None:
            return []
        for feature in features_:
            place = models.Place.objects.get(id=feature['properties']['id'])
            feature['properties']['id'] = models.Photo.objects.filter(places__id=place.id).count()
        return [
            {
                "name": "places",
                "features": features_,
            },
        ]

@icontract.invariant(lambda self: 0 <= self.zoom < 35)
@dataclass
class PhotoSphereTile(TileLayerBase):
    """Mapbox Vector Tiles for photospheres. In addition to the tile address,
    photospheres are also filtered by mainstreet id and optionally by tour id.
    """
    mainstreet: int
    tour: Optional[int]


    @property
    def photospheres(self) -> Iterable[models.PhotoSphere]:
        """PhotoSphere visible on this tile.

        PhotoSpheres are visible on this tile if they are in the right location
        and belong to the correct mainstreet. If tour is set, they must also
        belong to the same tour.

        Returns:
            Iterable[models.PhotoSphere]: PhotoSpheres within this tile, with geom in EPSG:3857.
        """
        kwargs = {}
        if self.tour is not None:
            kwargs['tour__id'] = self.tour

        return models.PhotoSphere.objects.filter(
            location__isnull=False,
            location__intersects=self.bbox(),
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

class Geom2Dict(TypedDict):
    geom2: Point

AnnotatedPhoto = Annotated[models.Photo, Geom2Dict]

@dataclass
class TileBounds:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def __post_init__(self) -> None:
        self.subdivisions = getattr(settings, "SUBDIVISIONS", 4)
        self.cell_width = (self.xmax - self.xmin)/self.subdivisions
        self.cell_height = (self.ymax - self.ymin)/self.subdivisions

    def subgrid(self) -> list[list[list[T]]]:
        return [[[] for y in range(self.subdivisions)] for y in range(self.subdivisions)]

    def get_cell(self, x: float, y: float) -> tuple[int, int]:
        xcell = int((x - self.xmin)//self.cell_width)
        ycell = int((y - self.ymin)//self.cell_height)
        return xcell, ycell

    def get_center(self, x: int, y: int) -> tuple[float, float]:
        return (
            round(self.xmin + (x + 0.5) * self.cell_width),
            round(self.ymin + (y + 0.5) * self.cell_height),
        )

    def get_polygon(self, x: int, y: int) -> Polygon:
        poly = Polygon.from_bbox((
            round(((self.xmin + x * self.cell_width))),
            round(((self.ymin + y * self.cell_height))),
            round(((self.xmin + (x+1) * self.cell_width))),
            round(((self.ymin + (y+1) * self.cell_height))),
        ))
        poly.srid = 3857
        return poly

@dataclass
class PhotoMapTile(TileLayerBase):
    "PhotoMapTiles appear on the map view. Photos are visible as markers."
    queryset: models.PhotoQuerySet
    url_kwargs: Dict[str, Any]
    get_params: QueryDict

    @cached_property
    def photos(self) -> Iterable[AnnotatedPhoto]:
        """Returns the Photo that should be included in this tile.

        Returns:
            Iterable[models.AnnotatedPhoto]: Photo that should be visible in this tile, with a geom2 field which is the geometry reprojected in EPSG:3857.
        """
        return self.queryset.filter(
            location_point__intersects=self.bbox(),
        ).annotate(geom2=Transform("location_point", 3857))

    def get_layers(self, *, x_span: float, y_span: float, x0: float, y0: float) -> list[Layer]:
        features_ : list[Feature] = []
        photos = self.photos
        bbox = self.bbox(3857)
        exmin, eymin, exmax, eymax = bbox.extent
        tb = TileBounds(*bbox.extent)

        SUBDIVISIONS = getattr(settings, "SUBDIVISIONS", 4)
        CLUMP_CUTOFF = 1
        cell_width = (exmax - exmin)/SUBDIVISIONS
        cell_height = (eymax - eymin)/SUBDIVISIONS
        subgrid: list[list[list[models.Photo]]] = tb.subgrid()

        if self.get_params:
            params = "?" + self.get_params.urlencode()
        else:
            params = ""

        for p in self.photos:
            c_x, c_y = p.geom2.coords # type: ignore
            xcell, ycell = tb.get_cell(c_x, c_y)
            # Getting exceptions on this append due to outside bounds.
            # I think that it is possible for a location to intersect the boundary on the large X or Y coordinate side.
            # On the low end, this is just in the 0 index of the subgrid. On the high end, it is index SUBDIVISIONS:
            # With width=2 and subdivisions=2, 2/(width/subdivisions) == 2 / (2/1) == subdivisions.
            # These photos should be included on the tiles on the other side of the boundary, because they are
            # apparently right on the line.

            if xcell < SUBDIVISIONS and ycell < SUBDIVISIONS:
                subgrid[xcell][ycell].append(p)

        for x in range(SUBDIVISIONS):
            for y in range(SUBDIVISIONS):
                contents = subgrid[x][y]

                #if len(contents) > CLUMP_CUTOFF:
                #    poly = Polygon(
                #        [
                #            (round((x - x0) * 4096 / x_span), round((y - y0) * 4096 / y_span))
                #            for (x, y) in tb.get_polygon(x, y).coords[0]
                #        ]
                #    )
                #    features_.append(
                #        {
                #            "geometry": poly.wkt,
                #            "properties": {
                #                "id": p.id,
                #                "count": len(contents),
                #                "popup_href": reverse("kronofoto:map-subtile-detail", kwargs={**self.url_kwargs, **{"x": self.x, "y": self.y, "zoom": self.zoom, "subx": x, "suby": y}}) + params
                #            },
                #        }
                #    )
                for p in contents:
                    c_x, c_y = p.geom2.coords # type: ignore
                    xcell, ycell = tb.get_cell(c_x, c_y)
                    px, py = tb.get_center(xcell, ycell)
                    point = Point(
                        round((px - x0) * 4096 / x_span),
                        round((py - y0) * 4096 / y_span),
                    )
                    features_.append(
                        {
                            "geometry": point.wkt,
                            "properties": {
                                "id": p.id,
                                "href": reverse("kronofoto:map-detail", kwargs={"photo": p.id, **self.url_kwargs}) + params,
                                "thumb": p.image_url(width=256, height=256),
                                "count": len(contents),
                                "popup_href": reverse("kronofoto:map-subtile-detail", kwargs={**self.url_kwargs, **{"x": self.x, "y": self.y, "zoom": self.zoom, "subx": x, "suby": y}}) + params if len(contents) > CLUMP_CUTOFF else "",
                            },
                        }
                    )
                    break

        if features_ is None:
            return []
        return [
            {
                "name": "photos",
                "features": features_,
            },
        ]

@cache_page(60*10)
@vary_on_headers("")
def photo_tile(request: HttpRequest, /, *, archive: Optional[str]=None, domain: Optional[str]=None, category: Optional[str]=None, zoom: int, x: int, y: int) -> HttpResponse:
    """View function for Place map tiles.

    Args:
        request (HttpRequest): request is used to filter Photos for counts on places.
        archive (str, optional): None by default. Used to filter Photos for counts on places by Archive.
        domain (str, optional): None by default. Used in tandem with ardchive to identify remote archives.
        category (str, optional): None by default. Used to filter Photos for counts on places by Category.
        zoom (int): tile zoom level
        x (int): tile x index
        y (int): tile y index
    Returns:
        HttpResponse: The response contains the mapbox vector tile, or will return a 400 response if the zoom level is negative or too high.
    """
    archive_ref = None
    if archive:
        archive_ref = ArchiveReference(archive, domain)
    areq = ArchiveRequest(request=request, archive_ref=archive_ref, category=category)
    if zoom < 0 or zoom >= 35:
        return HttpResponse("invalid zoom level", status=400)
    return PhotoMapTile(
        queryset=areq.get_photo_queryset(),
        url_kwargs=areq.url_kwargs,
        get_params=areq.get_params,
        zoom=zoom,
        x=x,
        y=y,
    ).response


def photosphere_vector_tile(request: HttpRequest, /, *, tour: Optional[int]=None, mainstreet: int, zoom: int, x: int, y: int) -> HttpResponse:
    """View function for Photosphere map tiles.

    Args:
        request (HttpRequest): request is used to filter Photos for counts on places.
        tour (int, optional): None by default. If given, PhotoSpheres must have this tour id to be included in the tile.
        mainstreet (int): PhotoSpheres must have this mainstreet id to be included in this tile.
        zoom (int): tile zoom level
        x (int): tile x index
        y (int): tile y index
    Returns:
        HttpResponse: The response contains the mapbox vector tile, or will return a 400 response if the zoom level is negative or too high.
    """
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

