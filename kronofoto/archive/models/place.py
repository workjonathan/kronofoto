from django.contrib.gis.db import models
from django.db.models.functions import Concat
from mptt.models import MPTTModel, TreeForeignKey


class PlaceType(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False, unique=True)

    def name_places(self):
        if self.name == "Country":
            self.place_set.all().update(fullname=models.F("name"))
        elif self.name == "US State":
            self.place_set.all().update(fullname=Concat("name", models.Value(", USA")))
        elif self.name == "US County":
            updates = list(self.place_set.all().annotate(newfullname=Concat("name", models.Value(" County, "), "parent__name")))
            for place in updates:
                place.fullname = place.newfullname
            Place.objects.bulk_update(updates, ['fullname'])
        elif self.name == "US Town":
            updates = list(self.place_set.all().annotate(newfullname=Concat("name", models.Value(", "), "parent__name")))
            for place in updates:
                place.fullname = place.newfullname
            Place.objects.bulk_update(updates, ['fullname'])

    def __str__(self):
        return self.name

    class Meta:
        indexes = (
            models.Index(fields=['name']),
        )

class Place(MPTTModel):
    place_type = models.ForeignKey(PlaceType, null=False, on_delete=models.PROTECT)
    name = models.CharField(max_length=64, null=False, blank=False)
    geom = models.GeometryField(null=True, srid=4326, blank=False)
    parent = TreeForeignKey('self', related_name='children', null=True, db_index=True, on_delete=models.PROTECT)
    fullname = models.CharField(max_length=128, null=False, default="")

    class MPTTMeta:
        order_insertion_by = ['place_type', 'name']

    def __str__(self):
        return self.name

    def collect_and_place_photos(self):
        from .photo import Photo

        if self.place_type.name == "Country":
            return Photo.objects.filter(place__isnull=True, address="", country__iexact=self.name, city="", state="", county="").update(place=self)
        elif self.place_type.name == "US State":
            return Photo.objects.filter(place__isnull=True, address="", country=self.parent.name, city="", state__iexact=self.name, county="").update(place=self)
        elif self.place_type.name == "US County":
            return (Photo.objects.filter(place__isnull=True, address="", city="", state__iexact=self.parent.name, county__iexact=self.name).update(place=self) +
            Photo.objects.filter(place__isnull=True, address="", city="", state__iexact=self.parent.name, county__iexact=self.name + " county").update(place=self))
        elif self.place_type.name == "US Town":
            return Photo.objects.filter(place__isnull=True, address="", city__iexact=self.name, state__iexact=self.parent.name).update(place=self)

    class Meta:
        indexes = (
            models.Index(fields=['name']),
            models.Index(fields=['fullname']),
            models.Index(fields=['place_type', 'name', "parent"]),
            #models.Index(fields=['tree_id', 'id', "lft"]),
        )
