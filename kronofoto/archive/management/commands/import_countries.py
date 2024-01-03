from django.core.management.base import BaseCommand
from django.contrib.gis.geos import MultiPolygon, Polygon
from ...models import Place, PlaceType
import json
from django.contrib.gis.gdal import DataSource
from django.db import connection

class Command(BaseCommand):
    help = "load countries from geojson"

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
            placetype, _ = PlaceType.objects.get_or_create(name='Country')
            with Place.objects.disable_mptt_updates():
                Place.objects.all().delete()
                for feature in data['features']:
                    properties = feature['properties']
                    name = properties['COUNTRY']
                    print(name)
                    if feature['geometry']['type'] == "Polygon":
                        polygons = [Polygon(*feature['geometry']['coordinates'])]
                    else:
                        polygons = [Polygon(*coords) for coords in feature['geometry']['coordinates']]
                    geom = MultiPolygon(*polygons)
                    Place.objects.create(place_type=placetype, name=name, geom=geom.wkt, parent=None)
                #record = Place.objects.create(place_type=placetype, name=name, parent=None, geom=geom.wkt)
                #record.refresh_from_db()
                # certain shapes will not go into sqlite. I am hoping this is sqlite specific.
                #if record.geom == None:
                #    #record.geom = geom.wkt
                #    #record.save()
                #    geom = geom.simplify(1, preserve_topology=True)
                #    if geom.geom_type == "Polygon":
                #        geom = MultiPolygon(geom)
                #    record.geom = geom.wkt
                #    record.save()
