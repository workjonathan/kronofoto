from django.core.management.base import BaseCommand
from django.db import models
from django.db.models.functions import Cast, Left
import re
from ...models.csvrecord import ConnecticutRecord
from ...models.archive import Archive
from PIL import Image, UnidentifiedImageError

class Command(BaseCommand):
    help = 'build ctda records'

    def add_arguments(self, parser):
        parser.add_argument('archive_slug')

    def handle(self, *args, archive_slug, **options):
        archive = Archive.objects.get(slug=archive_slug)
        for r in ConnecticutRecord.objects.filter(publishable=True, cleaned_year__isnull=False, photo__isnull=True).exclude(cleaned_county='', cleaned_city='', cleaned_state='', cleaned_country=''):
            r.photo_record(archive=archive)
