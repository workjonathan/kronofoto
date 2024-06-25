from django.db import models
from .photo import Photo
from .collection import Collection
from django.conf import settings
from django.utils.text import slugify
from ..reverse import reverse

class Exhibit(models.Model):
    name = models.CharField(max_length=256)
    title = models.CharField(max_length=256)
    description = models.TextField()
    photo = models.ForeignKey(Photo, null=False, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    collection = models.ForeignKey(Collection, on_delete=models.SET_NULL, null=True)

    def get_absolute_url(self) -> str:
        return reverse('kronofoto:exhibit-view', kwargs={'pk': self.pk, 'title': slugify(self.name)})
    def str(self) -> str:
        return self.name

class Card(models.Model):
    PLAIN_TEXT = 0
    NO_BORDER = 1
    card_style = models.IntegerField(default=0)
    title = models.TextField(blank=True, default="")
    description = models.TextField()
    exhibit = models.ForeignKey(Exhibit, on_delete=models.CASCADE)
    order = models.IntegerField()

    class Meta:
        indexes = (
            models.Index(fields=['exhibit', 'order']),
        )

class PhotoCard(Card):
    photo = models.ForeignKey(Photo, on_delete=models.PROTECT)

    def photo_choices(self) -> models.Q:
        return models.Q(collection__id=self.exhibit.collection.id) if self.exhibit.collection else models.Q(pk__in=[])

    class Alignment(models.IntegerChoices):
        FULL = 1
        LEFT = 2
        RIGHT = 3
    alignment = models.IntegerField(choices=Alignment.choices, default=Alignment.FULL)

class Figure(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    caption = models.TextField(blank=True, default="")
    photo = models.ForeignKey(Photo, on_delete=models.PROTECT)
    order = models.IntegerField(default=0)
