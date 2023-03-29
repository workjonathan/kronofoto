from django.db import models
from io import BytesIO
import requests
import deal
from PIL import Image, UnidentifiedImageError
from django.core.files.uploadedfile import SimpleUploadedFile
from .photo import Photo
from .donor import Donor

class ConnecticutRecordQuerySet(models.QuerySet):
    pass

class ConnecticutRecord(models.Model):
    file_id1 = models.IntegerField(null=False)
    file_id2 = models.IntegerField(null=False)
    title = models.TextField(null=False)
    year = models.TextField(null=False)
    contributor = models.TextField(null=False)
    description = models.TextField(null=False)
    location = models.TextField(null=False)
    cleaned_year = models.IntegerField(null=True)
    cleaned_city = models.CharField(max_length=128, null=False, default="", blank=True)
    cleaned_county = models.CharField(max_length=128, null=False, default="", blank=True)
    cleaned_state = models.CharField(max_length=128, null=False, default="", blank=True)
    cleaned_country = models.CharField(max_length=128, null=False, default="", blank=True)
    publishable = models.BooleanField(null=False, default=False)

    photo = models.OneToOneField('Photo', on_delete=models.SET_NULL, null=True, unique=True, blank=True)

    objects = ConnecticutRecordQuerySet.as_manager()

    @deal.raises(TypeError, UnidentifiedImageError, ValueError)
    @deal.has('network', "stdout")
    @deal.post(lambda result: result[:10] == b'\xff\xd8\xff\xe0\x00\x10JFIF')
    def hq_jpeg(self):
        resp = requests.get(self.tiff_url())
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
        jpgData = BytesIO()
        img.save(jpgData, "jpeg", optimize=True, quality=95)
        return jpgData.getvalue()

    @deal.has('network', "stdout")
    @deal.pre(lambda self, archive: self.cleaned_year != None)
    @deal.pre(lambda self, archive: self.photo == None)
    @deal.pre(lambda self, archive: not (self.cleaned_city == self.cleaned_county == self.cleaned_state == self.cleaned_country == ''))
    @deal.pre(lambda self, archive: self.contributor == self.contributor.strip())
    @deal.ensure(lambda self, archive, result: Donor.objects.filter(last_name=self.contributor).exists())
    @deal.ensure(lambda self, archive, result: self.title in result.caption)
    @deal.ensure(lambda self, archive, result: self.description in result.caption)
    @deal.ensure(lambda self, archive, result: self.cleaned_city == result.city)
    @deal.ensure(lambda self, archive, result: self.cleaned_county == result.county)
    @deal.ensure(lambda self, archive, result: self.cleaned_state == result.state)
    @deal.ensure(lambda self, archive, result: self.cleaned_country == result.country)
    @deal.ensure(lambda self, archive, result: self.cleaned_year == result.year)
    @deal.post(lambda result: result.original.name.startswith("original"))
    @deal.ensure(lambda self, archive, result: self.publishable == result.is_published)
    @deal.ensure(lambda self, archive, result: self.photo == result)
    def photo_record(self, *, archive):
        photo = Photo(
            archive=archive,
            donor=Donor.objects.get_or_create(last_name=self.contributor, archive=archive)[0],
            city=self.cleaned_city,
            county=self.cleaned_county,
            state=self.cleaned_state,
            country=self.cleaned_country,
            year=self.cleaned_year,
            caption="{}\n\n{}".format(self.title, self.description),
            is_published=self.publishable,
            is_featured=True,
        )
        photo.original = SimpleUploadedFile('original/{}.jpg'.format(photo.uuid), self.hq_jpeg(), content_type="image/jpeg")
        photo.save()
        self.photo = photo
        self.save()
        return photo

    @deal.pure
    def tiff_url(self):
        return "https://ctdigitalarchive.org/islandora/object/{}/datastream/OBJ".format(str(self))

    @deal.pure
    def __str__(self):
        return '{}:{}'.format(self.file_id1, self.file_id2)

    class Meta:
        indexes = [
            models.Index(fields=['file_id1', 'file_id2']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['file_id1', 'file_id2'], name='unique_id_combo'),
        ]




class CSVRecordQuerySet(models.QuerySet):
    @deal.pure
    def bulk_clean(self):
        records = list(self.all())
        for record in records:
            record.clean_whitespace()
        self.bulk_update(
            records,
            [
                'donorFirstName',
                'donorLastName',
                'scanner',
                'photographer',
                'address',
                'city',
                'county',
                'state',
                'country',
                'comments',
            ],
        )

    @deal.pure
    def exclude_geocoded(self):
        return self.filter(photo__isnull=False, photo__location_point__isnull=True)

class CSVRecord(models.Model):
    filename = models.TextField(unique=True)
    # unique constraint seems to make sense to me, but there are quite a few
    # duplicate records. should both be added? Or should we take newer added to
    # archive date to be the true record? Or should this be resolved on a case
    # by case basis?
    donorFirstName = models.TextField()
    donorLastName = models.TextField()
    year = models.IntegerField(null=True)
    circa = models.BooleanField(null=True)
    scanner = models.TextField()
    photographer = models.TextField()
    address = models.TextField()
    city = models.TextField()
    county = models.TextField()
    state = models.TextField()
    country = models.TextField()
    comments = models.TextField()
    added_to_archive = models.DateField()
    photo = models.OneToOneField('Photo', on_delete=models.SET_NULL, null=True)

    objects = CSVRecordQuerySet.as_manager()

    @deal.pure
    def location(self):
        components = []
        if self.country:
            components.append(self.country)
        if self.state:
            components.append(self.state)
        if self.city:
            components.append(self.city)
        elif self.county:
            components.append(self.county)
        if self.address:
            components.append(self.address)
        return ' '.join(reversed(components))


    @deal.pure
    def clean_whitespace(self):
        self.donorFirstName = self.donorFirstName.strip()
        self.donorLastName = self.donorLastName.strip()
        self.scanner = self.scanner.strip()
        self.photographer = self.photographer.strip()
        self.address = self.address.strip()
        self.city = self.city.strip()
        self.county = self.county.strip()
        self.country = self.country.strip()
        self.state = self.state.strip()
        self.comments = self.comments.strip()
