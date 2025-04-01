from django.core.management.base import BaseCommand
from django.contrib.gis.geos import MultiPolygon, Polygon
from ...models import Place, PlaceType
from ...models import Archive, LdId
from ...models.activity_schema import ArchiveSchema, Collection, CollectionPage
from ...models.activity_dicts import ArchiveValue, DonorValue
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
                actor.actor.profile,
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
            if page.next:
                page = CollectionPage().load(
                    requests.get(
                        page.next,
                        headers={
                            "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                        },
                    ).json()
                )
            else:
                page = None
