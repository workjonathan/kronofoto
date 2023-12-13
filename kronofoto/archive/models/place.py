from django.contrib.gis.db import models

class PlaceType(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False, unique=True)
    def __str__(self):
        return self.name
    class Meta:
        indexes = (
            models.Index(fields=['name']),
        )

class Place(models.Model):
    place_type = models.ForeignKey(PlaceType, null=False, on_delete=models.PROTECT)
    name = models.CharField(max_length=64, null=False, blank=False)
    parent = models.ForeignKey("self", null=True, on_delete=models.SET_NULL)
    geom = models.MultiPolygonField(null=True, srid=4326, blank=False)
    def __str__(self):
        return self.name

    class Meta:
        indexes = (
            models.Index(fields=['name']),
            models.Index(fields=['place_type', 'name', 'parent']),
        )
