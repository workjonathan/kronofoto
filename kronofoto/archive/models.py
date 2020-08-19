from django.db.models import Q, Window, F, Min, Subquery, Count, OuterRef, Sum
from django.urls import reverse
from django.db.models.functions import RowNumber
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.contrib.auth.models import User
import uuid
from PIL import Image, ExifTags, ImageOps
from io import BytesIO
import os
from functools import reduce
import operator
from bisect import bisect_left as bisect


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
    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)


class Collection(models.Model):
    PRIVACY_TYPES = [
        ('PR', 'Private'),
        ('UL', 'Unlisted'),
        ('PU', 'Public'),
    ]
    name = models.CharField(max_length=512)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    visibility = models.CharField(max_length=2, choices=PRIVACY_TYPES)
    photos = models.ManyToManyField('Photo', blank=True)

    def __str__(self):
        return self.name


class Term(models.Model):
    term = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(unique=True, blank=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.term)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.term


class Tag(models.Model):
    tag = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(unique=True, blank=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.tag)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.tag

class PhotoQuerySet(models.QuerySet):
    def year_links(self, params=None):
        year_index = self.year_index()
        years = [p.year for p in year_index]
        allyears = [(year, year_index[bisect(years, year)]) for year in range(years[0], years[-1]+1)]
        return [
            (year, photo.get_absolute_url(params=params), photo.get_json_url(params=params))
            for (year, photo) in allyears
        ]

    def year_index(self):
        yearid = self.values('year').annotate(min_id=Min('id'))
        yearcount = self.filter(year=OuterRef('year')).values('year').annotate(count=Count('id'))

        return self.filter(
            id__in=Subquery(yearid.values('min_id'))
        ).annotate(
            row_number=Window(
                expression=Sum(
                    Subquery(yearcount.values('count'), output_field=models.IntegerField())
                ),
                order_by=[F('year')],
            ) - Subquery(yearcount.values('count'), output_field=models.IntegerField())
        )

    def photo_position(self, photo):
        return self.filter(Q(year__lt=photo.year) | (Q(year=photo.year) & Q(id__lt=photo.id))).count()

    def filter_photos(self, params, user):
        return self.filter(Photo.build_query(params, user))

