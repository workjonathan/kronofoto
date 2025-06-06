from django.db import models
from django.conf import settings


class UserData(models.Model):
    """Extra storage for User data."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=False, on_delete=models.CASCADE
    )
    has_seen_exhibit_tour = models.BooleanField(default=False)
