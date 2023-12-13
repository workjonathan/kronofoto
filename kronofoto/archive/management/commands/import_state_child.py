from django.core.management.base import BaseCommand
from django.contrib.gis.geos import MultiPolygon, Polygon
from ...models import Place, PlaceType
import json
from django.contrib.gis.gdal import DataSource
from django.db import connection

class Command(BaseCommand):
    help = "load things like cities, counties, and townships/county subdivisions from geojson"

    def add_arguments(self, parser):
        parser.add_argument('--geojson', required=True)
        parser.add_argument('--placetype', required=True)

    def handle(self, *args, geojson, placetype, **options):
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
            placetype, _ = PlaceType.objects.get_or_create(name=placetype)
            Place.objects.filter(place_type=placetype).delete()
            records = []
            for feature in data['features']:
                properties = feature['properties']
                parent = Place.objects.get(name=properties['state_NAME'], place_type__name="US State")
                name = properties['NAME']
                if feature['geometry']['type'] == "Polygon":
                    polygons = [Polygon(*feature['geometry']['coordinates'])]
                else:
                    polygons = [Polygon(*coords) for coords in feature['geometry']['coordinates']]
                geom = MultiPolygon(*polygons)
                record = Place(place_type=placetype, name=name, parent=parent, geom=geom.wkt)
                records.append(record)
            Place.objects.bulk_create(records)