class Photo(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    original = models.ImageField(null=True, editable=False)
    h700 = models.ImageField(null=True, editable=False)
    thumbnail = models.ImageField(null=True, editable=False)
    donor = models.ForeignKey(Donor, models.PROTECT)
    tags = models.ManyToManyField(Tag, blank=True, through="PhotoTag")

    @classmethod
    def count(cls):
        return cls.objects.filter(is_published=True).count()

    @staticmethod
    def build_query(getparams, user):
        replacements = {
            "collection": "collection__id",
            "tag": 'phototag__tag__slug',
            'term': 'terms__slug',
            'donor': 'donor__id',
        }
        params = ("collection", "county", "city", "state", "country", 'tag', 'term', 'donor')
        merges = {
            'phototag__tag__slug': [Q(phototag__accepted=True)],
            'collection__id': [~Q(collection__visibility='PR')],
        }
        if user.is_authenticated:
            merges['collection__id'][0] |= Q(collection__owner=user)
            merges['phototag__tag__slug'][0] |= Q(phototag__creator=user)
        filtervals = (
            (replacements.get(param, param), getparams.get(param))
            for param in params
        )
        clauses = [reduce(operator.and_, [Q(**{k: v})] + merges.get(k, [])) for (k, v) in filtervals if v]

        andClauses = [Q(is_published=True), Q(year__isnull=False)]
        if clauses:
            andClauses.append(reduce(operator.or_, clauses))
        return reduce(operator.and_, andClauses)

    def get_accepted_tags(self, user=None):
        filter_args = Q(phototag__accepted=True)
        if user:
            filter_args |= Q(phototag__creator__pk=user.pk)
        return self.tags.filter(filter_args)

    def save_params(self, params):
        self.params = params

    def get_proposed_tags(self):
        return self.tags.filter(phototag__accepted=False)

    def page_number(self, queryset=None):
        if hasattr(self, 'page'):
            return self.page.number
        if queryset:
            self.row_number = queryset.photo_position(self)
        if hasattr(self, 'row_number'):
            return (self.row_number) // 10 + 1
        return 1

    def add_params(self, url, params):
        if params:
            url = '{}?{}'.format(url, params.urlencode())
        return url

    def get_json_url(self, queryset=None, params=None):
        url = reverse(
            'photoview-json',
            kwargs={'page': self.page_number(queryset=queryset), 'photo': self.accession_number},
        )
        return self.add_params(url=url, params=params or hasattr(self, 'params') and self.params)

    def get_urls(self):
        return {
            'url': self.get_absolute_url(),
            'json_url': self.get_json_url(),
        }

    def get_absolute_url(self, queryset=None, params=None):
        url = reverse(
            'photoview',
            kwargs={'page': self.page_number(queryset=queryset), 'photo': self.accession_number},
        )
        return self.add_params(url=url, params=params or hasattr(self, 'params') and self.params)

    terms = models.ManyToManyField(Term, blank=True)
    photographer = models.TextField(blank=True)
    city = models.CharField(max_length=128, blank=True)
    county = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=64, null=True, blank=True)
    year = models.SmallIntegerField(null=True, blank=True)
    caption = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    scanner = models.ForeignKey(
        Donor, null=True, on_delete=models.SET_NULL, blank=True, related_name="photos_scanned"
    )

    objects = PhotoQuerySet.as_manager()
    def __str__(self):
        return self.accession_number

    @staticmethod
    def accession2id(accession):
        if not accession.startswith('FI'):
            raise ValueError("{} doesn't start with FI", accession)
        return int(accession[2:])


    @property
    def accession_number(self):
        return 'FI' + str(self.id).zfill(7)

    def save(self, *args, **kwargs):
        if not self.thumbnail:
            image = ImageOps.exif_transpose(Image.open(BytesIO(self.original.read())))
            dims = ((75, 75), (None, 700))
            results = []
            w,h = image.size
            xoff = yoff = 0
            size = min(w, h)
            for dim in dims:
                if any(dim):
                    img = image
                    if all(dim):
                        if w > h:
                            xoff = round((w-h)/2)
                        elif h > w:
                            yoff = round((h-w)/4)
                        img = img.crop((xoff, yoff, xoff+size, yoff+size))
                    if dim[0] and not dim[1]:
                        dim = (dim[0], round(h/w*dim[0]))
                    elif dim[1] and not dim[0]:
                        dim = (round(w/h*dim[1]), dim[1])
                    img = img.resize(dim, Image.ANTIALIAS)
                    results.append(img)
            thumb, h700 = results
            fname = 'thumb/{}.jpg'.format(self.uuid)
            thumb.save(os.path.join(settings.MEDIA_ROOT, fname), "JPEG")
            self.thumbnail.name = fname
            fname = 'h700/{}.jpg'.format(self.uuid)
            h700.save(os.path.join(settings.MEDIA_ROOT, fname), "JPEG")
            self.h700.name = fname
        super().save(*args, **kwargs)


    def location(self):
        result = "Location: n/a"
        if self.city:
            result = "{}, {}".format(self.city, self.state)
        elif self.county:
            result = "{} County, {}".format(self.county, self.state)
        elif self.country:
            result = self.country
        return result


class WordCount(models.Model):
    FIELDS = [
        ('CA', 'Caption'),
        ('TA', 'Tag'),
        ('TE', 'Term'),
    ]
    photo = models.ForeignKey(Photo, models.CASCADE)
    word = models.CharField(max_length=64, blank=True)
    field = models.CharField(max_length=2, choices=FIELDS)
    count = models.FloatField()


class PhotoTag(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE)
    accepted = models.BooleanField()
    creator = models.ManyToManyField(User)


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


class CSVRecord(models.Model):
    filename = models.TextField() #unique=True)
    # unique constraint seems to make sense to me, but there are quite a few
    # duplicate records. should both be added? Or should we take newer added to
    # archive date to be the true record? Or should this be resolved on a case
    # by case basis?
    donorFirstName = models.TextField()
    donorLastName = models.TextField()
    year = models.IntegerField()
    circa = models.BooleanField()
    scanner = models.TextField()
    photographer = models.TextField()
    address = models.TextField()
    city = models.TextField()
    county = models.TextField()
    state = models.TextField()
    country = models.TextField()
    comments = models.TextField()
    added_to_archive = models.DateField()
    photo = models.OneToOneField(Photo, on_delete=models.SET_NULL, null=True)
