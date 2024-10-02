from django.core.management.base import BaseCommand
from archive.models import Place, PlaceWordCount
import re
from collections import Counter

class Command(BaseCommand):
    help = 'build word index for search'

    def handle(self, *args, **options):
        PlaceWordCount.objects.all().delete()
        wordcounts = []
        for place in Place.objects.all():
            counts = Counter(w for w in re.split(r"[^\w\']+", place.name.lower()) if w.strip())
            total = sum(counts.values())
            wordcounts += [
                PlaceWordCount(place=place, word=w) for w in counts
            ]
        PlaceWordCount.objects.bulk_create(wordcounts)
