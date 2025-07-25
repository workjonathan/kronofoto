from django.db import models
from .photo import Photo
from .place import Place


class WordCount(models.Model):
    """To facilitate fast searches of multi word fields like tag, term, and
    caption.
    """
    FIELDS = [
        ("CA", "Caption"),
        ("TA", "Tag"),
        ("TE", "Term"),
    ]
    photo = models.ForeignKey(Photo, models.CASCADE)
    word = models.CharField(max_length=64, blank=True, db_index=True)
    field = models.CharField(max_length=2, choices=FIELDS, db_index=True)
    count = models.FloatField()

    class Meta:
        unique_together = [("word", "field", "photo")]


class PlaceWordCount(models.Model):
    """To facilitate fast searches of places which can have multi word names.
    """
    place = models.ForeignKey(Place, models.CASCADE)
    word = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        unique_together = [("word", "place")]
