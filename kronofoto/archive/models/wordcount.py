from django.db import models
from .photo import Photo


class WordCount(models.Model):
    FIELDS = [
        ('CA', 'Caption'),
        ('TA', 'Tag'),
        ('TE', 'Term'),
    ]
    photo = models.ForeignKey(Photo, models.CASCADE)
    word = models.CharField(max_length=64, blank=True, db_index=True)
    field = models.CharField(max_length=2, choices=FIELDS, db_index=True)
    count = models.FloatField()

    class Meta:
        unique_together = [
            ('word', 'field', 'photo')
        ]
