from django.db import models
from django.utils.text import slugify
from .term import Term

class Category(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False)
    slug = models.SlugField(unique=True, blank=False)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class ValidCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=False)
    archive = models.ForeignKey("Archive", on_delete=models.CASCADE, null=False)
    terms = models.ManyToManyField(Term)

    def __str__(self) -> str:
        return "{} categories".format(self.category)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['category', 'archive'], name='unique_category_archive'),
        ]
        indexes = [
            models.Index(fields=['category', 'archive']),
        ]

