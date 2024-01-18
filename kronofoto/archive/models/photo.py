from django.contrib.gis.db import models
import base64
import json
from django.http import QueryDict
from django.core.signing import Signer
from django.db import transaction
from django.db.models import Q, Window, F, Min, Subquery, Count, OuterRef, Sum, Max
from django.db.models.functions import Lower
from django.db.models.signals import post_delete, pre_delete
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.files.uploadedfile import InMemoryUploadedFile
from ..reverse import reverse
from django.utils.http import urlencode
from datetime import datetime
import uuid
from PIL import Image, ExifTags, ImageOps, UnidentifiedImageError
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
from .archive import Archive
from .category import Category
from .place import Place
import requests
from dataclasses import dataclass
from django.core.cache import cache

bisect = lambda xs, x: min(bisect_left(xs, x), len(xs)-1)

class PhotoQuerySet(models.QuerySet):
    def year_range(self):
        return self.aggregate(end=Max('year'), start=Min('year'))

    def photo_position(self, photo):
        return self.filter(Q(year__lt=photo.year) | (Q(year=photo.year) & Q(id__lt=photo.id))).count()

    def filter_photos(self, collection):
        return collection.filter(self.filter(year__isnull=False, is_published=True))

    def photos_before(self, *, year: int, id: int):
        photos = self.filter(Q(year__lt=year) | Q(year=year, id__lt=id)).order_by('-year', '-id')
        return photos


    def photos_after(self, *, year: int, id: int) -> "PhotoQuerySet":
        photos = self.filter(Q(year__gt=year) | Q(year=year, id__gt=id)).order_by('year', 'id')
        return photos

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
    created = datetime.now() if instance.created is None else instance.created
    return path.join(
        'original',
        str(created.year),
        str(created.month),
        str(created.day),
        '{}.jpg'.format(instance.uuid)
    )

def get_submission_path(instance, filename):
    return path.join('submissions', '{}.jpg'.format(instance.uuid))

@dataclass
class PlaceData:
    address: str
    city: str
    county: str
    state: str
    country: str

    def get_query(self):
        parts = []
        if self.city:
            parts.append('city:"{}"'.format(self.city))
        if not self.city and self.county:
            parts.append('county:"{}"'.format(self.county))
        if self.state:
            parts.append('state:"{}"'.format(self.state))
        if self.country:
            parts.append('country:"{}"'.format(self.country))

        return " AND ".join(parts)

class PhotoBase(models.Model):
    archive = models.ForeignKey(Archive, models.PROTECT, null=False)
    category = models.ForeignKey(Category, models.PROTECT, null=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    donor = models.ForeignKey(Donor, models.PROTECT, null=True)
    terms = models.ManyToManyField(Term, blank=True)
    photographer = models.ForeignKey(
        Donor, models.PROTECT, null=True, blank=True, related_name="%(app_label)s_%(class)s_photographed",
    )
    address = models.CharField(max_length=128, blank=True, db_index=True)
    city = models.CharField(max_length=128, blank=True, db_index=True)
    county = models.CharField(max_length=128, blank=True, db_index=True)
    state = models.CharField(max_length=64, blank=True, db_index=True)
    country = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    place = models.ForeignKey(
        Place, models.PROTECT, null=True, blank=True, related_name="%(app_label)s_%(class)s_place"
    )
    year = models.SmallIntegerField(null=True, blank=True, db_index=True, validators=[MinValueValidator(limit_value=1800), MaxValueValidator(limit_value=datetime.now().year)])
    circa = models.BooleanField(default=False)
    caption = models.TextField(blank=True, verbose_name="comment")

    scanner = models.ForeignKey(
        Donor, null=True, on_delete=models.SET_NULL, blank=True, related_name="%(app_label)s_%(class)s_scanned",
    )

    def get_place(self, with_address=False):
        return PlaceData(
            address=self.address,
            city=self.city,
            county=self.county,
            state=self.state,
            country=self.country,
        )

    @property
    def place_query(self):
        return self.get_place().get_query()

    def location(self, with_address=False, force_country=False):
        kwargs = dict(
            city=self.city, state=self.state, county=self.county, country=self.country
        )
        if with_address:
            kwargs['address'] = self.address
        if self.city:
            del kwargs['county']
        return format_location(force_country=force_country, **kwargs)

    class Meta:
        abstract = True

class Submission(PhotoBase):
    image = models.ImageField(upload_to=get_submission_path, null=False)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)

    def __str__(self):
        location = self.location()
        if self.year:
            return "{} - {}".format(self.year, location)
        return location

class ResizerBase:

    def resize(self, *, image):
        img = self.crop_image(image=image)
        return img.resize(
            (self.output_width, self.output_height),
            Image.LANCZOS,
        )

@dataclass
class FixedHeightResizer(ResizerBase):
    height: int
    original_width: int
    original_height: int

    def crop_image(self, *, image):
        return image

    @property
    def output_height(self):
        return self.height

    @property
    def output_width(self):
        return round(self.original_width * self.height / self.original_height)

