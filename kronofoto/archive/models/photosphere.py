from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.gis.db import models
import uuid
from os import path
from ..storage import OverwriteStorage


def get_photosphere_path(instance, filename):
    return path.join('photosphere', '{}.jpg'.format(instance.uuid))


class PhotoSphere(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=512, blank=False)
    description = models.TextField()
    image = models.ImageField(upload_to=get_photosphere_path, storage=OverwriteStorage(), null=True, editable=True)
    heading = models.FloatField(
        default=0,
        validators=[MinValueValidator(limit_value=-180), MaxValueValidator(limit_value=180)],
    )
    photos = models.ManyToManyField("Photo", through="PhotoSpherePair")
    location = models.PointField(null=True, srid=4326, blank=True)

    def __str__(self):
        return self.title


class PhotoSpherePair(models.Model):
    photo = models.ForeignKey("Photo", on_delete=models.CASCADE, help_text="Select a photo then click Save and Continue Editing to use the interactive tool")
    photosphere = models.ForeignKey(PhotoSphere, on_delete=models.CASCADE, help_text="Select a photo and photo sphere then click Save and Continue Editing to use the interactive tool")
    azimuth = models.FloatField(default=0, validators=[MinValueValidator(limit_value=-180), MaxValueValidator(limit_value=180)])
    inclination = models.FloatField(default=0, validators=[MinValueValidator(limit_value=-90), MaxValueValidator(limit_value=90)])
    distance = models.FloatField(default=500, validators=[MinValueValidator(limit_value=1), MaxValueValidator(limit_value=2000)])

    class Meta:
        verbose_name = 'Photo position'

    def __str__(self):
        return "{donor} - {fi} - {sphere}".format(donor=self.photo.donor, fi=str(self.photo), sphere=self.photosphere)


