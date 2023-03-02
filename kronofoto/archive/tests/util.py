from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Photo, Donor, PhotoTag
from django.utils.text import slugify
from django.core.files.uploadedfile import SimpleUploadedFile
from hypothesis.extra.django import from_model, register_field_strategy
from hypothesis import strategies as st
from ..models.archive import Archive
from ..models.tag import Tag, LowerCaseCharField
from ..models.term import Term
from typing import NamedTuple, List

small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)
class MockPhoto(NamedTuple):
    year: int
    id: int

class MockQuerySet(list):
    def __init__(self, vals: List[MockPhoto]):
        super().__init__(vals)

    def photos_after(self, *, year, id):
        return MockQuerySet([p for p in self if p.year > year or p.year == year and p.id > id])

    def photos_before(self, *, year, id):
        return MockQuerySet(reversed([p for p in self if p.year < year or p.year == year and p.id < id]))

    def exists(self):
        return len(self) > 0



register_field_strategy(LowerCaseCharField, st.text().map(lambda s: s.lower()))

terms = lambda slug=None, **kwargs: from_model(Term)
tags = lambda slug=None, **kwargs: from_model(Tag)
donors = lambda **kwargs: from_model(Donor, **kwargs)
archives = lambda slug=None, **kwargs: from_model(Archive)

def photos(*, archive=None, **kwargs):
    return from_model(
        Photo,
        original=st.builds(
            lambda: SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        ),
        h700=st.builds(
            lambda: SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        ),
        thumbnail=st.builds(
            lambda: SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        ),
        archive=archive if archive is not None else archives(),
        **kwargs,
    )

class TestImageMixin:
    @classmethod
    def setUpClass(cls):
        cls.test_img = small_gif
        super().setUpClass()

    @classmethod
    def createPhoto(cls, is_published=True, year=1950, donor=None, archive=None, **kwargs):
        archive = archive or Archive.objects.all()[0]
        donor = donor or Donor.objects.create(last_name='last', first_name='first', archive=archive)
        return Photo.objects.create(
            original=SimpleUploadedFile(
                name='test_img.jpg',
                content=cls.test_img,
                content_type='image/jpeg',
            ),
            donor=donor,
            archive=archive,
            is_published=is_published,
            year=year,
            **kwargs,
        )
