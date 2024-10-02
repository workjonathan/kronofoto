from django.test import SimpleTestCase
from django.contrib.auth.models import User
from hypothesis.extra.django import from_model, register_field_strategy, TestCase, from_form
from hypothesis import given, strategies as st, note, settings as hsettings
from hypothesis.stateful import rule, invariant, Bundle, initialize, consumes, precondition
from hypothesis.extra.django import TestCase, from_model
from .util import TransactionalRuleBasedStateMachine, photos as gen_photos
from .models import FakeDonor, FakePhoto
from fortepan_us.kronofoto.models.donor import Donor
from fortepan_us.kronofoto.models.photo import Photo
from fortepan_us.kronofoto.models.archive import Archive
from collections import defaultdict
import pytest
from django.db.utils import IntegrityError
import unittest

class PhotoInterface:
    def test_should_have(self):
        assert hasattr(self.object, 'donor')
        assert hasattr(self.object, 'scanner')
        assert hasattr(self.object, 'photographer')
        assert hasattr(self.object, 'is_published')

class PhotoInterfaceTest(PhotoInterface, SimpleTestCase):
    def setUp(self):
        self.object = Photo

class FakePhotoInterfaceTest(PhotoInterface, SimpleTestCase):
    def setUp(self):
        self.object = FakePhoto

class DonorInterface:
    def test_should_have(self):
        assert self.object._meta.get_field('photo')
        assert self.object._meta.get_field("kronofoto_photo_scanned")
        assert self.object._meta.get_field("kronofoto_photo_photographed")

class DonorInterfaceTest(DonorInterface, SimpleTestCase):
    def setUp(self):
        self.object = Donor

class FakeDonorInterfaceTest(DonorInterface, SimpleTestCase):
    def setUp(self):
        self.object = FakeDonor

class DonorMachine(TransactionalRuleBasedStateMachine):
    donors = Bundle("donors")
    photos = Bundle("photos")

    def __init__(self):
        super().__init__()
        self.donor_model = defaultdict(set)
        self.scanner_model = defaultdict(set)
        self.photographer_model = defaultdict(set)

    @rule(target=donors, donor=from_model(FakeDonor, id=st.none()))
    def make_donor(self, donor):
        return donor

    @rule(target=photos, photo=from_model(FakePhoto, id=st.none(), year=st.just(1950), is_published=st.just(True)))
    def make_photo(self, photo):
        return photo

    @rule(donor=donors, photo=photos)
    def set_scanner(self, donor, photo):
        if photo.scanner:
            self.scanner_model[photo.scanner.pk].remove(photo.pk)
        photo.scanner = donor
        photo.save()
        self.scanner_model[donor.pk].add(photo.pk)

    @rule(donor=donors, photo=photos)
    def set_photographer(self, donor, photo):
        if photo.photographer:
            self.photographer_model[photo.photographer.pk].remove(photo.pk)
        photo.photographer = donor
        photo.save()
        self.photographer_model[donor.pk].add(photo.pk)

    @rule(donor=donors, photo=photos)
    def set_donor(self, donor, photo):
        if photo.donor:
            self.donor_model[photo.donor.pk].remove(photo.pk)
        photo.donor = donor
        photo.save()
        self.donor_model[donor.pk].add(photo.pk)

    @rule()
    def check_filter_donated(self):
        db_donors = set()
        model_donors = set()
        for donor in FakeDonor.objects.filter_donated().annotate_donatedcount():
            db_donors.add(donor.pk)
            assert len(self.donor_model[donor.pk]) == donor.donated_count
        for donor in self.donor_model:
            if len(self.donor_model[donor]) >= 1:
                model_donors.add(donor)
        assert db_donors == model_donors

    @rule()
    def check_counts(self):
        note(f"{FakeDonor.objects.count()=}")
        #qs = FakeDonor.objects.annotate_donatedcount()
        #for donor in qs:
        #    assert donor.donated_count == len(self.donor_model[donor.pk])
        qs = FakeDonor.objects.annotate_scannedcount()
        for donor in qs:
            note(f"{self.scanner_model}")
            assert donor.scanned_count == len(self.scanner_model[donor.pk])
        qs = FakeDonor.objects.annotate_photographedcount()
        for donor in qs:
            note(f"{self.photographer_model}")
            assert donor.photographed_count == len(self.photographer_model[donor.pk])

DonorMachine.TestCase.settings = hsettings(max_examples = 5, stateful_step_count = 5, deadline=None)

class TestDonorQuerySet(TestCase, DonorMachine.TestCase):
    pass

@pytest.mark.django_db
def test_donor_requires_archive():
    with pytest.raises(IntegrityError):
        Donor.objects.create(archive=None)

@pytest.mark.django_db
def test_donor_only_requires_archive():
    archive = Archive.objects.create()
    donor = Donor.objects.create(archive=archive)
    donor.clean_fields()
