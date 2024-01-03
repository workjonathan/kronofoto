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


    def handle(self, *args, **options):
        print(datetime.now())
        Place.objects.rebuild()
        print(datetime.now())

