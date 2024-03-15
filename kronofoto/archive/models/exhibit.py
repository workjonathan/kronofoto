from django.db import models
from .photo import Photo
from django.conf import settings

class Exhibit(models.Model):
    name = models.CharField(max_length=256)
    title = models.CharField(max_length=256)
    description = models.TextField()
    photo = models.ForeignKey(Photo, null=False, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

class Card(models.Model):
    PLAIN_TEXT = 0
    NO_BORDER = 1
    card_style = models.IntegerField()
    description = models.TextField()
    exhibit = models.ForeignKey(Exhibit, on_delete=models.CASCADE)
    order = models.IntegerField()

    class Meta:
        indexes = (
            models.Index(fields=['exhibit', 'order']),
        )

class PhotoCard(Card):
    photo = models.ForeignKey(Photo, on_delete=models.PROTECT)

class DoublePhotoCard(PhotoCard):
    photo2 = models.ForeignKey(Photo, on_delete=models.PROTECT)
    description2 = models.TextField()
