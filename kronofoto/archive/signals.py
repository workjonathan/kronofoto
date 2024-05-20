from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.db.models import Q
from .models import Photo, WordCount, Tag, Term, PhotoTag, Place, PlaceWordCount
from collections import Counter
import re


@receiver(post_save, sender=Place)
def place_save(sender, instance, created, raw, using, update_fields, **kwargs):
    PlaceWordCount.objects.filter(place=instance).delete()
    counts = Counter(w for w in re.split(r"[^\w\']+", instance.name.lower()) if w.strip())
    total = sum(counts.values())
    wordcounts = [
        PlaceWordCount(place=instance, word=w) for w in counts
    ]
    PlaceWordCount.objects.bulk_create(wordcounts)

@receiver(post_save, sender=Photo)
def photo_save(sender, instance, created, raw, using, update_fields, **kwargs):
    WordCount.objects.filter(photo=instance, field='CA').delete()
    WordCount.objects.filter(photo=instance, field='PL').delete()
    counts = Counter(w for w in re.split(r"[^\w\']+", instance.caption.lower()) if w.strip())
    total = sum(counts.values())
    wordcounts = [
        WordCount(photo=instance, word=w, field='CA', count=counts[w]/total) for w in counts
    ]
    if instance.place:
        q = Q(lft__lte=instance.place.lft, rght__gte=instance.place.rght, tree_id=instance.place.tree_id)
        if instance.place.geom:
            q |= Q(geom__contains=instance.place.geom)
        if instance.location_point:
            q |= Q(geom__contains=instance.location_point)
        places = Place.objects.filter(q)
        instance.places.set(places)
        counts = sum((Counter(place.name.lower().split()) for place in places), Counter())
        total = sum(counts.values())
        wordcounts += [
            WordCount(photo=instance, word=w, field='PL', count=counts[w]/total) for w in counts
        ]
    WordCount.objects.bulk_create(wordcounts)

@receiver(post_save, sender=PhotoTag)
def tag_change(sender, instance, update_fields, **kwargs):
    WordCount.objects.filter(photo=instance.photo, field='TA').delete()
    counts = sum((Counter(tag.tag.lower().split()) for tag in instance.photo.tags.filter(phototag__accepted=True)), Counter())
    total = sum(counts.values())
    wordcounts = [
        WordCount(photo=instance.photo, word=w, field='TA', count=counts[w]/total) for w in counts
    ]
    WordCount.objects.bulk_create(wordcounts)

@receiver(m2m_changed, sender=Photo.terms.through)
def photo_save_m2m(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove'):
        WordCount.objects.filter(photo=instance, field='TE').delete()
        counts = sum((Counter(term.term.lower().split()) for term in instance.terms.all()), Counter())
        total = sum(counts.values())
        wordcounts = [
            WordCount(photo=instance, word=w, field='TE', count=counts[w]/total) for w in counts
        ]
        WordCount.objects.bulk_create(wordcounts)
