from django.db import models
from ..reverse import reverse
from django.utils.http import urlencode
from django.contrib.auth.models import User
import uuid
import deal
from .photo import Photo
from django.db.models import QuerySet
from django.db.models.functions import Lower
from typing import Optional

class CollectionQuerySet(models.QuerySet):
    @deal.ensure(lambda self, photo, result:
        all(bool(collection.membership) == collection.photos.filter(id=photo).exists() for collection in result)
    )
    def count_photo_instances(self, *, photo: Photo) -> 'CollectionQuerySet':
        return self.annotate(
            membership=models.Count('photos', filter=models.Q(photos__id=photo))
        )

    def by_user(self, *, user: User, visibility: Optional[str]=None) -> "CollectionQuerySet":
        objs = self.filter(owner=user)
        if visibility:
            objs.filter(visibility=visibility)
        return objs.order_by(Lower("name"))

class Collection(models.Model):
    PRIVACY_TYPES = [
        ('PR', 'Private'),
        ('UL', 'Unlisted'),
        ('PU', 'Public'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=512)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    visibility = models.CharField(max_length=2, choices=PRIVACY_TYPES)
    photos = models.ManyToManyField('archive.Photo', blank=True)

    objects = CollectionQuerySet.as_manager()

    def get_absolute_url(self) -> str:
        return '{}?{}'.format(reverse('kronofoto:gridview'), urlencode({'query': 'collection:{}'.format(self.uuid)}))

    def __str__(self) -> str:
        return self.name

