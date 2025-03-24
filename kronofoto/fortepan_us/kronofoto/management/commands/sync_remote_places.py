from django.core.management.base import BaseCommand
from django.contrib.gis.geos import MultiPolygon, Polygon
from ...models import Place, PlaceType
from ...models import RemoteActor, LdId
from ...models.activity_schema import ServiceActorSchema, Collection
from ...models.activity_dict import ServiceActorSchema, PlaceUpserter
import json
import requests

class Command(BaseCommand):
    help = "resync places from a remote actor"

    def add_arguments(self, parser):
        parser.add_argument('--profile', required=True)

    def handle(self, *args, profile, **options):
        actor = RemoteActor.objects.get(profile=profile)
        servicevalue = ServiceActorSchema().load(
            requests.get(
                profile,
                headers={
                    "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
            ).json()
        )
        placescollection = Collection().load(
            requests.get(
                servicevalue.places,
                headers={
                    "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
            ).json()
        )
        page = placescollection.first
        with Place.objects.disable_mptt_updates():
            while page is not None:
                for place in page.items:
                    PlaceUpserter(
                        queryset=LdId.objects.all(),
                        owner=actor,
                        object=place,
                    ).result
                page = page.next
