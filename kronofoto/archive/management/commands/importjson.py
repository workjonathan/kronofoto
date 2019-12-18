from django.core.management.base import BaseCommand
from django.db import transaction
from archive.models import Donor, Collection, Photo, ContactInfo, Contributor
from datetime import datetime
import json
import sys

class Command(BaseCommand):
    help = 'import json snapshot of data from legacy db'

    def handle(self, *args, **options):
        data = json.load(sys.stdin)
        with transaction.atomic():
            users = {
                user['id']: {
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'email': user['email'],
                    'username': user['username'],
                } for user in data['users']
            }
            for donor in data['donors']:
                contactinfo = ContactInfo(
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
                contactinfo.save()
                record = Donor(
                    id=donor['id'],
                    contactinfo=contactinfo,
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
                    u = users[photo['created_by']]
                    try:
                        curator = Contributor.objects.get(id=photo['created_by'])
                    except:
                        try:
                            contactinfo = ContactInfo.objects.get(id=photo['created_by'])
                        except:
                            contactinfo = ContactInfo(
                                id=photo['created_by'],
                                last_name=u['last_name'],
                                first_name=u['first_name'],
                            )
                            contactinfo.save()
                        curator = Contributor(
                            id=photo['created_by'],
                            contactinfo=contactinfo,
                        )
                        curator.save()

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
                        created_by=curator,
                        created=datetime.strptime(photo['created'], '%Y-%m-%d %H:%M:%S %Z%z'),
                    )
                    p.save()

