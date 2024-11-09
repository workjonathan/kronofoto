from django.db import models
from .photo import Photo
from .collection import Collection
from django.conf import settings
from django.utils.text import slugify
from fortepan_us.kronofoto.reverse import reverse
from typing import Any

class Exhibit(models.Model):
    name = models.CharField(max_length=256)
    title = models.CharField(max_length=1024, blank=True)
    description = models.TextField(blank=True)
    photo = models.ForeignKey(Photo, null=False, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    collection = models.ForeignKey(Collection, on_delete=models.SET_NULL, null=True)
    credits = models.TextField(blank=True, null=False)

    def get_absolute_url(self, *args: Any, **kwargs: Any) -> str:
        return reverse('kronofoto:exhibit-view', kwargs={'pk': self.pk, 'title': slugify(self.name)})

    def str(self) -> str:
        return self.name

    class Meta:
        db_table = "kronofoto_exhibit"

class Card(models.Model):
    title = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    exhibit = models.ForeignKey(Exhibit, on_delete=models.CASCADE)
    order = models.IntegerField()

    def figures(self) -> "models.QuerySet[Figure]":
        return self.figure_set.all().order_by("order")

    class Meta:
        indexes = (
            models.Index(fields=['exhibit', 'order']),
        )
        db_table = "kronofoto_card"

class PhotoCard(Card):
    photo = models.ForeignKey(Photo, null=True, on_delete=models.SET_NULL, blank=True)

    def photo_choices(self) -> models.Q:
        return models.Q(collection__id=self.exhibit.collection.id) if self.exhibit.collection else models.Q(pk__in=[])

    class Alignment(models.IntegerChoices):
        FULL = 1
        LEFT = 2
        RIGHT = 3

    class Fill(models.IntegerChoices):
        CONTAIN = 1
        COVER = 2

    alignment = models.IntegerField(choices=Alignment.choices, default=Alignment.FULL)
    fill_style = models.IntegerField(choices=Fill.choices, default=Fill.CONTAIN)

    class Meta:
        db_table = "kronofoto_photocard"

class Figure(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    caption = models.TextField(blank=True, default="")
    photo = models.ForeignKey(Photo, null=True, on_delete=models.SET_NULL, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = "kronofoto_figure"
