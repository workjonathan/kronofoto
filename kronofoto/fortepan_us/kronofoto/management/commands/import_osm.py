from django.core.management.base import BaseCommand
from django.contrib.gis.geos import MultiPolygon, Polygon, Point
from django.db import transaction
from ...models import Place, PlaceType
import shapely
import json
from django.contrib.gis.gdal import DataSource
from django.db import connection
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from django.db.transaction import atomic

@dataclass
class Children:
    parent: Place
    children: list = field(default_factory=list)

def recursive_delete(p):
    for child in Place.objects.filter(parent=p):
        print(child)
        recursive_delete(child)
    p.delete()

class Command(BaseCommand):
    help = "load things like cities, counties, and townships/county subdivisions from geojson"

    def add_arguments(self, parser):
        parser.add_argument('--geojson', required=True)
        parser.add_argument('--admin_level', required=True, type=str)
        parser.add_argument("--parent_type", required=True, type=int)
        parser.add_argument("--new_type", required=True, type=int)

    def handle(self, *args, geojson, parent_type, admin_level, new_type, **options):
       # m = Place.objects.get(name="Mongolia")
       # for p in Place.objects.filter(parent=m):
       #     print(p)
       #     recursive_delete(p)

        print(datetime.now())
        with atomic():
            Place.objects.rebuild()
        count = 0

        with open(geojson, 'r') as inf:
            data = json.load(inf)
            parent_type = PlaceType.objects.get(id=parent_type)
            new_type = PlaceType.objects.get(id=new_type)
            new_places = []
            for feature in data['features']:
                properties = feature['properties']
                if admin_level != properties['admin_level']:
                    continue
                name = properties['name']
                import re
                tags = dict(re.findall(r'"([^"]*)"=>"([^"]*)"', properties['other_tags'])) if properties['other_tags'] else {}
                if feature['geometry']['type'] == 'Polygon':
                    polygons = [shapely.Polygon(feature['geometry']['coordinates'][0], feature['geometry']['coordinates'][1:])]
                elif feature['geometry']['type'] == 'MultiPolygon':
                    polygons = [shapely.Polygon(coords[0], coords[1:]) for coords in feature['geometry']['coordinates']]
                geom = shapely.MultiPolygon(polygons)
                new_places.append((name, geom, tags))
                print(geom.centroid)
            print(new_places)
            added, no_parent, many_parents = Place.objects.osm_import(
                import_data=new_places,
                parent_place_type=parent_type,
                new_place_type=new_type,
            )
            print(f'added: {len(added)}, no_parents: {len(no_parent)}, many parents: {len(many_parents)}')
