from django.core.management.base import BaseCommand
from archive.models import Photo, WordCount, Place
from django.db.models import Q
import re
from collections import Counter

class Command(BaseCommand):
    help = 'build word index for search'

    def handle(self, *args, **options):
        WordCount.objects.all().delete()
        wordcounts = []
        # cache_places = {}
        # caching is much more difficult with location_point
        # This may run acceptably fast on postgres.
        for photo in Photo.objects.all().order_by('id'):
            print(photo.id, len(wordcounts))
            if len(wordcounts) > 10000:
                WordCount.objects.bulk_create(wordcounts)
                wordcounts = []
            if photo.place:
                q = Q(lft__lte=photo.place.lft, rght__gte=photo.place.rght, tree_id=photo.place.tree_id)
                if photo.place.geom:
                    q |= Q(geom__contains=photo.place.geom)
                if photo.location_point:
                    q |= Q(geom__contains=photo.location_point)
                places = Place.objects.filter(q)
                counts = sum((Counter(place.name.lower().split()) for place in places), Counter())
                total = sum(counts.values())
                wordcounts += [
                    WordCount(photo=photo, word=w, field='PL', count=counts[w]/total) for w in counts
                ]
            counts = Counter(w for w in re.split(r"[^\w\']+", photo.caption.lower()) if w.strip())
            total = sum(counts.values())
            wordcounts += [
                WordCount(photo=photo, word=w, field='CA', count=counts[w]/total) for w in counts
            ]
            counts = sum((Counter(term.term.lower().split()) for term in photo.terms.all()), Counter())
            total = sum(counts.values())
            wordcounts += [
                WordCount(photo=photo, word=w, field='TE', count=counts[w]/total) for w in counts
            ]
            counts = sum((Counter(tag.tag.lower().split()) for tag in photo.tags.filter(phototag__accepted=True)), Counter())
            total = sum(counts.values())
            wordcounts += [
                WordCount(photo=photo, word=w, field='TA', count=counts[w]/total) for w in counts
            ]
        WordCount.objects.bulk_create(wordcounts)
