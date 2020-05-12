from django.core.management.base import BaseCommand
from django.conf import settings
from archive.models import CSVRecord, Photo, Collection, Donor
import sys
import os
import shutil


def splitname(name):
    name = name.strip()
    if not name:
        return name
    names = name.split()
    if not len(names):
        return name
    return names[-1], ' '.join(names[:-1])


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
                photographer = record.photographer.strip()
                scanner = splitname(record.scanner)
                scanner, _ = Donor.objects.get_or_create(first_name=scanner[0], last_name=scanner[1])
                donor, _ = Donor.objects.get_or_create(first_name=record.donorFirstName, last_name=record.donorLastName)
                photo = Photo(
                    donor=donor,
                    city=record.city,
                    county=record.county,
                    state=record.state,
                    country=record.country,
                    year=record.year,
                    caption=record.comments,
                    is_published=True,
                    photographer=photographer,
                    scanner=scanner,
                )
                fname = 'original/{}.jpg'.format(photo.uuid)
                shutil.copyfile(filename, os.path.join(settings.MEDIA_ROOT, fname))
                photo.original.name = fname
                photo.save()
                photo.created = record.added_to_archive
                photo.save()
                record.photo = photo
                record.save()
