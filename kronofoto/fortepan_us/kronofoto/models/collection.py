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
        return self.annotate(
            membership=models.Count("photos", filter=models.Q(photos__id=photo))
        )

    def by_user(
        self, *, user: User, visibility: Optional[str] = None
    ) -> "CollectionQuerySet":
        objs = self.filter(owner=user)
        if visibility:
            objs.filter(visibility=visibility)
        return objs.order_by(Lower("name"))


class Collection(models.Model):
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
        return self.get_absolute_url()

    def get_absolute_url(self) -> str:
        return "{}?{}".format(
            reverse("kronofoto:gridview"),
            urlencode({"query": "collection:{}".format(self.uuid)}),
        )

    def __str__(self) -> str:
        return self.name