@dataclass
class FixedWidthResizer(ResizerBase):
    width: int
    original_width: int
    original_height: int

    def crop_image(self, *, image):
        return image

    @property
    def output_height(self):
        return round(self.original_height * self.width / self.original_width)

    @property
    def output_width(self):
        return self.width

@dataclass
class FixedResizer(ResizerBase):
    width: int
    height: int
    original_width: int
    original_height: int

    @property
    def crop_coords(self):
        original_origin_x = self.original_width / 2
        original_origin_y = self.original_height / 4
        output_ratio = self.width/self.height
        adjusted_output_width = min(self.original_width, self.original_height * output_ratio)
        adjusted_output_height = min(self.original_height, self.original_width / output_ratio)
        adjusted_origin_x = adjusted_output_width / 2
        adjusted_origin_y = adjusted_output_height / 4
        xoff = original_origin_x - adjusted_origin_x
        yoff = original_origin_y - adjusted_origin_y
        return (xoff, yoff, xoff+adjusted_output_width, yoff+adjusted_output_height)

    def crop_image(self, *, image):
        return image.crop(self.crop_coords)

    @property
    def output_height(self):
        return self.height

    @property
    def output_width(self):
        return self.width

@dataclass
class ImageData:
    height: int
    width: int
    url: str
    name: str

class Photo(PhotoBase):
    original = models.ImageField(upload_to=get_original_path, storage=OverwriteStorage(), null=True, editable=True)
    h700 = models.ImageField(null=True, editable=False)
    @property
    def h700(self):
        block1 = self.id & 255
        block2 = (self.id >> 8) & 255
        signer = Signer(salt="{}/{}".format(block1, block2))
        profile = signer.sign_object({
            "height": 700,
            "path": self.original.name,
        })
        return ImageData(
            height=700,
            width=round(self.original.width*700/self.original.height),
            url=reverse("kronofoto:resize-image", kwargs={'block1': block1, 'block2': block2, 'profile1': profile.split(':')[0], 'profile2': profile.split(":")[1]}),
            name="thumbnail",
        )
    thumbnail = models.ImageField(null=True, editable=False)
    @property
    def thumbnail(self):
        block1 = self.id & 255
        block2 = (self.id >> 8) & 255
        signer = Signer(salt="{}/{}".format(block1, block2))
        profile = signer.sign_object({
            "height": 75,
            "width": 75,
            "path": self.original.name,
        })
        return ImageData(
            height=75,
            width=75,
            url=reverse("kronofoto:resize-image", kwargs={'block1': block1, 'block2': block2, 'profile1': profile.split(':')[0], 'profile2': profile.split(":")[1]}),
            name="thumbnail",
    )
    tags = models.ManyToManyField(Tag, db_index=True, blank=True, through="PhotoTag")
    location_from_google = models.BooleanField(editable=False, default=False)
    location_point = models.PointField(null=True, srid=4326, blank=True)
    location_bounds = models.MultiPolygonField(null=True, srid=4326, blank=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False, db_index=True)
    local_context_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[RegexValidator(regex="[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", message='This should be blank or 36 alphanumerics with hyphens grouped like this: 8-4-4-4-12')],
    )
    created = models.DateTimeField(auto_now_add=True)

    objects = PhotoQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(is_published=False) | Q(donor__isnull=False), name="never_published_without_donor"),
        ]
        indexes = (
            models.Index(fields=['year', 'is_published']),
        )

    def page_number(self):
        return {'year:gte': self.year, 'id:gt': self.id-1}

    def get_all_tags(self, user=None):
        "Return a list of tag and term objects, annotated with label and label_lower for label and sorting."
        tags = self.get_accepted_tags(user=user).annotate(label_lower=Lower("tag"), label=models.F("tag"))
        terms = self.terms.annotate(label_lower=Lower("term"), label=models.F("term"))
        return list(tags) + list(terms)


    def get_accepted_tags(self, user=None):
        query = Q(phototag__accepted=True)
        if user:
            query |= Q(phototag__creator__pk=user.pk)
        return self.tags.filter(query)

    def get_proposed_tags(self):
        return self.tags.filter(phototag__accepted=False)

    def add_params(self, url, params):
        if params:
            url = '{}?{}'.format(url, params.urlencode())
        return url

    def create_url(self, viewname, queryset=None, params=None):
        kwargs = {'photo': self.id}
        url = reverse(
            viewname,
            kwargs=kwargs,
        )
        return self.add_params(url=url, params=params)

    def get_download_page_url(self, kwargs=None, params=None):
        kwargs = kwargs or {}
        url = reverse('kronofoto:download', kwargs=dict(**kwargs, **{'pk': self.id}))
        if params:
            params = params.copy()
        else:
            params = QueryDict(mutable=True)
        return self.add_params(url=url, params=params)

    def get_urls(self, embed=False):
        return {
            'url': self.get_embedded_url() if embed else self.get_absolute_url(),
        }

    def get_grid_url(self, kwargs=None, params=None):
        kwargs = kwargs or {}
        url = reverse('kronofoto:gridview', kwargs=kwargs)
        if params:
            params = params.copy()
        else:
            params = QueryDict(mutable=True)
        params['year:gte'] = self.year
        params['id:gt'] = self.id - 1
        return self.add_params(url=url, params=params)


    def get_absolute_url(self, kwargs=None, params=None):
        kwargs = kwargs or {}
        kwargs = dict(**kwargs)
        kwargs['photo'] = self.id
        url = reverse('kronofoto:photoview', kwargs=kwargs)
        if params:
            return '{}?{}'.format(url, params.urlencode())
        return url

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


    @property  # type: ignore[misc]
    def accession_number(self):
        return 'FI' + str(self.id).zfill(7)

    def resizer(self, *, size, original_width, original_height):
        if size == 'thumbnail':
            return FixedResizer(width=75, height=75, original_width=original_width, original_height=original_height)
        elif size == 'h700':
            return FixedHeightResizer(height=700, original_width=original_width, original_height=original_height)

    @dataclass
    class Saver:
        uuid: uuid
        path: str

        def save(self, *, image):
            fname = self.format_path()
            image.save(os.path.join(settings.MEDIA_ROOT, fname), "JPEG")
            return fname

        def format_path(self):
            return self.path.format(self.uuid)


    def saver(self, *, size, uuid):
        if size == 'thumbnail':
            return Photo.Saver(uuid=uuid, path='thumb/{}.jpg')
        elif size == 'h700':
            return Photo.Saver(uuid=uuid, path="h700/{}.jpg")

    #def save(self, *args, **kwargs):
    #    if not self.thumbnail:
    #        Image.MAX_IMAGE_PIXELS = 195670000
    #        filedata = self.original.read()
    #        # TODO: when inevitably getting "too many files open" errors during
    #        # imports in the future, closing the file here, as commented out
    #        # below, is not the correct fix. It must either be closed during the
    #        # import script or this must be reworked. Closing it here results in
    #        # runtime errors in tests and in the admin backend.
    #        # self.original.close()
    #        with ImageOps.exif_transpose(Image.open(BytesIO(filedata))) as image:
    #            w, h = image.size
    #            sizes = ["thumbnail", "h700"]
    #            for size in sizes:
    #                resizer = self.resizer(size=size, original_height=h, original_width=w)
    #                img = resizer.resize(image=image)

    #                saver = self.saver(size=size, uuid=self.uuid)
    #                getattr(self, size).name = saver.save(image=img)
    #    super().save(*args, **kwargs)


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

