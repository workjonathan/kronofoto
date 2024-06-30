from django.http import QueryDict
from django.db import models
from django.db.models import Count
from django.utils.text import slugify
from .collectible import Collectible
from typing import Any, Dict, List



class LowerCaseCharField(models.CharField):
    def get_prep_value(self, value: str) -> str:
        return str(value).lower()


class TagQuerySet(models.QuerySet):
    def __str__(self) -> str:
        return ', '.join(str(t) for t in self)


class Tag(Collectible, models.Model):
    tag = LowerCaseCharField(max_length=64, unique=True)
    slug = models.SlugField(unique=True, blank=True, editable=False)

    objects = TagQuerySet.as_manager()

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.tag)
        super().save(*args, **kwargs)

    def encode_params(self, params: QueryDict) -> str:
        params['tag'] = self.tag
        return params.urlencode()

    @staticmethod
    def dead_tags() -> TagQuerySet:
        return Tag.objects.annotate(photo_count=Count('phototag')).filter(photo_count=0)

    @staticmethod
    def index() -> List[Dict[str, Any]]:
        return [
            {'name': tag.tag, 'count': tag.count, 'href': tag.get_absolute_url()}
            for tag in Tag.objects.filter(phototag__accepted=True).annotate(count=Count('phototag__id')).order_by('tag')
        ]

    def __str__(self) -> str:
        return self.tag

    class Meta:
        ordering = ('tag',)
