from django.db import models
from django.db.models import Count
from django.utils.text import slugify
from .collectible import Collectible

class TermQuerySet(models.QuerySet):
    def objects_for(self, archive: "Archive", category: int) -> models.QuerySet["Term"]:
        return self.filter(validcategory__archive=archive, validcategory__category=category).order_by("term")

class Term(Collectible, models.Model):
    term = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(unique=True, blank=True, editable=False)
    description = models.TextField(blank=True)
    objects = TermQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.term)
        super().save(*args, **kwargs)

    def encode_params(self, params):
        params['term'] = self.id
        return params.urlencode()

    class Meta:
        ordering = ['term']
        verbose_name = "Subcategory"
        verbose_name_plural = "Subcategories"

    @staticmethod
    def index():
        return [
            {'name': term.term, 'count': term.count, 'href': term.get_absolute_url()}
            for term in Term.objects.annotate(count=Count('photo__id')).order_by('term').filter(count__gt=0)
        ]

    def __str__(self):
        return self.term
