from django.core.management.base import BaseCommand
from django.conf import settings
from archive.models import CSVRecord, Photo, Collection, Contributor, Donor, ContactInfo
import sys
import os
import shutil

class Command(BaseCommand):
    help = 'look for the Jpegs to associate with CSVRecords'

    def add_arguments(self, parser):
        parser.add_argument('photo_archive', nargs=1)

    def handle(self, *args, **options):
        files = {os.path.splitext(f)[0]: os.path.join(d, f) for d, _, fs in os.walk(options['photo_archive'][0]) for f in fs if not f.startswith('.')}
        for record in CSVRecord.objects.filter(photo__isnull=True):
            if record.filename in files:
                fname = ''
                filename = files[record.filename]
                contactInfo, _ = ContactInfo.objects.get_or_create(first_name=record.donorFirstName, last_name=record.donorLastName)
                donor, _ = Donor.objects.get_or_create(contactinfo=contactInfo)
                photo = Photo(
                    donor=donor,
                    city=record.city,
                    county=record.county,
                    state=record.state,
                    country=record.country,
                    year=record.year,
                    caption=record.comments,
                    is_published=True,
                )
                fname = 'original/{}.jpg'.format(photo.uuid)
                shutil.copyfile(filename, os.path.join(settings.MEDIA_ROOT, fname))
                photo.original.name = fname
                photo.save()
                photo.created = record.added_to_archive
                photo.save()
                record.photo = photo
                record.save()
