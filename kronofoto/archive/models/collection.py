from django.db import models
from ..reverse import reverse
from django.utils.http import urlencode
from django.contrib.auth.models import User
import uuid
import deal

class CollectionQuerySet(models.QuerySet):
    @deal.ensure(lambda self, photo, result:
        all(bool(collection.membership) == collection.photos.filter(id=photo).exists() for collection in result)
    )
    def count_photo_instances(self, *, photo):
        return self.annotate(
            membership=models.Count('photos', filter=models.Q(photos__id=photo))
        )

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
    photos = models.ManyToManyField('Photo', blank=True)

    objects = CollectionQuerySet.as_manager()

    def get_absolute_url(self):
        return '{}?{}'.format(reverse('kronofoto:gridview'), urlencode({'query': 'collection:{}'.format(self.uuid)}))

    def __str__(self):
        return self.name