def get_resized_path(instance, filename):
    return path.join('resized', '{}_{}_{}.jpg'.format(instance.width, instance.height, instance.photo.uuid))

class SizedPhotoQuerySet(models.QuerySet):
    def get_or_create_fixed_height(self, *, photo, height):
        with transaction.atomic():
            try:
                return self.get(photo=photo, height=height, cropped=False), False
            except ObjectDoesNotExist:
                Image.MAX_IMAGE_PIXELS = 195670000
                filedata = photo.original.read()
                with ImageOps.exif_transpose(Image.open(BytesIO(filedata))) as image:
                    (w, h) = image.size
                    resizer = FixedHeightResizer(height=height, original_width=w, original_height=h)
                    img = resizer.resize(image=image)
                    fp = BytesIO()
                    img.save(fp, "JPEG")
                    file = InMemoryUploadedFile(fp, None, f"fixed_height_{photo.id}", "image/jpeg", fp.getbuffer().nbytes, None, None)
                    return self.update_or_create(photo=photo, width=resizer.output_width, height=resizer.output_height, defaults={"cropped": False, "image":file})

    def get_or_create_thumb(self, *, photo, width, height):
        with transaction.atomic():
            try:
                return self.get(photo=photo, width=width, height=height), False
            except ObjectDoesNotExist:
                Image.MAX_IMAGE_PIXELS = 195670000
                filedata = photo.original.read()
                with ImageOps.exif_transpose(Image.open(BytesIO(filedata))) as image:
                    (w, h) = image.size
                    resizer = FixedResizer(width=width, height=height, original_width=w, original_height=h)
                    img = resizer.resize(image=image)
                    fp = BytesIO()
                    img.save(fp, "JPEG")
                    file = InMemoryUploadedFile(fp, None, f"thumb_{photo.id}", "image/jpeg", fp.getbuffer().nbytes, None, None)
                    return self.create(photo=photo, width=resizer.output_width, height=resizer.output_height, cropped=True, image=file), True


class SizedPhoto(models.Model):
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE)
    width = models.IntegerField()
    height = models.IntegerField()
    cropped = models.BooleanField()
    image = models.ImageField(upload_to=get_resized_path)

    objects = SizedPhotoQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['photo', 'width', 'height'], name='unique_photo_size'),
        ]
        indexes = [
            models.Index(fields=['photo', 'width', 'height']),
            models.Index(fields=['photo', 'width', 'cropped']),
        ]


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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tag', 'photo'], name='unique_tag_photo'),
        ]
        indexes = [
            models.Index(fields=['tag', 'photo']),
        ]

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
