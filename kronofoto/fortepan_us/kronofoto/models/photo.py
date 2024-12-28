from django.contrib.gis.db import models
import base64
import json
from django.core.files.storage import default_storage
from django.http import QueryDict
from django.core.signing import Signer
from django.db import transaction
from django.db.models import Q, Window, F, Min, Subquery, Count, OuterRef, Sum, Max, QuerySet
from django.db.models.functions import Lower
from django.db.models.signals import post_delete, pre_delete
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.files.uploadedfile import InMemoryUploadedFile
from fortepan_us.kronofoto.reverse import reverse
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
from fortepan_us.kronofoto.storage import OverwriteStorage
from .donor import Donor
from .tag import Tag, TagQuerySet
from .term import Term
from .archive import Archive
from .category import Category
from .place import Place
import requests
from dataclasses import dataclass
from django.core.cache import cache
from typing import Dict, Any, List, Optional, Set, Tuple, Protocol, overload, TypedDict, Callable, Iterable
from typing_extensions import Self
from fortepan_us.kronofoto.imageutil import ImageSigner
from itertools import chain, cycle, islice
from typing import Dict, Any, List, Optional, Set, Tuple, Protocol
from typing_extensions import Self
from .activity_dicts import ActivitypubImage

EMPTY_PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
bisect = lambda xs, x: min(bisect_left(xs, x), len(xs)-1)

class Thumbnail(TypedDict):
    url: str
    height: int
    width: int


EMPTY_THUMBNAIL = Thumbnail(url=EMPTY_PNG, height=75, width=75)


class PhotoQuerySet(models.QuerySet['Photo']):
    def year_range(self) -> Dict[str, Any]:
        return self.aggregate(end=Max('year'), start=Min('year'))

    def photo_position(self, photo: "Photo") -> int:
        return self.filter(Q(year__lt=photo.year) | (Q(year=photo.year) & Q(id__lt=photo.id))).count()

    def photos_before(self, *, year: int, id: int) -> Self:
        photos = self.filter(Q(year__lt=year) | Q(year=year, id__lt=id)).order_by('-year', '-id')
        return photos


    def photos_after(self, *, year: int, id: int) -> Self:
        photos = self.filter(Q(year__gt=year) | Q(year=year, id__gt=id)).order_by('year', 'id')
        return photos

    def exclude_geocoded(self) -> Self:
        return self.filter(location_point__isnull=True) | self.filter(location_bounds__isnull=True) | self.filter(location_from_google=True)


def format_location(force_country:bool=False, **kwargs: str) -> str:
    parts = []
    if kwargs.get('address', None):
        parts.append(kwargs['address'])
    if kwargs.get('city', None):
        parts.append(kwargs['city'])
    if kwargs.get('county', None):
        parts.append('{} County'.format(kwargs['county']))
    if kwargs.get('state', None):
        parts.append(kwargs['state'])
    if (force_country or not parts) and 'country' in kwargs:
        parts.append(kwargs['country'])
    s = ', '.join(parts)
    return s or 'Location: n/a'


def get_original_path(instance: "Photo", filename: str) -> str:
    created = datetime.now() if instance.created is None else instance.created
    return path.join(
        'original',
        str(created.year),
        str(created.month),
        str(created.day),
        '{}.jpg'.format(instance.uuid)
    )

def get_submission_path(instance: "Submission", filename: str) -> str:
    return path.join('submissions', '{}.jpg'.format(instance.uuid))

