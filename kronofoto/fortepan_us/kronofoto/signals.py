from django.db.models.signals import post_save, m2m_changed, pre_delete
from django.dispatch import receiver
from . import signed_requests
import json
import requests
from django.db.models import Q
from .reverse import reverse
from functools import cached_property
from fortepan_us.kronofoto.models import Photo, WordCount, Tag, Term, PhotoTag, Place, PlaceWordCount, Donor, Archive, RemoteActor
from collections import Counter
import re
from typing import Any, Union, Optional, List, Dict, NoReturn, Type, Iterable
from dataclasses import dataclass


@receiver(post_save, sender=Place)
def place_save(sender: Any, instance: Place, created: Any, raw: Any, using: Any, update_fields: Any, **kwargs: Any) -> None:
    PlaceWordCount.objects.filter(place=instance).delete()
    counts = Counter(w for w in re.split(r"[^\w\']+", instance.name.lower()) if w.strip())
    total = sum(counts.values())
    wordcounts = [
        PlaceWordCount(place=instance, word=w) for w in counts
    ]
    PlaceWordCount.objects.bulk_create(wordcounts)

from fortepan_us.kronofoto.models.activity_schema import ActivitySchema
from fortepan_us.kronofoto.models import activity_dicts

def send_donor_activities(instance: Donor, created: bool, DELETE: bool) -> None:
    if not instance.archive.type == Archive.ArchiveType.LOCAL:
        return
    archive = instance.archive
    from . import signed_requests
    import requests
    import json
    if not archive.remoteactor_set.exists():
        return
    data = ActivitySchema().dump({
        "object": instance if not DELETE else reverse("kronofoto:activitypub_data:archives:contributors:detail", kwargs={'short_name': archive.slug, "pk": instance.pk}),
        "actor": instance.archive,
        "type": "Create" if created else "Delete" if DELETE else "Update",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
    })

    for actor in archive.remoteactor_set.all():
        resp = requests.get(actor.profile)
        profile = resp.json()
        inbox = profile.get("inbox")
        if inbox:
            signed_requests.post(
                inbox,
                data=json.dumps(data),
                headers={
                    "content-type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
                private_key=archive.private_key,
                keyId=archive.keyId,
            )

@receiver(pre_delete, sender=Donor)
def donor_delete_activity(sender: Type[Donor], instance: Donor, using: Any, **kwargs: Any) -> None:
    Sender(data_provider=DonorDeleteSender(instance=instance)).send()

@receiver(post_save, sender=Donor)
def donor_activity(sender: Type[Donor], instance: Donor, created: bool, raw: Any, using: Any, update_fields: Any, **kwargs: Any) -> None:
    Sender(data_provider=DonorUpsertSender(instance=instance, created=created)).send()

@receiver(pre_delete, sender=Photo)
def photo_delete_activity(sender: Type[Photo], instance: Photo, using: Any, **kwargs: Any) -> None:
    if not instance.archive.type == Archive.ArchiveType.LOCAL:
        return
    archive = instance.archive
    if not archive.remoteactor_set.exists():
        return
    from . import signed_requests
    import requests
    import json
    data = activity_dicts.DeleteValue(
        id=archive.ldid() + "#event",
        actor=archive.ldid(),
        object=instance.ldid(),
    ).dump()

    for actor in archive.remoteactor_set.all():
        resp = requests.get(actor.profile)
        profile = resp.json()
        inbox = profile.get("inbox")
        if inbox:
            signed_requests.post(
                inbox,
                data=json.dumps(data),
                headers={
                    "content_type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                    'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                },
                private_key=archive.private_key,
                keyId=archive.keyId,
            )

@dataclass
class Sender:
    data_provider: Union["PhotoDeleteSender", "DonorDeleteSender"]

    def load_profile(self, profile: str) -> Optional[Dict[str, Any]]:
        resp = requests.get(profile)
        if resp.status_code == 200:
            return resp.json()
        else:
            return None

    def send(self) -> None:
        archive = self.data_provider.archive
        if not self.data_provider.is_local:
            return
        for actor in self.data_provider.remote_actors:
            profile = self.load_profile(profile=actor.profile) or {}
            inbox = profile.get("inbox")
            if inbox:
                self.send_data(inbox=inbox, data=self.data_provider.data)

    def send_data(self, inbox: str, data: str) -> None:
        signed_requests.post(
            inbox,
            data=data,
            headers={
                "content_type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
                'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
            private_key=self.data_provider.archive.private_key,
            keyId=self.data_provider.archive.keyId,
        )

@dataclass
class DonorDeleteSender:
    instance: Donor

    @property
    def is_local(self) -> bool:
        return self.instance.archive.type == Archive.ArchiveType.LOCAL

    @property
    def archive(self) -> Archive:
        return self.instance.archive

    @cached_property
    def remote_actors(self) -> Iterable[RemoteActor]:
        return self.instance.archive.remoteactor_set.all()


    @cached_property
    def data(self) -> str:
        return json.dumps(activity_dicts.DeleteValue(
            id=self.instance.archive.ldid() + "#event",
            actor=self.instance.archive.ldid(),
            object=self.instance.ldid(),
        ).dump())

@dataclass
class PhotoDeleteSender:
    instance: Photo

    @property
    def is_local(self) -> bool:
        return self.instance.archive.type == Archive.ArchiveType.LOCAL

    @property
    def archive(self) -> Archive:
        return self.instance.archive

    @cached_property
    def remote_actors(self) -> Iterable[RemoteActor]:
        return self.instance.archive.remoteactor_set.all()

    @cached_property
    def data(self) -> str:
        return json.dumps(activity_dicts.DeleteValue(
            id=self.instance.archive.ldid() + "#event",
            actor=self.instance.archive.ldid(),
            object=self.instance.ldid(),
        ).dump())

@dataclass
class DonorUpsertSender(DonorDeleteSender):
    created: bool

    @cached_property
    def data(self) -> str:
        if self.created:
            cls : Union[Type[activity_dicts.CreateValue], Type[activity_dicts.UpdateValue]] = activity_dicts.CreateValue
        else:
            cls = activity_dicts.UpdateValue

        return json.dumps(cls(
            id=self.instance.archive.ldid() + "#event",
            actor=self.instance.archive.ldid(),
            object=activity_dicts.DonorValue.from_donor(self.instance),
        ).dump())

@dataclass
class PhotoUpsertSender(PhotoDeleteSender):
    created: bool

    @cached_property
    def data(self) -> str:
        if self.created:
            cls : Union[Type[activity_dicts.CreateValue], Type[activity_dicts.UpdateValue]] = activity_dicts.CreateValue
        else:
            cls = activity_dicts.UpdateValue

        return json.dumps(cls(
            id=self.instance.archive.ldid() + "#event",
            actor=self.instance.archive.ldid(),
            object=activity_dicts.PhotoValue.from_photo(self.instance),
        ).dump())



@receiver(post_save, sender=Photo)
def photo_activity(sender: Type[Photo], instance: Photo, created: bool, raw: Any, using: Any, update_fields: Any, **kwargs: Any) -> None:
    Sender(PhotoUpsertSender(instance=instance, created=created)).send()


@receiver(post_save, sender=Photo)
def photo_save(sender: Any, instance: Photo, created: Any, raw: Any, using: Any, update_fields: Any, **kwargs: Any) -> None:
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
def tag_change(sender: Any, instance: PhotoTag, update_fields: Any, **kwargs: Any) -> None:
    WordCount.objects.filter(photo=instance.photo, field='TA').delete()
    counts : Counter = sum((Counter(tag.tag.lower().split()) for tag in instance.photo.tags.filter(phototag__accepted=True)), Counter())
    total = sum(counts.values())
    wordcounts = [
        WordCount(photo=instance.photo, word=w, field='TA', count=counts[w]/total) for w in counts
    ]
    WordCount.objects.bulk_create(wordcounts)

@receiver(m2m_changed, sender=Photo.terms.through)
def photo_save_m2m(sender: Any, instance: Any, action: Any, **kwargs: Any) -> None:
    if action in ('post_add', 'post_remove'):
        WordCount.objects.filter(photo=instance, field='TE').delete()
        counts: Counter = sum((Counter(term.term.lower().split()) for term in instance.terms.all()), Counter())
        total = sum(counts.values())
        wordcounts = [
            WordCount(photo=instance, word=w, field='TE', count=counts[w]/total) for w in counts
        ]
        WordCount.objects.bulk_create(wordcounts)
