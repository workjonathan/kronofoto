from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.gis.db import models
from fortepan_us.kronofoto.reverse import reverse
import uuid
from os import path
from fortepan_us.kronofoto.storage import OverwriteStorage
from io import BytesIO
from PIL import Image
from PIL.Image import Exif
from PIL.ExifTags import TAGS, GPSTAGS
from django.contrib.gis.geos import Point
from typing import Tuple
from .photo import Photo
from django.http import QueryDict


class IncompleteGPSInfo(Exception):
    """Exif GPS extraction can either return GPS coordinates or raise this
    exception.
    """
    pass


def get_photosphere_path(instance: "PhotoSphere", filename: str) -> str:
    """Get a storage path for a photosphere image.

    Args:
        instance (PhotoSphere): A PhotoSphere model record.
        filename (str): The file's name.

    Returns:
        str: The storage path for this PhotoSphere image.
    """
    return path.join("photosphere", "{}.jpg".format(instance.uuid))

class PhotoSphereSetData(models.Model):
    """Abstract Base Model for Sets and Tours, which both have names and
    descriptions.
    """
    name = models.CharField(max_length=256, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.name

class PhotoSphereTour(PhotoSphereSetData, models.Model):
    """PhotoSpheres can belong to a Tour. These are typically used to group
    PhotoSpheres by area. When a user is in a Tour, they can conveniently jump
    between Sets that have Photos in this Tour.
    """
    sets = models.ManyToManyField("kronofoto.MainStreetSet", through="kronofoto.TourSetDescription")

class MainStreetSet(PhotoSphereSetData, models.Model):
    """PhotoSpheres can belong to a set. These are typically used to group
    PhotoSpheres by decade, but other schemes would be fine.
    """
    tours = models.ManyToManyField("kronofoto.MainStreetSet", through="kronofoto.TourSetDescription")
    def get_absolute_url(self) -> str:
        return reverse("kronofoto:mainstreet-detail", kwargs={"pk": self.pk})

class TourSetDescription(models.Model):
    """This model allows overriding the Set description for a given Tour."""
    tour = models.ForeignKey(PhotoSphereTour, null=False, on_delete=models.CASCADE)
    set = models.ForeignKey(MainStreetSet, null=False, on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tour", "set"], name="unique_tour_set"
            ),
        ]
        indexes = [
            models.Index(fields=["tour", "set"]),
        ]


