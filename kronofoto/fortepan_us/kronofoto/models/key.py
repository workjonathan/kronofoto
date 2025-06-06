from django.db import models
from django.conf import settings


class Key(models.Model):
    """Used to allow users to export data in CSV. This is not used though."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=80, unique=True)
    key = models.CharField(max_length=80)
