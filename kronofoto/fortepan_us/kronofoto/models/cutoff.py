from django.db import models
from django.core.exceptions import ValidationError
from typing import Any


class NewCutoff(models.Model):
    """Allows an administrator to specify what constitutes a new Photo. There is
    one allowed instance of this record.  Anything newer than that is considered
    to be a New Photo.
    """
    date = models.DateField()

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Overridden save prevents creating a second instance, although this
        could be circumvented by setting a unique ID in code. Don't do that.
        """
        if not self.pk and NewCutoff.objects.exists():
            raise ValidationError("There can be only one instance of this object")
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return 'Cutoff date for "new" photos'
