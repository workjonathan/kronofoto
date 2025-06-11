from django.db import models
from fortepan_us.kronofoto.reverse import reverse
from django.utils.http import urlencode
from django.contrib.auth.models import User
import uuid
import icontract
from .photo import Photo
from django.db.models import QuerySet
from django.db.models.functions import Lower
from typing import Optional
from typing import Dict, Any, Protocol, List, Tuple
import json


class CollectionQuerySet(models.QuerySet):
    @icontract.ensure(
        lambda self, photo, result: all(
            bool(collection.membership) == collection.photos.filter(id=photo).exists()
            for collection in result
        )
    )
    def count_photo_instances(self, *, photo: Any) -> Dict[str, Any]:
        """Annotate the queryset with a count of how many times this photo
        appears in each collection.

        Args:
            photo (Photo): The photo we are counting instances of.

        Returns:
            CollectionQuerySet: The queryset with a `membership` field, which is 0 if the photo is not in the collection and 1 if it is in the collection.
        """
        return self.annotate(
            membership=models.Count("photos", filter=models.Q(photos__id=photo))
        )

    def by_user(
        self, *, user: User, visibility: Optional[str] = None
    ) -> "CollectionQuerySet":
        """Filter to collections owned by a given user and optionally also
        filter for visibility.

        Args:
            user (User): The User that created these collections.
            visibility (str, optional): Allows filtering to only public or private collections.

        Returns:
            CollectionQuerySet: A queryset containing collections owned by the user with the desired visibility, in alphabetical order.
        """
        objs = self.filter(owner=user)
        if visibility:
            objs.filter(visibility=visibility)
        return objs.order_by(Lower("name"))


class Collection(models.Model):
    """Users can put together private or public lists of photos for timeline
    filtering.
    """
    PRIVACY_TYPES = [
        ("PR", "Private"),
        ("UL", "Unlisted"),
        ("PU", "Public"),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=512)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    visibility = models.CharField(max_length=2, choices=PRIVACY_TYPES)
    photos = models.ManyToManyField("kronofoto.Photo", blank=True)

    objects = CollectionQuerySet.as_manager()

    @icontract.require(lambda self: self.id != None)
    def menu_items(self) -> List[Tuple[str, Dict[str, str]]]:
        """Get a list of links for this Collection for the user's profile page.

        Returns:
            list[(str, dict[str, str])]: A list of tuples. The first is the action name, the second is a dictionary of HTML attributes and their values.
        """
        return [
            (
                "Edit",
                {
                    "href": reverse(
                        "kronofoto:collection-edit", kwargs={"pk": self.id}
                    ),
                    "hx-get": reverse(
                        "kronofoto:collection-edit", kwargs={"pk": self.id}
                    ),
                    "hx-target": "#app",
                },
            ),
            (
                "View",
                {
                    "href": self.get_absolute_url(),
                    "hx-get": self.get_absolute_url(),
                    "hx-target": "#app",
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
                    "href": reverse(
                        "kronofoto:collection-embed", kwargs={"pk": self.id}
                    ),
                    "hx-get": reverse(
                        "kronofoto:collection-embed", kwargs={"pk": self.id}
                    ),
                    "hx-target": "#app",
                },
            ),
            (
                "Delete",
                {
                    "href": reverse(
                        "kronofoto:collection-delete", kwargs={"pk": self.id}
                    ),
                    "hx-get": reverse(
                        "kronofoto:collection-delete", kwargs={"pk": self.id}
                    ),
                    "hx-target": "closest section",
                    "hx-select": "#my-lists",
                    "hx-swap": "outerHTML",
                },
            ),
            (
                "Use in a FotoStory",
                {
                    "href": "{}?collection={}".format(
                        reverse("kronofoto:exhibit-create"), self.id
                    ),
                    "hx-post": reverse("kronofoto:exhibit-create"),
                    "hx-vals": json.dumps({"collection": self.id}),
                    "hx-target": "#app",
                },
            ),
        ]

    def get_main_menu_url(self) -> str:
        """Get the main menu edit url, which is just the grid view for this collection.

        Returns:
            str: A URL.
        """
        return self.get_absolute_url()

    def get_absolute_url(self) -> str:
        """Get the canonical user facing url, which is just the grid view for
        this collection.

        Returns:
            str: A URL.
        """
        return "{}?{}".format(
            reverse("kronofoto:gridview"),
            urlencode({"query": "collection:{}".format(self.uuid)}),
        )

    def __str__(self) -> str:
        return self.name
