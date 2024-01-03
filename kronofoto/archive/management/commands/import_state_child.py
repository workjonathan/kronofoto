from django.core.management.base import BaseCommand
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import transaction
from ...models import Place, PlaceType
import json
from django.contrib.gis.gdal import DataSource
from django.db import connection
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Children:
    parent: Place
    children: list = field(default_factory=list)


class Command(BaseCommand):
    help = "load things like cities, counties, and townships/county subdivisions from geojson"

    def add_arguments(self, parser):
        parser.add_argument('--geojson', required=True)
        parser.add_argument('--placetype', required=True)

    def handle(self, *args, geojson, placetype, **options):
        print(datetime.now())
        count = 0
        #ds = DataSource(geojson)
        #placetype, _ = PlaceType.objects.get_or_create(name='Country')
        #Place.objects.all().delete()
        #for lyr in ds:
        #    for feature in lyr:
        #        name = feature.get("name")
        #        geom = feature.geom
        #        if feature.geom.geom_type == "Polygon":
        #            geom = MultiPolygon(geom)
        #        record = Place.objects.create(place_type=placetype, name=name, parent=None, geom=geom.wkt)

        with open(geojson, 'r') as inf:
            data = json.load(inf)
            with Place.objects.disable_mptt_updates():
                placetype, _ = PlaceType.objects.get_or_create(name=placetype)
                print('deleting old')
                for place in Place.objects.filter(place_type=placetype):
                    place.delete()
                structure = defaultdict(list)
                for feature in data['features']:
                    properties = feature['properties']
                    parent = Place.objects.get(name=properties['state_STUSPS'], place_type__name="US State")
                    name = properties['NAME']
                    if feature['geometry']['type'] == "Polygon":
                        polygons = [Polygon(*feature['geometry']['coordinates'])]
                    else:
                        polygons = [Polygon(*coords) for coords in feature['geometry']['coordinates']]
                    geom = MultiPolygon(*polygons)
                    Place.objects.create(name=name, geom=geom.wkt, place_type=placetype, parent=parent)
                    count += 1
                    if count % 100 == 0:
                        print(count, datetime.now())
