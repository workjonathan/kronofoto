from django.db import models
from django.urls import reverse
from django.utils.http import urlencode
from django.contrib.auth.models import User
import uuid


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

    def get_absolute_url(self):
        return '{}?{}'.format(reverse('search-results'), urlencode({'query': 'collection:{}'.format(self.uuid)}))

    def __str__(self):
        return self.name

