from django.db import models
from django.conf import settings

class Key(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=80, unique=True)
    key = models.CharField(max_length=80)
    class Meta:
        db_table = 'kronofoto_key'
