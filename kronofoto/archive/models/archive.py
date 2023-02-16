from django.db import models

class Archive(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False)
    short_name = models.CharField(max_length=16, null=False, blank=False)
    cms_root = models.CharField(max_length=16, null=False, blank=False)

    def __str__(self):
        return self.name