class PhotoSphere(models.Model):
    """PhotoSpheres are 360 photos. They can have 0 or more Photo objects
    linked. They can optionally also be linked to 0 or more other PhotoSpheres.
    They have a latitude and longitude so that they can be placed on a map.
    They also have a heading which indicates which way is north inside the
    PhotoSphere. This is needed to make arrows point in the correct direction to
    other photospheres.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=512, blank=False)
    description = models.TextField()
    is_published = models.BooleanField(default=True)
    use_new_angles = models.BooleanField(default=True, help_text="This option could fix photo sphere alignment issues. It should be enabled on all photo spheres. However, changing it may knock existing matches off.")
    image = models.ImageField(
        upload_to=get_photosphere_path,
        storage=OverwriteStorage(),
        null=True,
        editable=True,
    )
    heading = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(limit_value=-180),
            MaxValueValidator(limit_value=180),
        ],
    )
    photos = models.ManyToManyField(Photo, through="kronofoto.PhotoSpherePair")
    location = models.PointField(null=True, srid=4326, blank=True)
    tour = models.ForeignKey(
        PhotoSphereTour, default=None, null=True, blank=True, on_delete=models.SET_NULL
    )
    mainstreetset = models.ForeignKey(
        MainStreetSet, default=None, null=True, on_delete=models.SET_NULL
    )
    links = models.ManyToManyField("self", symmetrical=True, blank=True)

    @staticmethod
    def decimal(*, pos: Tuple[float, float, float], ref: str) -> float:
        """Exif annoyingly gives lat/lon as degree-minute-seconds and N S W E.
        This function converts these to one floating point number.

        Args:
            pos (float, float, float): A tuple representing degrees, minutes, seconds respectively. All numbers are >= 0.
            ref (str): N, S, E, or W.

        Returns:
            float: A floating point number incorporating all these numbers ranging from -180 to 180 for W/E or -90 to 90 for N/S.
        """
        degrees = pos[0]
        minutes = pos[1]
        seconds = pos[2]
        minutes += seconds / 60
        return float(degrees + minutes / 60) * (-1 if ref in ("S", "W") else 1)

    def exif_location(self) -> Point:
        """Get the WGS84 Point representing the location of the 360 image
        according to the EXIF data.

        Returns:
            Point: A WGS84 Point.
        """
        contents = self.image.read()
        img = Image.open(BytesIO(contents))
        exif_data = img.getexif()
        exif = {}
        for tag, value in exif_data.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                value = exif_data.get_ifd(tag)
            exif[decoded] = value
        if "GPSInfo" in exif:
            gps_info = {
                GPSTAGS.get(key, key): value for key, value in exif["GPSInfo"].items()
            }
            try:
                lon = self.decimal(
                    pos=gps_info["GPSLongitude"], ref=gps_info["GPSLongitudeRef"]
                )
                lat = self.decimal(
                    pos=gps_info["GPSLatitude"], ref=gps_info["GPSLatitudeRef"]
                )
                return Point(x=lon, y=lat, srid=4326)
            except KeyError as error:
                raise IncompleteGPSInfo from error
        raise IncompleteGPSInfo

    def get_absolute_url(self) -> str:
        """The canonical user facing URL for this 360 image.

        Returns:
            str: The URL for this PhotoSphere.
        """
        query = QueryDict(mutable=True)
        query["id"] = str(self.pk)
        return "{}?{}".format(reverse("kronofoto:mainstreetview"), query.urlencode())

    def __str__(self) -> str:
        return self.title


class PhotoSphereInfo(models.Model):
    "Used to put an Info marker over an interesting detail in a PhotoSphere."
    photosphere = models.ForeignKey(PhotoSphere, on_delete=models.CASCADE, null=False)
    text = models.TextField(blank=False, null=False)
    yaw = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(limit_value=-180),
            MaxValueValidator(limit_value=180),
        ],
    )
    pitch = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(limit_value=-90),
            MaxValueValidator(limit_value=90),
        ],
    )


class PhotoSpherePair(models.Model):
    """A Through model linking a Photo and PhotoSphere.
    This stores the orientation of the Photo in the PhotoSphere.
    """
    photo = models.ForeignKey(
        "Photo",
        on_delete=models.CASCADE,
        help_text="Select a photo then click Save and Continue Editing to use the interactive tool",
    )
    photosphere = models.ForeignKey(
        PhotoSphere,
        on_delete=models.CASCADE,
        help_text="Select a photo and photo sphere then click Save and Continue Editing to use the interactive tool",
    )
    azimuth = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(limit_value=-180),
            MaxValueValidator(limit_value=180),
        ],
    )
    inclination = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(limit_value=-90),
            MaxValueValidator(limit_value=90),
        ],
    )
    distance = models.FloatField(
        default=500,
        validators=[
            MinValueValidator(limit_value=1),
            MaxValueValidator(limit_value=3000),
        ],
    )

    class Meta:
        verbose_name = "Photo position"
        constraints = [
            models.UniqueConstraint(
                fields=["photo", "photosphere"], name="unique_photosphere_photo"
            ),
        ]
        indexes = [
            models.Index(fields=["photo", "photosphere"]),
        ]

    def __str__(self) -> str:
        return "{donor} - {fi} - {sphere}".format(
            donor=self.photo.donor, fi=str(self.photo), sphere=self.photosphere
        )
