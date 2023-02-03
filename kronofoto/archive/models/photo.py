from django.contrib.gis.db import models
from django.db.models import Q, Window, F, Min, Subquery, Count, OuterRef, Sum, Max
from django.db.models.signals import post_delete, pre_delete
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.urls import reverse
from django.utils.http import urlencode
from datetime import datetime
import uuid
from PIL import Image, ExifTags, ImageOps
from io import BytesIO
import os
from os import path
import operator
from bisect import bisect_left
from functools import reduce
from ..storage import OverwriteStorage
from .donor import Donor
from .tag import Tag
from .term import Term
import requests
from dataclasses import dataclass
from django.core.cache import cache


bisect = lambda xs, x: min(bisect_left(xs, x), len(xs)-1)


class PhotoQuerySet(models.QuerySet):
    def year_links(self, params=None):
        year_index = self.year_index()
        years = [p.year for p in year_index]
        year_range = Photo.objects.filter(year__isnull=False, is_published=True).year_range()
        allyears = [(year, year_index[bisect(years, year)]) for year in range(year_range['start'], year_range['end']+1)]
        return [
            (year, photo.get_absolute_url(params=params))
            for (year, photo) in allyears
        ]

    def year_index(self):
        set = Photo.objects.filter(id__in=Subquery(self.values('id')))
        yearid = set.values('year').annotate(min_id=Min('id'))
        yearcount = set.filter(year=OuterRef('year')).values('year').annotate(count=Count('id'))

        return set.filter(
            id__in=Subquery(yearid.values('min_id'))
        ).annotate(
            row_number=Window(
                expression=Sum(
                    Subquery(yearcount.values('count'), output_field=models.IntegerField())
                ),
                order_by=[F('year')],
            ) - Subquery(yearcount.values('count'), output_field=models.IntegerField())
        ).order_by('year')

    def year_range(self):
        return self.aggregate(end=Max('year'), start=Min('year'))

    def photo_position(self, photo):
        return self.filter(Q(year__lt=photo.year) | (Q(year=photo.year) & Q(id__lt=photo.id))).count()

    def filter_photos(self, collection):
        return collection.filter(self.filter(year__isnull=False, is_published=True))

    def exclude_geocoded(self):
        return self.filter(location_point__isnull=True) | self.filter(location_bounds__isnull=True) | self.filter(location_from_google=True)


def format_location(force_country=False, **kwargs):
    parts = []
    if kwargs.get('address', None):
        parts.append(kwargs['address'])
    if kwargs.get('city', None):
        parts.append(kwargs['city'])
    if kwargs.get('county', None):
        parts.append('{} County'.format(kwargs['county']))
    if kwargs.get('state', None):
        parts.append(kwargs['state'])
    if (force_country or not parts) and kwargs.get('country', None):
        parts.append(kwargs['country'])
    s = ', '.join(parts)
    return s or 'Location: n/a'


def get_original_path(instance, filename):
    return path.join('original', '{}.jpg'.format(instance.uuid))


