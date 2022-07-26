from django.contrib.gis.db import models


class LocationQuerySet(models.QuerySet):
    def locate(self, description):
        return self.get(description=description)

class Location(models.Model):
    description = models.TextField(unique=True)
    location_point = models.PointField(null=True, srid=4326, blank=True)
    location_bounds = models.MultiPolygonField(null=True, srid=4326, blank=True)
    objects = LocationQuerySet.as_manager()

    def describe(self):
        return self.description

    def __str__(self):
        return self.description
