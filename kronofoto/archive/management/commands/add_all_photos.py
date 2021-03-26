from django.core.management.base import BaseCommand
from django.conf import settings
from archive.models import CSVRecord, Photo, Collection, Donor
import sys
import os
import shutil
from django.db import transaction


class Command(BaseCommand):
    help = 'add jpegs in a directory and its subdirectories'

    def add_arguments(self, parser):
        parser.add_argument('photo_archive', nargs=1)

    def handle(self, *args, **options):
        for d, _, fs in os.walk(options['photo_archive'][0]):
            for f in fs:
                if not f.startswith('.'):
                    photo = Photo(is_published=False)
                    fname = 'original/{}.jpg'.format(photo.uuid)
                    shutil.copyfile(os.path.join(d, f), os.path.join(settings.MEDIA_ROOT, fname))
                    photo.original.name = fname
                    photo.save()
