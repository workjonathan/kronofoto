from django.contrib.gis.db import models
from mptt.models import MPTTModel, TreeForeignKey


class PlaceType(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False, unique=True)
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
            models.Index(fields=['place_type', 'name', "parent"]),
            #models.Index(fields=['tree_id', 'id', "lft"]),
        )
