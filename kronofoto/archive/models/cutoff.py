from django.db import models
from django.core.exceptions import ValidationError


class NewCutoff(models.Model):
    date = models.DateField()

    def save(self, *args, **kwargs):
        if not self.pk and NewCutoff.objects.exists():
            raise ValidationError('There can be only one instance of this object')
        return super().save(*args, **kwargs)

    def __str__(self):
        return 'Cutoff date for "new" photos'