class Photo(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    original = models.ImageField(upload_to=get_original_path, storage=OverwriteStorage(), null=True, editable=True)
    h700 = models.ImageField(null=True, editable=False)
    thumbnail = models.ImageField(null=True, editable=False)
    donor = models.ForeignKey(Donor, models.PROTECT, null=True)
    tags = models.ManyToManyField(Tag, blank=True, through="PhotoTag")
    terms = models.ManyToManyField(Term, blank=True)
    photographer = models.TextField(blank=True)
    location_from_google = models.BooleanField(editable=False, default=False)
    location_point = models.PointField(null=True, srid=4326, blank=True)
    location_bounds = models.MultiPolygonField(null=True, srid=4326, blank=True)
    address = models.CharField(max_length=128, blank=True, db_index=True)
    city = models.CharField(max_length=128, blank=True, db_index=True)
    county = models.CharField(max_length=128, blank=True, db_index=True)
    state = models.CharField(max_length=64, blank=True, db_index=True)
    country = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    year = models.SmallIntegerField(null=True, blank=True, db_index=True, validators=[MinValueValidator(limit_value=1800), MaxValueValidator(limit_value=datetime.now().year)])
    circa = models.BooleanField(default=False)
    caption = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    local_context_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[RegexValidator(regex="[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", message='This should be blank or 36 alphanumerics with hyphens grouped like this: 8-4-4-4-12')],
    )
    created = models.DateTimeField(auto_now_add=True)
    scanner = models.ForeignKey(
        Donor, null=True, on_delete=models.SET_NULL, blank=True, related_name="photos_scanned"
    )

    objects = PhotoQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(is_published=False) | Q(donor__isnull=False), name="never_published_without_donor"),
        ]

    @classmethod
    def count(cls):
        return cls.objects.filter(is_published=True).count()

    def get_accepted_tags(self, user=None):
        filter_args = Q(phototag__accepted=True)
        if user:
            filter_args |= Q(phototag__creator__pk=user.pk)
        return self.tags.filter(filter_args).distinct()

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
            return self.row_number // 10 + 1
        raise AttributeError

    def add_params(self, url, params):
        if params:
            url = '{}?{}'.format(url, params.urlencode())
        return url

    def create_url(self, viewname, queryset=None, params=None):
        kwargs = {'photo': self.id}
        try:
            kwargs['page'] = self.page_number(queryset=queryset)
        except AttributeError:
            pass

        url = reverse(
            viewname,
            kwargs=kwargs,
        )
        return self.add_params(
            url=url, params=params or hasattr(self, 'params') and self.params or None
        )

    def get_download_page_url(self, params=None):
        params = params or hasattr(self, 'params') and self.params or None
        return self.add_params(
            url=reverse('kronofoto:download', kwargs=dict(pk=self.id)), params=params
        )

    def get_urls(self, embed=False):
        return {
            'url': self.get_embedded_url() if embed else self.get_absolute_url(),
        }

    def get_grid_url(self, params=None):
        page = self.row_number//settings.GRID_DISPLAY_COUNT + 1
        params = params or hasattr(self, 'params') and self.params or None
        if params:
            url = reverse('kronofoto:search-results')
            params = params.copy()
            params['page'] = page
        else:
            url = reverse('kronofoto:gridview', kwargs=dict(page=page))
        return self.add_params(url=url, params=params)


    def get_absolute_url(self, queryset=None, params=None):
        return self.create_url('kronofoto:photoview', queryset=queryset, params=params)

    def get_edit_url(self):
        return reverse('admin:archive_photo_change', args=(self.id,))

    @staticmethod
    def format_url(**kwargs):
        return "{}?{}".format(
            reverse('kronofoto:gridview'), urlencode(kwargs)
        )

    def get_county_url(self):
        return Photo.format_url(county=self.county, state=self.state)

    def get_city_url(self):
        return Photo.format_url(city=self.city, state=self.state)

    class CityIndexer:
        def index(self):
            return Photo.city_index()

    class CountyIndexer:
        def index(self):
            return Photo.county_index()

    @staticmethod
    def index_by_fields(*fields):
        return [
            {
                'name': ', '.join(p[field] for field in fields),
                'count': p['count'],
                'href': Photo.format_url(**{field: p[field] for field in fields}),
            }
            for p in Photo.objects.filter(
                is_published=True
            ).exclude(
                reduce(operator.or_, (Q(**{field: ''}) for field in fields))
            ).values(*fields).annotate(count=Count('id')).order_by(*fields)
        ]

    @staticmethod
    def county_index():
        return Photo.index_by_fields('county', 'state')

    @staticmethod
    def city_index():
        return Photo.index_by_fields('city', 'state')


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
            Image.MAX_IMAGE_PIXELS = 195670000
            filedata = self.original.read()
            # TODO: when inevitably getting "too many files open" errors during
            # imports in the future, closing the file here, as commented out
            # below, is not the correct fix. It must either be closed during the
            # import script or this must be reworked. Closing it here results in
            # runtime errors in tests and in the admin backend.
            # self.original.close()
            with ImageOps.exif_transpose(Image.open(BytesIO(filedata))) as image:
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

    def location(self, with_address=False, force_country=False):
        kwargs = dict(
            city=self.city, state=self.state, county=self.county, country=self.country
        )
        if with_address:
            kwargs['address'] = self.address
        if self.city:
            del kwargs['county']
        return format_location(force_country=force_country, **kwargs)

    def describe(self, user=None):
        terms = {str(t) for t in self.terms.all()}
        tags = {str(t) for t in self.get_accepted_tags(user)}
        location = self.location()
        location = {location} if location != "Location: n/a" else set()
        return terms | tags | location | { str(self.donor), "history of Iowa", "Iowa", "Iowa History" }

    def notices(self):
        if not self.local_context_id:
            return []
        def _():
            url = '{base}projects/{id}/'.format(base=settings.LOCAL_CONTEXTS, id=self.local_context_id)
            print(url)
            resp = requests.get(url)
            if resp.status_code == 200:
                return [
                    LocalContextNotice(
                        name=notice['name'],
                        img_url=notice['img_url'],
                        svg_url=notice['svg_url'],
                        default_text=notice['default_text'],
                    )
                    for notice in resp.json()['notice']
                ]
            else:
                return []
        return cache.get_or_set(self.local_context_id, _, timeout=24*60*60)


@dataclass
class LocalContextNotice:
    name: str
    img_url: str
    svg_url: str
    default_text: str


class PhotoTag(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE)
    accepted = models.BooleanField()
    creator = models.ManyToManyField(User, editable=False)

    def __str__(self):
        return str(self.tag)

def remove_deadtags(sender, instance, **kwargs):
    if instance.tag.phototag_set.count() == 0:
        instance.tag.delete()

def disconnect_deadtags(sender, instance, **kwargs):
    post_delete.disconnect(remove_deadtags, sender=Photo.tags.through)

def connect_deadtags(sender, instance, **kwargs):
    post_delete.connect(remove_deadtags, sender=Photo.tags.through)

post_delete.connect(remove_deadtags, sender=Photo.tags.through)
pre_delete.connect(disconnect_deadtags, sender=Tag)
post_delete.connect(connect_deadtags, sender=Tag)
