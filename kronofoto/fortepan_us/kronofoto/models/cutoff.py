from django.db import models
from django.core.exceptions import ValidationError
from typing import Any


class NewCutoff(models.Model):
    date = models.DateField()

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.pk and NewCutoff.objects.exists():
            raise ValidationError("There can be only one instance of this object")
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return 'Cutoff date for "new" photos'
