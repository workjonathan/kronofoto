from django.db import models

class Donor(models.Model):
    last_name = models.CharField(max_length=256)
    first_name = models.CharField(max_length=256)
    home_phone = models.CharField(max_length=256)
    street1 = models.CharField(max_length=256)
    street2 = models.CharField(max_length=256)
    city = models.CharField(max_length=256)
    state = models.CharField(max_length=256)
    zip = models.CharField(max_length=256)
    country = models.CharField(max_length=256)

class Collection(models.Model):
    name = models.CharField(max_length=512)
    donors = models.ManyToManyField(Donor)
    displayed_donors = models.CharField(max_length=512)
    description = models.TextField()
    year_min = models.SmallIntegerField('oldest photo year', editable=False, null=True)
    year_max = models.SmallIntegerField('newest photo year', editable=False, null=True)
    total_photos = models.SmallIntegerField('photos', editable=False)
    is_published = models.BooleanField(default=False)

class Photo(models.Model):
    accession_number = models.CharField(max_length=50, unique=True)
    collection = models.ForeignKey(Collection, models.PROTECT)
    city = models.CharField(max_length=128)
    county = models.CharField(max_length=128)
    state = models.CharField(max_length=64)
    country = models.CharField(max_length=64, null=True)
    year = models.SmallIntegerField(null=True)
    caption = models.TextField()
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
