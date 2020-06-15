from django.core.management.base import BaseCommand
from archive.models import Photo, WordCount
import re
from collections import Counter

class Command(BaseCommand):
    help = 'build word index for search'

    def handle(self, *args, **options):
        WordCount.objects.all().delete()
        wordcounts = []
        for photo in Photo.objects.all():
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
            counts = sum((Counter(tag.tag.lower().split()) for tag in photo.tags.all()), Counter())
            total = sum(counts.values())
            wordcounts += [
                WordCount(photo=photo, word=w, field='TA', count=counts[w]/total) for w in counts
            ]
        WordCount.objects.bulk_create(wordcounts)
