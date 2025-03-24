from django.core.management.base import BaseCommand
from django.contrib.gis.geos import MultiPolygon, Polygon
from ...models import Place, PlaceType
from ...models import Archive, LdId
from ...models.activity_schema import ArchiveSchema, Collection
from ...models.activity_dict import ArchiveValue, DonorValue
import json
import requests

class Command(BaseCommand):
    help = "resync places from a remote actor"

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True)
        parser.add_argument('--server_domain', required=True)

    def handle(self, *args, slug, server_domain, **options):
        actor = Archive.objects.get(slug=slug, server_domain=server_domain)
        servicevalue = ArchiveSchema().load(
            requests.get(
                profile,
                headers={
                    "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
            ).json()
        )
        donorscollection = Collection().load(
            requests.get(
                servicevalue.contributors,
                headers={
                    "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
            ).json()
        )
        page = donorscollection.first
        while page is not None:
            for donor in page.items:
                if isinstance(donor, DonorValue):
                    donor.upsert(actor)
            page = page.next
