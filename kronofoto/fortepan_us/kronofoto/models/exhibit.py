from django.db import models
from .photo import Photo
from .collection import Collection
from django.conf import settings
from django.utils.text import slugify
from fortepan_us.kronofoto.reverse import reverse
from typing import Any, List, Dict, Tuple
import icontract


class Exhibit(models.Model):
    """Data storage for user created exhibits."""
    name = models.CharField(max_length=256)
    title = models.CharField(max_length=1024, blank=True)
    description = models.TextField(blank=True)
    smalltext = models.TextField(blank=True, default="")
    photo = models.ForeignKey(Photo, null=True, on_delete=models.SET_NULL, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    collection = models.ForeignKey(Collection, on_delete=models.SET_NULL, null=True)
    credits = models.TextField(blank=True, null=False)

    @icontract.require(lambda self: self.id != None)
    def menu_items(self) -> List[Tuple[str, Dict[str, str]]]:
        """Generate a list of actions with link attributes for User's profile
        pertaining to this exhibit.

        Returns:
            list[(str, dict[str, str])]: The str is the action name and the dict represents attributes for the href.
        """
        return [
            (
                "Edit",
                {
                    "href": reverse("kronofoto:exhibit-edit", kwargs={"pk": self.id}),
                },
            ),
            (
                "View",
                {
                    "href": self.get_absolute_url(),
                },
            ),
            (
                "Share",
                {
                    "href": self.get_absolute_url(),
                    "data-clipboard-copy": "",
                },
            ),
            (
                "Embed",
                {
                    "href": reverse("kronofoto:exhibit-embed", kwargs={"pk": self.id}),
                    "hx-get": reverse(
                        "kronofoto:exhibit-embed", kwargs={"pk": self.id}
                    ),
                    "hx-target": "#app",
                },
            ),
            (
                "Delete",
                {
                    "href": reverse("kronofoto:exhibit-delete", kwargs={"pk": self.id}),
                    "hx-get": reverse(
                        "kronofoto:exhibit-delete", kwargs={"pk": self.id}
                    ),
                    "hx-target": "closest section",
                    "hx-swap": "outerHTML",
                    "hx-select": "#my-exhibits",
                },
            ),
        ]

    @icontract.require(lambda self: self.pk is not None)
    def get_main_menu_url(self) -> str:
        """Gets the edit URL for this exhibit.

        Returns:
            str: The edit URL for this exhibit.
        """
        return reverse("kronofoto:exhibit-edit", kwargs={"pk": self.pk})

    def get_absolute_url(self, *args: Any, **kwargs: Any) -> str:
        """Gets the canonical URL for this exhibit.

        Returns:
            str: The URL for this exhibit.
        """
        return reverse(
            "kronofoto:exhibit-view",
            kwargs={"pk": self.pk, "title": slugify(self.name)},
        )

    def str(self) -> str:
        return self.name

    class Meta:
        db_table = "kronofoto_exhibit"


class Card(models.Model):
    """Card model. A card is a combination of a Photo, title, description, and
    small text and some presentation style information.
    """
    class CardType(models.IntegerChoices):
        TEXT_ONLY = 0
        FULL = 1
        LEFT = 2
        RIGHT = 3

    class Fill(models.IntegerChoices):
        COVER = 1
        CONTAIN = 2

    title = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    smalltext = models.TextField(blank=True, default="")
    exhibit = models.ForeignKey(Exhibit, on_delete=models.CASCADE)
    order = models.IntegerField()
    photo = models.ForeignKey(Photo, null=True, on_delete=models.SET_NULL, blank=True)
    card_type = models.IntegerField(
        choices=CardType.choices, default=CardType.TEXT_ONLY
    )
    fill_style = models.IntegerField(choices=Fill.choices, default=Fill.CONTAIN)

    def photo_choices(self) -> models.Q:
        """Get a Query for finding Photo objects that belong to the Collection
        associated with the exhibit. There is an associated Collection because
        it would be difficult for Users to find the photo they want without some
        filtering.

        Returns:
            models.Q: A query for Photos associated with the exhibit's Collection.
        """
        return (
            models.Q(collection__id=self.exhibit.collection.id)
            if self.exhibit.collection
            else models.Q(pk__in=[])
        )

    def figures(self) -> "models.QuerySet[Figure]":
        return self.figure_set.all().order_by("order")

    class Meta:
        indexes = (models.Index(fields=["exhibit", "order"]),)
        db_table = "kronofoto_card"


class PhotoCard(Card):
    """A deprecated Proxy class."""

    def photo_choices(self) -> models.Q:
        return (
            models.Q(collection__id=self.exhibit.collection.id)
            if self.exhibit.collection
            else models.Q(pk__in=[])
        )

    class Meta:
        proxy = True


class Figure(models.Model):
    """Some cards have a set of Photos that they display side by side."""
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    caption = models.TextField(blank=True, default="")
    photo = models.ForeignKey(Photo, null=True, on_delete=models.SET_NULL, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = "kronofoto_figure"
