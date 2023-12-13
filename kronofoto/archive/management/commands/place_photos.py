from django.core.management.base import BaseCommand
from django.contrib.gis.geos import MultiPolygon, Polygon
from ...models import Place, PlaceType
import json
from django.contrib.gis.gdal import DataSource
from django.db import connection

class Command(BaseCommand):
    help = "load states from geojson"

    def handle(self, *args, **options):
        total_placed = 0
        for place in Place.objects.all():
            print(place.name, place.parent, place.place_type)
            placed = place.collect_and_place_photos()
            total_placed += placed
            print( placed, total_placed)
