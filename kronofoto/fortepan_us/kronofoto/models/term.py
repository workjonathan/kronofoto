from django.db import models
from django.db.models import Count
from django.utils.text import slugify
from .collectible import Collectible
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .archive import Archive
from django.http import QueryDict


class TermQuerySet(models.QuerySet["Term"]):
    def objects_for(self, archive: "Archive", category: int) -> models.QuerySet["Term"]:
        """Filter a queryset for a given Archive and Category combination. It's
        just a filter, but the filter selectors are a bit obtuse, so this
        handles it.

        Args:
            archive (Archive): The Archive to filter with.
            category (int): The category ID.

        Returns:
            TermQuerySet: A queryset with only Terms that are relevant for the given Archive and Category.
        """
        return self.filter(
            validcategory__archive=archive, validcategory__category=category
        ).order_by("term")

    def get_by_natural_key(self, name: str) -> "Term":
        return self.get(term=name)


class TermGroup(models.Model):
    """Optionally, Terms can belong to a group. Groups are like folders for
    Terms. But this feature is not used and could be removed.
    """
    name = models.CharField(max_length=64, unique=True)

    def __str__(self) -> str:
        return self.name


class Term(Collectible, models.Model):  # type: ignore
    """Terms are like tags, but they are curated and more general."""
    term = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(unique=True, blank=True, editable=False)
    description = models.TextField(blank=True)
    group = models.ForeignKey(
        TermGroup,
        null=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_terms",
    )
    objects = TermQuerySet.as_manager()

    def natural_key(self) -> str:
        return self.term

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.term)
        super().save(*args, **kwargs)

    def encode_params(self, params: QueryDict) -> str:
        params["term"] = str(self.id)
        return params.urlencode()

    class Meta:
        ordering = ["term"]
        verbose_name = "Subcategory"
        verbose_name_plural = "Subcategories"

    def __str__(self) -> str:
        return self.term
