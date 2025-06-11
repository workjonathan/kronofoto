from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """The main type of media is Photo, but it is also possible to host Maps and
    Documents. Categories are a way to distinguish media types such as these.
    """
    name = models.CharField(max_length=64, null=False, blank=False)
    slug = models.SlugField(unique=True, blank=False)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class ValidCategory(models.Model):
    """This mechanism allows archives to specify what types of media can be
    uploaded to their archive."""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=False)
    archive = models.ForeignKey("Archive", on_delete=models.CASCADE, null=False)
    terms = models.ManyToManyField("kronofoto.Term")

    def __str__(self) -> str:
        return "{} categories".format(self.category)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "archive"], name="unique_category_archive"
            ),
        ]
        indexes = [
            models.Index(fields=["category", "archive"]),
        ]
