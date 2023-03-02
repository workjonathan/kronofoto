from django.db import models
from django.utils.text import slugify
from django.core.validators import MinLengthValidator

class Archive(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False)
    cms_root = models.CharField(max_length=16, null=False, blank=False)
    slug = models.SlugField(unique=True, blank=False)

    def __str__(self):
        return self.name
