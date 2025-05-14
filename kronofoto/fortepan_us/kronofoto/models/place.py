from django.contrib.gis.db import models
from django.db.models.functions import Concat, Upper
from mptt.models import MPTTModel, TreeForeignKey  # type: ignore
from mptt.querysets import TreeQuerySet # type: ignore
from fortepan_us.kronofoto.reverse import reverse
from django.http import QueryDict
from django.contrib.contenttypes.models import ContentType
from typing import Any, Optional, Dict, TYPE_CHECKING
from .archive import RemoteActor


class PlaceType(models.Model): # type: ignore[django-manager-missing]
    """Places use PlaceTypes to distinguish countries from states or other things."""
    name = models.CharField(max_length=64, null=False, blank=False, unique=True)

    def name_places(self) -> None:
        if self.name == "Country":
            self.place_set.all().update(fullname=models.F("name"))
        elif self.name == "US State":
            self.place_set.all().update(fullname=Concat("name", models.Value(", USA")))
        elif self.name == "US County":
            updates = list(
                self.place_set.all().annotate(
                    newfullname=Concat(
                        "name", models.Value(" County, "), "parent__name"
                    )
                )
            )
            for place in updates:
                place.fullname = place.newfullname
            Place.objects.bulk_update(updates, ["fullname"])
        elif self.name == "US Town" or self.name == "US Unincorporated Area":
            updates = list(
                self.place_set.all().annotate(
                    newfullname=Concat("name", models.Value(", "), "parent__name")
                )
            )
            for place in updates:
                place.fullname = place.newfullname
            Place.objects.bulk_update(updates, ["fullname"])

    def __str__(self) -> str:
        return self.name

    class Meta:
        indexes = (models.Index(fields=["name"]),)

class PlaceQuerySet(TreeQuerySet):
    def zoom(self, level: int) -> "PlaceQuerySet":
        """Filter places visible at the specified Mapbox vector tile zoom level.

        A place is considered visible on the map if its
        `min_level <= level < max_level`.

        Args:
            level (int): The Mapbox vector tile zoom level to filter by.

        Returns:
            PlaceQuerySet: Only those places whose level range inclues `level`.
        """
        return self.filter(min_level__lte=level, max_level__gt=level)

class Place(MPTTModel):
    """A model for Place objects.

    Places are places on Earth. They have geometry, and they have parents. That
    way something can be in a Place because we say it is in that Place, or a
    child of the Place. We can also say that something is in a Place because it
    has its own geometry that is within that Place, or because we say it is in a
    Place has geometry within a Place. For example, cities often have geometry
    that is incidentally within a county, but they are not children of the
    county, so those cities can be considered within the county Place. Other
    cities span multiple counties, so those cities are not within those
    counties.
    """
    place_type: models.ForeignKey[PlaceType, PlaceType] = models.ForeignKey(
        PlaceType, null=False, on_delete=models.PROTECT
    )
    owner: models.ForeignKey[RemoteActor, RemoteActor] = models.ForeignKey(RemoteActor, null=True, on_delete=models.CASCADE, blank=True)
    name: models.CharField = models.CharField(max_length=64, null=False, blank=False)
    geom: models.GeometryField = models.GeometryField(null=True, srid=4326, blank=False)
    parent = TreeForeignKey(
        "self",
        related_name="children",
        null=True,
        db_index=True,
        on_delete=models.PROTECT,
    )
    fullname: models.CharField = models.CharField(
        max_length=128, null=False, default=""
    )
    min_level : models.IntegerField = models.IntegerField(null=True, blank=True)
    max_level : models.IntegerField = models.IntegerField(null=True, blank=True)
    objects = PlaceQuerySet.as_manager()

    def ldid(self) -> str:
        """Gets the ActivityPub LD-ID. It is a url which will contain a JSON
        definition of this Place. It may or may not be on this server.

        Returns:
            str: The URL for the JSON definition of this Place.
        """
        from .ldid import LdId
        try:
            return LdId.objects.get(content_type__app_label="kronofoto", content_type__model="place", object_id=self.id).ld_id
        except LdId.DoesNotExist:
            return reverse(
                "kronofoto:activitypub-main-service-places",
                kwargs={"pk": self.id},
            )

    def is_owned_by(self, actor: RemoteActor) -> bool:
        """Determines whether this object is owned by a remote actor.

        Args:
            actor (RemoteActor): An activitypub actor.

        Returns:
            bool: True if actor owns this Place.
        """
        return self.owner.id == actor.id


    def get_absolute_url(
        self,
        kwargs: Optional[Dict[str, Any]] = None,
        params: Optional[QueryDict] = None,
    ) -> str:
        """Return the canonical user facing url for this Place.

        The canonical url is a search for Photo objects in this Place. This
        loosens the argument contract for get_absolute_url by adding some
        optional parameters that preserve archive, category, and certain search
        parameters.

        Args:
            kwargs (dict[str, Any], optional): None by default. These are keyword arguments to the URL. This is used to preserve archive and category filtering.
            params (QueryDict, optional): None by default. These are used to preserve search filtering. It is mainly used to preserve the filtering of embedded web componenets.

        Returns:
            str: The URL for a search for Photos in this Place.
        """
        kwargs = kwargs or {}
        kwargs = dict(**kwargs)
        url = reverse("kronofoto:gridview", kwargs=kwargs)
        params = params or QueryDict(mutable=True)
        params["place"] = self.id
        if params:
            return "{}?{}".format(url, params.urlencode())
        return url

    class MPTTMeta:
        order_insertion_by = ["place_type", "name"]

    def __str__(self) -> str:
        return self.fullname

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="place_zoom_levels_defined",
                check=(models.Q(min_level__isnull=True) & models.Q(max_level__isnull=True)) | models.Q(min_level__lt=models.F("max_level"))
            ),
        ]
        indexes = (
            models.Index(fields=["min_level", "max_level"]),
            models.Index(fields=["name"]),
            models.Index(fields=["fullname"]),
            models.Index(fields=["place_type", "name", "parent"]),
            models.Index(
                fields=["tree_id", "lft", "rght"], name="archive_tree_nested_set_index"
            ),
            models.Index(Upper("fullname"), name="archive_place_icase_fullname"),
            models.Index(Upper("name"), "place_type", name="archive_place_icase_name"),
        )