@dataclass
class PlaceData:
    address: str
    city: str
    county: str
    state: str
    country: str

    def get_query(self) -> str:
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
    archive = models.ForeignKey(Archive, on_delete=models.PROTECT, null=False)
    category = models.ForeignKey(Category, models.PROTECT, null=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    donor = models.ForeignKey(Donor, models.PROTECT, null=True)
    terms = models.ManyToManyField(Term, blank=True)
    photographer = models.ForeignKey(
        Donor, models.PROTECT, null=True, blank=True, related_name="%(app_label)s_%(class)s_photographed",
    )
    address = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=128, blank=True)
    county = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=64, null=True, blank=True)
    place = models.ForeignKey(
        Place, models.PROTECT, null=True, blank=True, related_name="%(app_label)s_%(class)s_place"
    )
    location_point = models.PointField(null=True, srid=4326, blank=True)
    year = models.SmallIntegerField(null=True, blank=True, db_index=True, validators=[MinValueValidator(limit_value=1800), MaxValueValidator(limit_value=datetime.now().year)])
    circa = models.BooleanField(default=False)
    caption = models.TextField(blank=True, verbose_name="comment")

    scanner = models.ForeignKey(
        Donor, null=True, on_delete=models.SET_NULL, blank=True, related_name="%(app_label)s_%(class)s_scanned",
    )

    def get_place(self, with_address: bool=False) -> PlaceData:
        return PlaceData(
            address=self.address,
            city=self.city,
            county=self.county,
            state=self.state,
            country=self.country or "",
        )

    @property
    def place_query(self) -> str:
        return self.get_place().get_query()

    def location(self, with_address: bool=False, force_country: bool=False) -> str:
        kwargs : Dict[str, str] = dict(
            city=self.city, state=self.state, county=self.county,
        )
        if self.country:
            kwargs['country'] = self.country
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

    def __str__(self) -> str:
        location = self.place
        stuff = [str(self.donor)]
        if self.year:
            stuff.append(str(self.year))
        if location:
            stuff.append(location.fullname)
        return ' - '.join(stuff)

class ResizerBase(Protocol):
    @property
    def output_height(self) -> int:
        ...
    @property
    def output_width(self) -> int:
        ...
    def crop_image(self, *, image: Image.Image) -> Image.Image:
        ...

    def resize(self, *, image: Image.Image) -> Image.Image:
        image = self.crop_image(image=image)
        return image.resize(
            (self.output_width, self.output_height),
            Image.Resampling.LANCZOS,
        )

@dataclass
class FixedHeightResizer(ResizerBase):
    height: int
    original_width: int
    original_height: int

    def crop_image(self, *, image: Image.Image) -> Image.Image:
        return image

    @property
    def output_height(self) -> int:
        return self.height

    @property
    def output_width(self) -> int:
        return round(self.original_width * self.height / self.original_height)

@dataclass
class FixedWidthResizer(ResizerBase):
    width: int
    original_width: int
    original_height: int

    def crop_image(self, *, image: Image.Image) -> Image.Image:
        return image

    @property
    def output_height(self) -> int:
        return round(self.original_height * self.width / self.original_width)

    @property
    def output_width(self) -> int:
        return self.width

@dataclass
class FixedResizer(ResizerBase):
    width: int
    height: int
    original_width: int
    original_height: int

    @property
    def crop_coords(self) -> Tuple[int, int, int, int]:
        original_origin_x = self.original_width / 2
        original_origin_y = self.original_height / 4
        output_ratio = self.width/self.height
        adjusted_output_width = min(self.original_width, self.original_height * output_ratio)
        adjusted_output_height = min(self.original_height, self.original_width / output_ratio)
        adjusted_origin_x = adjusted_output_width / 2
        adjusted_origin_y = adjusted_output_height / 4
        xoff = round(original_origin_x - adjusted_origin_x)
        yoff = round(original_origin_y - adjusted_origin_y)
        return (xoff, yoff, round(xoff+adjusted_output_width), round(yoff+adjusted_output_height))

    def crop_image(self, *, image: Image.Image) -> Image.Image:
        return image.crop(self.crop_coords)

    @property
    def output_height(self) -> int:
        return self.height

    @property
    def output_width(self) -> int:
        return self.width

@dataclass
class ImageData:
    height: int
    width: int
    url: str
    name: str

