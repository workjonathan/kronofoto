from django.db import models
from django.db.models import Count
from django.utils.text import slugify
from .collectible import Collectible


class LowerCaseCharField(models.CharField):
    def get_prep_value(self, value):
        return str(value).lower()


class TagQuerySet(models.QuerySet):
    def __str__(self):
        return ', '.join(str(t) for t in self)


class Tag(Collectible, models.Model):
    tag = LowerCaseCharField(max_length=64, unique=True, editable=False)
    slug = models.SlugField(unique=True, blank=True, editable=False)

    objects = TagQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.tag)
        super().save(*args, **kwargs)

    def encode_params(self, params):
        params['tag'] = self.tag
        return params.urlencode()

    @staticmethod
    def dead_tags():
        return Tag.objects.annotate(photo_count=Count('phototag')).filter(photo_count=0)

    @staticmethod
    def index():
        return [
            {'name': tag.tag, 'count': tag.count, 'href': tag.get_absolute_url()}
            for tag in Tag.objects.filter(phototag__accepted=True).annotate(count=Count('phototag__id')).order_by('tag')
        ]

    def __str__(self):
        return self.tag

    class Meta:
        ordering = ('tag',)
