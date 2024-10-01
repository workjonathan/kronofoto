from django.core.management.base import BaseCommand
from archive.models import Photo, WordCount
from django.db.models import Count, Min, Max
import re
from collections import Counter

class Command(BaseCommand):
    help = 'build word index for search'

    def handle(self, *args, **options):
        for pt in Photo.tags.through.objects.values('photo', 'tag').annotate(c=Count('photo'), gi=Min('id'), bi=Max('id')).filter(c__gt=1):
            for ptc in Photo.tags.through.creator.through.objects.filter(phototag_id=pt['bi']):
                ptc.phototag_id = pt['gi']
            Photo.tags.through.objects.filter(id=pt['bi']).delete()
