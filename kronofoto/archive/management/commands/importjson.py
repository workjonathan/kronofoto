from django.core.management.base import BaseCommand
from archive.models import Donor, Collection, Photo
import json
import sys

class Command(BaseCommand):
    help = 'import json snapshot of data from legacy db'

    def handle(self, *args, **options):
        data = json.load(sys.stdin)
        for donor in data['donors']:
            record = Donor(
                id=donor['id'],
                first_name=donor['first_name'],
                last_name=donor['last_name'],
                street1=donor['street1'],
                street2=donor['street2'],
                city=donor['city'],
                state=donor['state'],
                zip=donor['zip'],
                country=donor['country'],
                home_phone=donor['home_phone'],
            )
            record.save()
        for collection in data['collections']:
            record = Collection(
                name=collection['name'],
                displayed_donors=collection['displayed_donors'],
                description=collection['description'],
                year_min=collection['year_min'],
                year_max=collection['year_max'],
                total_photos=collection['total_photos'],
                is_published=collection['is_published'],
            )
            record.save()
            for donor in collection['donors']:
                record.donors.add(Donor.objects.get(id=donor))
                record.save()
            for photo in collection['photos']:
                p = Photo(
                    accession_number=photo['accession_number'],
                    city=photo['city'],
                    county=photo['county'],
                    state=photo['state'],
                    country=photo['country'],
                    year=photo['year'],
                    caption=photo['caption'],
                    is_featured=photo['is_featured'],
                    is_published=photo['is_published'],
                    collection=record,
                )
                p.save()

