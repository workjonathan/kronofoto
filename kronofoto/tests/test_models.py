from django.test import SimpleTestCase
from django.contrib.auth.models import User
from hypothesis.extra.django import from_model, register_field_strategy, TestCase, from_form
from hypothesis import given, strategies as st, note, settings as hsettings
from hypothesis.stateful import rule, invariant, Bundle, initialize, consumes, precondition
from hypothesis.extra.django import TestCase, from_model
from .util import TransactionalRuleBasedStateMachine, photos as gen_photos
from .models import FakeDonor, FakePhoto
from archive.models.donor import Donor
from archive.models.photo import Photo
from archive.models.archive import Archive
from collections import defaultdict

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
        assert self.object._meta.get_field("archive_photo_scanned")
        assert self.object._meta.get_field("archive_photo_photographed")
        assert hasattr(self.object, 'users_starred_by')

class DonorInterfaceTest(DonorInterface, SimpleTestCase):
    def setUp(self):
        self.object = Donor

class FakeDonorInterfaceTest(DonorInterface, SimpleTestCase):
    def setUp(self):
        self.object = FakeDonor

class DonorStarMachine(TransactionalRuleBasedStateMachine):
    donors = Bundle("donors")
    users = Bundle("users")

    def __init__(self):
        super().__init__()
        self.user_model = defaultdict(set)
        self.uid = 0

    @rule(target=donors, donor=from_model(FakeDonor, id=st.none()))
    def make_donor(self, donor):
        return donor

    @rule(donor=consumes(donors))
    def delete_donor(self, donor):
        for donors in self.user_model.values():
            if donor.id in donors:
                donors.remove(donor.id)
        donor.delete()

    @rule(target=users)
    def make_user(self):
        self.uid = self.uid + 1
        return User.objects.create_user(str(self.uid))

    @rule(user=consumes(users))
    def delete_user(self, user):
        if user.id in self.user_model:
            del self.user_model[user.id]
        user.delete()

    @rule(user=users, donor=donors)
    def star_donor(self, user, donor):
        donor.users_starred_by.add(user)
        self.user_model[user.id].add(donor.id)

    @rule(user=users, donor=donors)
    def unstar_donor(self, user, donor):
        donor.users_starred_by.remove(user)
        if user.id in self.user_model and donor.id in self.user_model[user.id]:
            self.user_model[user.id].remove(donor.id)

    @rule(user=users)
    def starring_matches(self, user):
        note(f"{FakeDonor.objects.count()=} {User.objects.count()=} {FakeDonor.users_starred_by.through.objects.count()=}")
        assert set(donor.id for donor in FakeDonor.objects.starred_by(user)) == self.user_model[user.id]
        assert len(list(FakeDonor.objects.starred_by(user))) == len(self.user_model[user.id])

DonorStarMachine.TestCase.settings = hsettings(max_examples = 50, stateful_step_count = 50, deadline=None)

class TestDonorStarring(TestCase, DonorStarMachine.TestCase):
    pass

class DonorMachine(TransactionalRuleBasedStateMachine):
    donors = Bundle("donors")
    photos = Bundle("photos")

    def __init__(self):
        super().__init__()
        self.donor_model = defaultdict(set)
        self.scanner_model = defaultdict(set)

    @rule(target=donors, donor=from_model(FakeDonor, id=st.none()))
    def make_donor(self, donor):
        return donor

    @rule(target=photos, photo=from_model(FakePhoto, id=st.none()))
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
    def set_donor(self, donor, photo):
        if photo.donor:
            self.donor_model[photo.donor.pk].remove(photo.pk)
        photo.donor = donor
        photo.save()
        self.donor_model[donor.pk].add(photo.pk)

    @rule(count=st.integers(max_value=1000, min_value=-1000))
    def check_filter_donated(self, count):
        db_donors = set()
        model_donors = set()
        for donor in FakeDonor.objects.filter_donated(at_least=count):
            db_donors.add(donor.pk)
            assert len(self.donor_model[donor.pk]) == donor.donated_count
        for donor in self.donor_model:
            if len(self.donor_model[donor]) >= count:
                model_donors.add(donor)
        assert db_donors == model_donors

    @rule()
    def check_counts(self):
        note(f"{FakeDonor.objects.count()=}")
        for donor in FakeDonor.objects.annotate_donatedcount().annotate_scannedcount():
            assert donor.donated_count == len(self.donor_model[donor.pk])
            assert donor.scanned_count == len(self.scanner_model[donor.pk])

DonorMachine.TestCase.settings = hsettings(max_examples = 50, stateful_step_count = 50, deadline=None)

class TestDonorQuerySet(TestCase, DonorMachine.TestCase):
    pass
