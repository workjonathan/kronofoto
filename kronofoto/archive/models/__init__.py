from django.contrib.gis.db import models
from django.contrib.auth.models import User
from .donor import Donor
from .tag import Tag, LowerCaseCharField
from .term import Term
from .collection import Collection
from .collectible import Collectible
from .collectionquery import CollectionQuery
from .location import Location
from .csvrecord import CSVRecord
from .photo import Photo, get_original_path, format_location, PhotoTag
from .wordcount import WordCount
from .cutoff import NewCutoff
from .photosphere import PhotoSphere, PhotoSpherePair, get_photosphere_path


class PrePublishPhoto(models.Model):
    id = models.AutoField(primary_key=True)
    photo = models.OneToOneField(Photo, on_delete=models.CASCADE)


class ScannedPhoto(models.Model):
    image = models.ImageField(upload_to='uploads/%Y/%m/%d/') # callable that incorporates donor name?
    donor = models.ForeignKey(Donor, models.PROTECT)

    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        Donor, null=True, on_delete=models.SET_NULL, related_name="scanned_photos"
    )
    accepted = models.BooleanField(null=True)


class PhotoVote(models.Model):
    photo = models.ForeignKey(ScannedPhoto, on_delete=models.CASCADE, related_name='votes', related_query_name='vote')
    voter = models.ForeignKey(User, on_delete=models.CASCADE)
    infavor = models.BooleanField()


