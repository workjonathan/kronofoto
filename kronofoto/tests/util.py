from django.core.files.uploadedfile import SimpleUploadedFile
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, Bundle, initialize, consumes, precondition
from django.db import transaction
from archive.models import Photo, Donor, PhotoTag, Category
from django.utils.text import slugify
from django.core.files.uploadedfile import SimpleUploadedFile
from hypothesis.extra.django import from_model, register_field_strategy
from hypothesis import strategies as st, note
from archive.models.archive import Archive
from archive.models.tag import Tag, LowerCaseCharField
from archive.models.term import Term
from typing import NamedTuple, List
from archive.search import expression as expr

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


class TransactionalRuleBasedStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.atomic = transaction.atomic()
        self.atomic.__enter__()

    def teardown(self):
        transaction.set_rollback(True)
        self.atomic.__exit__(None, None, None)

register_field_strategy(LowerCaseCharField, st.text().map(lambda s: s.lower()))

searchTerms = st.deferred(lambda:
      st.builds(expr.IsNew, st.booleans())
    | st.builds(expr.AccessionNumber, st.integers(min_value=0))
    | st.builds(expr.YearLTE, st.integers(min_value=0))
    | st.builds(expr.YearGTE, st.integers(min_value=0))
    | st.builds(expr.YearEquals, st.integers(min_value=0))
    | st.builds(expr.UserCollection, st.uuids())
    | st.builds(expr.TagExactly, st.text())
    | st.builds(expr.State, st.text())
    | st.builds(expr.City, st.text())
    | st.builds(expr.County, st.text())
    | st.builds(expr.Country, st.text())
    #| st.builds(expr.TermExactly, st.integers(min_value=0) | st.text())
    #| st.builds(expr.DonorExactly, st.integers(min_value=0) | st.text())
    | st.builds(expr.Not, searchTerms)
    | st.builds(expr.Or, searchTerms, searchTerms)
    | st.builds(expr.Maximum, searchTerms, searchTerms)
    | st.builds(expr.And, searchTerms, searchTerms)
)

terms = lambda **kwargs: from_model(Term, id=st.none(), **kwargs)
tags = lambda **kwargs: from_model(Tag, id=st.none(), **kwargs)
archives = lambda slug=None, id=st.none(), **kwargs: from_model(Archive)
donors = lambda archive=None, id=st.none(), **kwargs: from_model(Donor, archive=archives(), **kwargs)

def photos(*, archive=None, **kwargs):
    return from_model(
        Photo,
        id=st.none(),
        original=st.builds(
            lambda: SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        ),
        archive=archive if archive is not None else archives(),
        category=from_model(Category, id=st.none()),
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
