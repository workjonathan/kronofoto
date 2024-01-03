from django.core.management.base import BaseCommand
from django.contrib.gis.geos import MultiPolygon, Polygon
from ...models import Place, PlaceType
import json
from django.contrib.gis.gdal import DataSource
from django.db import connection

class Command(BaseCommand):
    help = "load states from geojson"

    def add_arguments(self, parser):
        parser.add_argument('--geojson', required=True)

    def handle(self, *args, geojson, **options):
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
            placetype, _ = PlaceType.objects.get_or_create(name='US State')
            with Place.objects.disable_mptt_updates():
                Place.objects.filter(place_type=placetype).delete()
                usa = Place.objects.get(name="United States")
                for feature in data['features']:
                    properties = feature['properties']
                    name = properties['STUSPS']
                    if feature['geometry']['type'] == "Polygon":
                        polygons = [Polygon(*feature['geometry']['coordinates'])]
                    else:
                        polygons = [Polygon(*coords) for coords in feature['geometry']['coordinates']]
                    geom = MultiPolygon(*polygons)
                    record = Place.objects.create(parent=usa, place_type=placetype, name=name, geom=geom.wkt)
