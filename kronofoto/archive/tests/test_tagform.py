from django.test import TestCase, tag
from django.contrib.auth.models import User, Permission
from ..models import Term, Photo, Tag
from ..forms import TagForm
from .util import TestImageMixin


@tag("fast")
class TagFormTest(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.photo = cls.createPhoto()
        cls.user = User.objects.create_user('testuser', 'user@email.com', 'testpassword')
        cls.admin = User.objects.create_superuser('testuser2', 'user2@email.com', 'testpassword')

    def testShouldNotAllowTagsWhichAreAlreadyTerms(self):
        Term.objects.create(term='dog')
        form = TagForm(data={'tag': 'dog'})
        self.assertFalse(form.is_valid())

    def testShouldNotRemoveAcceptedStatus(self):
        form = TagForm(data=dict(tag='dog'))
        self.assertTrue(form.is_valid())
        form.add_tag(self.photo, self.admin)
        self.assertEqual(self.photo.get_accepted_tags().count(), 1)
        form.add_tag(self.photo, self.user)
        self.assertEqual(self.photo.get_accepted_tags().count(), 1)

    def testShouldNotDuplicateTag(self):
        form = TagForm(data=dict(tag='dog'))
        self.assertTrue(form.is_valid())
        form.add_tag(self.photo, self.user)
        self.assertEqual(self.photo.get_accepted_tags().count(), 0)
        form.add_tag(self.photo, self.admin)
        self.assertEqual(self.photo.get_accepted_tags(self.admin).count(), 1)

    def testShouldAutoAcceptTagsIfUserHasPermissions(self):
        user = self.user
        form = TagForm(data={'tag': 'dog'})
        self.assertTrue(form.is_valid())
        form.add_tag(self.photo, user)

        user.is_staff = True
        user.user_permissions.add(Permission.objects.get(codename='add_tag'))
        user.user_permissions.add(Permission.objects.get(codename='change_tag'))
        user.user_permissions.add(Permission.objects.get(codename='add_phototag'))
        user.user_permissions.add(Permission.objects.get(codename='change_phototag'))
        user.save()
        user = User.objects.get(username='testuser')
        form = TagForm(data={'tag': 'Hat'})
        self.assertTrue(form.is_valid())
        form.add_tag(self.photo, user)
        self.photo.refresh_from_db()
        self.assertTrue(Photo.tags.through.objects.get(photo=self.photo, tag__tag='hat').accepted)
        form = TagForm(data={'tag': 'dog'})
        self.assertTrue(form.is_valid())
        form.add_tag(self.photo, user)
        self.photo.refresh_from_db()
        self.assertTrue(Photo.tags.through.objects.get(photo=self.photo, tag__tag='dog').accepted)


    def testShouldHandleTagsWithDifferentCapitalization(self):
        photo = self.photo
        user = self.user

        form = TagForm(data={'tag': 'Hat'})
        form.is_valid()
        form.add_tag(photo, user)
        photo = self.createPhoto()
        form = TagForm(data={'tag': 'hat'})
        form.is_valid()
        form.add_tag(photo, user)
        self.assertEqual(Tag.objects.filter(tag='Hat').count(), 1)
        self.assertEqual(Tag.objects.filter(tag='hat').count(), 1)

    def testShouldTreatCommasAsTagSeparators(self):
        form = TagForm(data={'tag': 'dog, cat, human'})
        self.assertTrue(form.is_valid())
        form.add_tag(self.photo, self.user)
        self.assertEqual(Tag.objects.filter(tag='dog').count(), 1)
        self.assertEqual(Tag.objects.filter(tag='cat').count(), 1)
        self.assertEqual(Tag.objects.filter(tag='human').count(), 1)