class Photo(PhotoBase):
    original = models.ImageField(upload_to=get_original_path, storage=OverwriteStorage(), null=True, editable=True)
    remote_image = models.URLField(null=True, editable=False)
    places = models.ManyToManyField("kronofoto.Place", editable=False)
    original_height = models.IntegerField(default=0, editable=False)
    original_width = models.IntegerField(default=0, editable=False)

    @overload
    def image_url(self, *, height: int) -> str:
        ...
    @overload
    def image_url(self, *, height: Optional[int]=None, width: int) -> str:
        ...
    def image_url(self, *, height: Optional[int]=None, width: Optional[int]=None) -> str:
        assert height is not None or width is not None

        if self.remote_image is None:
            path = self.original.name
        else:
            path = (0, self.remote_image)
        return ImageSigner(id=self.id, path=path, width=width, height=height).url

    @property
    def h700(self) -> Optional[ImageData]:
        from fortepan_us.kronofoto.imageutil import ImageSigner
        if not self.original or not self.id:
            return None
        signer = ImageSigner(id=self.id, path=self.original.name, width=0, height=700)
        return ImageData(
            height=700,
            width=self.original.width/self.original.height*700,
            url=signer.url,
            name="h700",
        )
    @property
    def thumbnail(self) -> Optional[ImageData]:
        if not self.original or not self.id:
            return None
        from fortepan_us.kronofoto.imageutil import ImageSigner
        signer = ImageSigner(id=self.id, path=self.original.name, width=75, height=75)
        return ImageData(
            height=75,
            width=75,
            url=signer.url,
            name="thumbnail",
        )

    tags = models.ManyToManyField(Tag, db_index=True, blank=True, through="kronofoto.PhotoTag")
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False, db_index=True)
    local_context_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[RegexValidator(regex="[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", message='This should be blank or 36 alphanumerics with hyphens grouped like this: 8-4-4-4-12')],
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = PhotoQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(is_published=False) | Q(donor__isnull=False), name="never_published_without_donor"),
        ]
        indexes = (
            models.Index(fields=['archive', 'id']),
            models.Index(fields=['year', 'id'], condition=Q(is_published=True, year__isnull=False), name="year_id_sort"),
            models.Index(fields=['donor_id', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="donor_year_id_sort"),
            models.Index(fields=['donor_id', 'category', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="d_category_year_id_sort"),
            models.Index(fields=['donor_id', 'archive', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="d_archive_year_id_sort"),
            models.Index(fields=['donor_id', 'category', 'archive', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="d_category_archive_year_id_s"),
            models.Index(fields=['category', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="category_year_id_sort"),
            models.Index(fields=['archive', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="archive_year_id_sort"),
            models.Index(fields=['category', 'archive', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="category_archive_year_id_sort"),
            models.Index(fields=['place_id', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="pyear_id_sort"),
            models.Index(fields=['donor_id', 'place_id', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="donor_pyear_id_sort"),
            models.Index(fields=['donor_id', 'category', 'place_id', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="d_category_pyear_id_sort"),
            models.Index(fields=['donor_id', 'archive', 'place_id', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="d_archive_pyear_id_sort"),
            models.Index(fields=['donor_id', 'category', 'archive', 'place_id', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="d_category_archive_pyear_id_s"),
            models.Index(fields=['category', 'place_id', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="category_pyear_id_sort"),
            models.Index(fields=['archive', 'place_id', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="archive_pyear_id_sort"),
            models.Index(fields=['category', 'archive', 'place_id', 'year', 'id'], condition=Q(is_published=True, year__isnull=False), name="category_archive_pyear_id_sort"),
        )

    def reconcile(self, object: ActivitypubImage, donor: Donor) -> None:
        self.caption = object['content']
        self.donor = donor
        self.year = object['year']
        self.circa = object['circa']
        self.is_published = object['is_published']
        self.donor = donor
        self.remote_image = object['url']
        self.category, _ = Category.objects.get_or_create(
            slug=object['category']['slug'],
            defaults={"name": object['category']['name']},
        )
        self.save()

    @property
    def activity_dict(self) -> Dict[str, Any]:
        return {
            "id": reverse("kronofoto:activitypub-photo", kwargs={"short_name": self.archive.slug, "pk": self.id}),
            "type": "Image",
            "attributedTo": [reverse("kronofoto:activitypub-archive", kwargs={"short_name": self.archive.slug})],
            "content": self.caption,
            "url": self.original.url,
        }
    def page_number(self) -> Dict[str, Optional[int]]:
        return {'year:gte': self.year, 'id:gt': self.id-1}

    def get_all_tags(self, user: Optional[User]=None) -> List[str]:
        "Return a list of tag and term objects, annotated with label and label_lower for label and sorting."
        tags = self.get_accepted_tags(user=user).annotate(label_lower=Lower("tag"), label=models.F("tag"))
        terms = self.terms.annotate(label_lower=Lower("term"), label=models.F("term"))
        return list(tags) + list(terms)


    def get_accepted_tags(self, user: Optional[User]=None) -> TagQuerySet:
        query = Q(phototag__accepted=True)
        if user:
            query |= Q(phototag__creator__pk=user.pk)
        return self.tags.filter(query)

    def get_proposed_tags(self) -> TagQuerySet:
        return self.tags.filter(phototag__accepted=False)

    def add_params(self, url: str, params: Optional[QueryDict]) -> str:
        if params:
            url = '{}?{}'.format(url, params.urlencode())
        return url

    def create_url(self, viewname: str, queryset: Optional[int]=None, params: Optional[QueryDict]=None) -> str:
        kwargs = {'photo': self.id}
        url = reverse(
            viewname,
            kwargs=kwargs,
        )
        return self.add_params(url=url, params=params)

    def get_download_page_url(self, kwargs: Optional[Dict[str, Any]]=None, params: Optional[QueryDict]=None) -> str:
        kwargs = kwargs or {}
        url = reverse('kronofoto:download', kwargs=dict(**kwargs, **{'pk': self.id}))
        if params:
            params = params.copy()
        else:
            params = QueryDict(mutable=True)
        return self.add_params(url=url, params=params)

    def get_urls(self, embed: bool=False) -> Dict[str, str]:
        return {
            'url': self.get_absolute_url(),
        }

    def get_grid_url(self, kwargs: Optional[Dict[str, Any]]=None, params: Optional[QueryDict]=None) -> str:
        if self.year:
            kwargs = kwargs or {}
            url = reverse('kronofoto:gridview', kwargs=kwargs)
            if params:
                params = params.copy()
            else:
                params = QueryDict(mutable=True)
            params['year:gte'] = str(self.year)
            params['id:gt'] = str(self.id - 1)
            return self.add_params(url=url, params=params)
        raise ValueError("Photo.year must be set")


    def get_absolute_url(self, kwargs: Optional[Dict[str, Any]]=None, params: Optional[QueryDict]=None) -> str:
        kwargs = kwargs or {}
        kwargs = dict(**kwargs)
        kwargs['photo'] = self.id
        url = reverse('kronofoto:photoview', kwargs=kwargs)
        if params:
            return '{}?{}'.format(url, params.urlencode())
        return url

    def get_edit_url(self) -> str:
        return reverse('admin:kronofoto_photo_change', args=(self.id,))

    @staticmethod
    def format_url(**kwargs: Any) -> str:
        return "{}?{}".format(
            reverse('kronofoto:gridview'), urlencode(kwargs)
        )

    def get_county_url(self) -> str:
        return Photo.format_url(county=self.county, state=self.state)

    def get_city_url(self) -> str:
        return Photo.format_url(city=self.city, state=self.state)

    class CityIndexer:
        def index(self) -> List[Dict[str, Any]]:
            return Photo.city_index()

    class CountyIndexer:
        def index(self) -> List[Dict[str, Any]]:
            return Photo.county_index()

    @staticmethod
    def index_by_fields(*fields: str) -> List[Dict[str, Any]]:
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
    def county_index() -> List[Dict[str, Any]]:
        return Photo.index_by_fields('county', 'state')

    @staticmethod
    def city_index() -> List[Dict[str, Any]]:
        return Photo.index_by_fields('city', 'state')


    def __str__(self) -> str:
        return self.accession_number

    @staticmethod
    def accession2id(accession: str) -> int:
        if not accession.startswith('FI'):
            raise ValueError("{} doesn't start with FI", accession)
        return int(accession[2:])


    @property
    def accession_number(self) -> str:
        return 'FI' + str(self.id).zfill(7)

    def resizer(self, *, size: int, original_width: int, original_height: int) -> ResizerBase:
        if size == 'thumbnail':
            return FixedResizer(width=75, height=75, original_width=original_width, original_height=original_height)
        elif size == 'h700':
            return FixedHeightResizer(height=700, original_width=original_width, original_height=original_height)
        raise NotImplementedError

    @dataclass
    class Saver:
        uuid: uuid.UUID
        path: str

        def save(self, *, image: Image.Image) -> str:
            fname = self.format_path()
            image.save(os.path.join(settings.MEDIA_ROOT, fname), "JPEG")
            return fname

        def format_path(self) -> str:
            return self.path.format(self.uuid)


    def saver(self, *, size: int, uuid: uuid.UUID) -> Saver:
        if size == 'thumbnail':
            return Photo.Saver(uuid=uuid, path='thumb/{}.jpg')
        elif size == 'h700':
            return Photo.Saver(uuid=uuid, path="h700/{}.jpg")
        raise NotImplementedError

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


    def describe(self, user: Optional[User]=None) -> Set[str]:
        terms = {str(t) for t in self.terms.all()}
        tags = {str(t) for t in self.get_accepted_tags(user)}
        location = self.location()
        locations = {location} if location != "Location: n/a" else set()
        return terms | tags | locations | { str(self.donor), "history of Iowa", "Iowa", "Iowa History" }

    def notices(self) -> List["LocalContextNotice"]:
        if not self.local_context_id:
            return []
        def _() -> List[LocalContextNotice]:
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
        val = cache.get_or_set(self.local_context_id, _, timeout=24*60*60)
        if val and isinstance(val, list):
            return val
        else:
            return []

def get_resized_path(instance: Any, filename: str) -> str:
    return path.join('resized', '{}_{}_{}.jpg'.format(instance.width, instance.height, instance.photo.uuid))


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


    def __str__(self) -> str:
        return str(self.tag)

def remove_deadtags(sender: Any, instance: Tag, **kwargs: Any) -> None:
    if instance.tag.phototag_set.count() == 0:
        instance.tag.delete()

def disconnect_deadtags(*args: Any, **kwargs: Any) -> None:
    post_delete.disconnect(remove_deadtags, sender=Photo.tags.through)

def connect_deadtags(*args: Any, **kwargs: Any) -> None:
    post_delete.connect(remove_deadtags, sender=Photo.tags.through)

post_delete.connect(remove_deadtags, sender=Photo.tags.through)
pre_delete.connect(disconnect_deadtags, sender=Tag)
post_delete.connect(connect_deadtags, sender=Tag)

@dataclass
class PhotoPlaceholder:
    thumbnail: Thumbnail
    is_spacer: bool
    photo: Photo

    def get_absolute_url(self, *args: Any, **kwargs: Any) -> str:
        return self.photo.get_absolute_url(*args, **kwargs)

    @property
    def id(self) -> int:
        return self.photo.id

    @property
    def year(self) -> Optional[int]:
        return self.photo.year

@dataclass
class CarouselList:
    queryset: QuerySet

    @property
    def keyset(self) -> QuerySet:
        raise NotImplementedError

    @property
    def wrapped_queryset(self) -> QuerySet:
        raise NotImplementedError

    def carousel_list(self, *, item_count: int, func: Optional[Callable]=None) -> List[Photo]:
        keyset: Iterable = self.keyset[:item_count]
        if func:
            keyset = [func(item) for item in keyset]
        wrapped_qs = self.wrapped_queryset
        cycling = cycle(
            PhotoPlaceholder(
                thumbnail=EMPTY_THUMBNAIL,
                is_spacer=True,
                photo=func(photo) if func else photo,
            ) for photo in wrapped_qs[:item_count]
        )
        looping = chain(keyset, cycling)
        return list(islice(looping, item_count))

@dataclass
class BackwardList(CarouselList):
    queryset: PhotoQuerySet
    year: int
    id: int

    @property
    def keyset(self) -> PhotoQuerySet:
        return self.queryset.photos_before(year=self.year, id=self.id)

    @property
    def wrapped_queryset(self) -> PhotoQuerySet:
        return self.queryset.order_by('-year', '-id')

@dataclass
class ForwardList(CarouselList):
    queryset: PhotoQuerySet
    year: int
    id: int

    @property
    def keyset(self) -> PhotoQuerySet:
        return self.queryset.photos_after(year=self.year, id=self.id)

    @property
    def wrapped_queryset(self) -> PhotoQuerySet:
        return self.queryset
