from django.test import TestCase, SimpleTestCase, RequestFactory, tag
from ..auth.views import RegisterAccount
from .. import models
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User, AnonymousUser, Permission
from django.urls import reverse
from django.utils.http import urlencode
from django.http import QueryDict
from ..forms import TagForm
from django.conf import settings
from os.path import join
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from archive.search.expression import TagExactly


class TestImageMixin:
    @classmethod
    def setUpClass(cls):
        with open('testdata/test.jpg', 'rb') as f:
            cls.test_img = f.read()
        super().setUpClass()

    @classmethod
    def createPhoto(cls, is_published=True, year=1950, donor=None, **kwargs):
        donor = donor or models.Donor.objects.create(last_name='last', first_name='first')
        return models.Photo.objects.create(
            original=SimpleUploadedFile(
                name='test_img.jpg',
                content=cls.test_img,
                content_type='image/jpeg',
            ),
            donor=donor,
            is_published=is_published,
            year=year,
            **kwargs,
        )


@tag("fast")
class PhotoTest(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.photo = cls.createPhoto()

    def testShouldDescribeItself(self):
        models.PhotoTag.objects.create(tag=models.Tag.objects.create(tag="dog"), photo=self.photo, accepted=True)
        models.PhotoTag.objects.create(tag=models.Tag.objects.create(tag="cat"), photo=self.photo, accepted=True)
        models.PhotoTag.objects.create(tag=models.Tag.objects.create(tag="car"), photo=self.photo, accepted=False)
        self.photo.terms.add(models.Term.objects.create(term="Animals"))
        self.photo.terms.add(models.Term.objects.create(term="Portraits"))
        self.photo.city = "Cedar Falls"
        self.photo.state = "IA"
        self.photo.county = "Black Hawk"
        self.photo.country = "USA"
        self.assertEqual(self.photo.describe(), {"dog", "cat", "Animals", "Portraits", "Cedar Falls, IA", "last, first", "history of Iowa", "Iowa", "Iowa History"})

    def testShouldNotAppearTwiceWhenTwoUsersSubmitSameTag(self):
        user = User.objects.create_user('testuser', 'user@email.com', 'testpassword')
        user2 = User.objects.create_user('testuser2', 'user@email.com', 'testpassword')
        photo = self.photo
        tag = models.Tag.objects.create(tag="test tag")
        phototag = models.PhotoTag.objects.create(tag=tag, photo=photo, accepted=True)
        phototag.creator.add(user2)
        phototag.creator.add(user)
        phototag.save()
        photo.save()
        self.assertEqual(models.Photo.objects.filter_photos(models.CollectionQuery(TagExactly("test tag"), user)).count(), 1)
        self.assertEqual(photo.get_accepted_tags().count(), 1)

    def testShouldEnforceUUIDFilename(self):
        photo = self.photo
        photo.original.save('badname.png', ContentFile(self.test_img))
        self.assertEqual(photo.original.path, join(settings.MEDIA_ROOT, 'original', '{}.jpg'.format(photo.uuid)))

    @tag("fast")
    def testShouldDisallowYearsBefore1800(self):
        photo = models.Photo(year=1799)
        with self.assertRaises(ValidationError) as cm:
            year = photo.clean_fields()
        self.assertIn('year', cm.exception.message_dict)

    @tag("fast")
    def testCityURL(self):
        photo = models.Photo(city='CityName', state='StateName')
        self.assertEqual(photo.get_city_url(), '{}?{}'.format(reverse('gridview'), urlencode({'city': photo.city, 'state': photo.state})))

    @tag("fast")
    def testCountyURL(self):
        photo = models.Photo(county='CountyName', state='StateName')
        self.assertEqual(photo.get_county_url(), '{}?{}'.format(reverse('gridview'), urlencode({'county': photo.county, 'state': photo.state})))

    def testShouldNotAllowGuestsToTagPhotos(self):
        resp = self.client.get(reverse('addtag', kwargs={'photo': self.photo.accession_number}))
        self.assertEqual(resp.status_code, 302)

        resp = self.client.post(reverse('addtag', kwargs={'photo': self.photo.accession_number}), {'tag': 'test tag'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(self.photo.get_proposed_tags()), 0)
        self.assertEqual(len(self.photo.get_accepted_tags()), 0)

    def testShouldBeAbleToTagPhotos(self):
        User.objects.create_user('testuser', 'user@email.com', 'testpassword')
        self.client.login(username='testuser', password='testpassword')
        resp = self.client.get(reverse('addtag', kwargs={'photo': self.photo.accession_number}))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(reverse('addtag', kwargs={'photo': self.photo.accession_number}), { 'tag': 'test tag'})
        self.assertEqual(len(self.photo.get_proposed_tags()), 1)
        self.assertEqual(self.photo.get_proposed_tags()[0].tag, 'test tag')
        self.assertEqual(len(self.photo.get_accepted_tags()), 0)

    def testShould404WhenPhotoNotFound(self):
        resp = self.client.get(reverse('photoview', kwargs={'page': 1, 'photo': 'FI99999'}))
        self.assertEqual(resp.status_code, 404)

    def testShouldHaveUniqueDownloadPage(self):
        self.assertEqual(self.photo.get_download_page_url(), reverse('download', kwargs={'pk': self.photo.id}))
        resp = self.client.get(reverse('download', kwargs={'pk': self.photo.id}))
        self.assertEqual(resp.status_code, 200)
        templates = {template.name for template in resp.templates}
        self.assertIn('archive/download-page.html', templates)
        self.assertIn('archive/base.html', templates)
        self.assertEqual(resp.context['host_uri'], settings.HOST_URI)

    def testShouldHaveSearchFiltersOnDownloadUrl(self):
        self.assertEqual(self.photo.get_download_page_url(params=QueryDict('a=1')), reverse('download', kwargs={'pk': self.photo.id}) + '?a=1')


@tag("fast")
class PhotoTagTest(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.photo = cls.createPhoto()
        cls.photo2 = cls.createPhoto()
        cls.tag = models.Tag.objects.create(tag='tag')
        cls.phototag = models.PhotoTag.objects.create(tag=cls.tag, photo=cls.photo, accepted=False)

    def testShouldAutomaticallyRemoveDeadTags(self):
        self.phototag.delete()
        self.assertEqual(models.Tag.objects.filter(tag='tag').count(), 0)

    def testShouldNotAutomaticallyRemoveLiveTags(self):
        phototag = models.PhotoTag.objects.create(tag=self.tag, photo=self.photo2, accepted=False)
        phototag.delete()
        self.assertEqual(models.Tag.objects.filter(tag='tag').count(), 1)

    def testShouldAllowDeletionOfTags(self):
        self.tag.delete()
        self.assertEqual(models.Tag.objects.filter(tag='tag').count(), 0)


@tag("fast")
class DonorTest(TestCase):
    def testURL(self):
        donor = models.Donor.objects.create(
            last_name='last',
            first_name='first',
        )
        self.assertEqual(donor.get_absolute_url(), "{}?{}".format(reverse('search-results'), urlencode({'donor': donor.id})))

@tag("fast")
class TermTest(TestCase):
    def testURL(self):
        term = models.Term.objects.create(term="test term")
        self.assertEqual(term.get_absolute_url(), "{}?{}".format(reverse('search-results'), urlencode({'term': term.id})))

@tag("fast")
class TagTest(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.photo = cls.createPhoto()

    def testSubstringSearchShouldNotReturnTooManyThings(self):
        photo = self.photo
        for x in range(11):
            tag = models.Tag.objects.create(tag="test tag {}".format(x))
            models.PhotoTag.objects.create(tag=tag, photo=photo, accepted=True)
        obj = self.client.get(reverse('tag-search'), dict(term='tag')).json()
        self.assertEqual(len(obj), 10)

    def testSubstringSearchShouldOnlyReturnMatchingTags(self):
        photo = self.photo
        tag1 = models.Tag.objects.create(tag="test tag")
        models.PhotoTag.objects.create(tag=tag1, photo=photo, accepted=True)

        tag2 = models.Tag.objects.create(tag="j tag 1")
        models.PhotoTag.objects.create(tag=tag2, photo=photo, accepted=True)
        tag3 = models.Tag.objects.create(tag="a tag 2")
        models.PhotoTag.objects.create(tag=tag3, photo=photo, accepted=True)
        tag4 = models.Tag.objects.create(tag="dog")
        models.PhotoTag.objects.create(tag=tag4, photo=photo, accepted=True)

        obj = self.client.get(reverse('tag-search'), dict(term='tag')).json()

        self.assertEqual(len(obj), 3)

    def testSubstringSearchShouldOnlyReturnAcceptedTags(self):
        photo = self.photo
        tag1 = models.Tag.objects.create(tag="test tag")
        models.PhotoTag.objects.create(tag=tag1, photo=photo, accepted=True)

        tag2 = models.Tag.objects.create(tag="j tag 1")
        tag3 = models.Tag.objects.create(tag="a tag 2")
        tag4 = models.Tag.objects.create(tag="dog")

        obj = self.client.get(reverse('tag-search'), dict(term='tag')).json()

        self.assertEqual(len(obj), 1)


    def testFindDeadTags(self):
        photo = self.photo
        tag1 = models.Tag.objects.create(tag="test tag")
        tag2 = models.Tag.objects.create(tag="dead tag 1")
        tag3 = models.Tag.objects.create(tag="dead tag 2")
        models.PhotoTag.objects.create(tag=tag1, photo=photo, accepted=False)
        self.assertEqual(models.Tag.dead_tags().count(), 2)
        for tag in models.Tag.dead_tags():
            self.assertNotEqual(tag.tag, tag1.tag)

    @tag("fast")
    def testURL(self):
        tag = models.Tag.objects.create(tag="test tag")
        self.assertEqual(tag.get_absolute_url(), "{}?{}".format(reverse('search-results'), urlencode({'tag': tag.tag})))

    @tag("fast")
    def testShouldEnforceLowerCase(self):
        tag = models.Tag.objects.create(tag='CAPITALIZED')
        tag.refresh_from_db()
        self.assertEqual(tag.tag, 'capitalized')


@tag("fast")
class TagFormTest(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.photo = cls.createPhoto()
        cls.user = User.objects.create_user('testuser', 'user@email.com', 'testpassword')
        cls.admin = User.objects.create_superuser('testuser2', 'user2@email.com', 'testpassword')

    def testShouldNotAllowTagsWhichAreAlreadyTerms(self):
        models.Term.objects.create(term='dog')
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
        self.assertTrue(models.PhotoTag.objects.get(photo=self.photo, tag__tag='hat').accepted)
        form = TagForm(data={'tag': 'dog'})
        self.assertTrue(form.is_valid())
        form.add_tag(self.photo, user)
        self.photo.refresh_from_db()
        self.assertTrue(models.PhotoTag.objects.get(photo=self.photo, tag__tag='dog').accepted)


    def testShouldHandleTagsWithDifferentCapitalization(self):
        photo = self.photo
        user = self.user

        form = TagForm(data={'tag': 'Hat'})
        form.is_valid()
        form.add_tag(photo, user)
        photo = models.Photo.objects.create(
            original=SimpleUploadedFile(
                    name='test_img.jpg',
                    content=self.test_img,
                    content_type='image/jpeg'
            ),
            donor=models.Donor.objects.create(last_name='last', first_name='first'),
        )
        form = TagForm(data={'tag': 'hat'})
        form.is_valid()
        form.add_tag(photo, user)
        self.assertEqual(models.Tag.objects.filter(tag='Hat').count(), 1)
        self.assertEqual(models.Tag.objects.filter(tag='hat').count(), 1)

    def testShouldTreatCommasAsTagSeparators(self):
        form = TagForm(data={'tag': 'dog, cat, human'})
        self.assertTrue(form.is_valid())
        form.add_tag(self.photo, self.user)
        self.assertEqual(models.Tag.objects.filter(tag='dog').count(), 1)
        self.assertEqual(models.Tag.objects.filter(tag='cat').count(), 1)
        self.assertEqual(models.Tag.objects.filter(tag='human').count(), 1)

class WhenHave50Photos(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.donor = donor = models.Donor.objects.create(
            last_name='last',
            first_name='first',
        )
        cls.photos = []
        for y in range(1900, 1905):
            p = cls.createPhoto(
                year=y,
                donor=donor,
                city='city{}'.format(y % 3),
                state='state{}'.format(y % 3),
                county='county{}'.format(y % 3),
            )
            cls.photos.append(p)

    def testCountyIndex(self):
        self.assertEqual(
            models.Photo.county_index(),
            [
                {'name': 'county0, state0', 'count': 1, 'href': self.photos[2].get_county_url()},
                {'name': 'county1, state1', 'count': 2, 'href': self.photos[0].get_county_url()},
                {'name': 'county2, state2', 'count': 2, 'href': self.photos[1].get_county_url()},
            ]
        )

    def testCityIndex(self):
        self.assertEqual(
            models.Photo.city_index(),
            [
                {'name': 'city0, state0', 'count': 1, 'href': self.photos[2].get_city_url()},
                {'name': 'city1, state1', 'count': 2, 'href': self.photos[0].get_city_url()},
                {'name': 'city2, state2', 'count': 2, 'href': self.photos[1].get_city_url()},
            ]
        )

    def testDonorIndex(self):
        self.assertEqual(
            models.Donor.index(),
            [
                {'name': 'last, first', 'count': 5, 'href': self.donor.get_absolute_url()},
            ]
        )

    def testTermIndex(self):
        endswithzero = models.Term.objects.create(term="new decade")
        even = models.Term.objects.create(term="even year")
        no = models.Term.objects.create(term="none")
        for photo in self.photos:
            if photo.year % 2 == 0:
                photo.terms.add(even)
            if photo.year % 10 == 0:
                photo.terms.add(endswithzero)
        self.assertEqual(
            models.Term.index(),
            [
                {'name': 'even year', 'count': 3, 'href': even.get_absolute_url()},
                {'name': 'new decade', 'count': 1, 'href': endswithzero.get_absolute_url()},
            ],
        )

    def testTagIndex(self):
        endswithzero = models.Tag.objects.create(tag="new decade")
        eventag = models.Tag.objects.create(tag="even year")
        notags = models.Tag.objects.create(tag="none")
        for photo in self.photos:
            if photo.year % 2 == 0:
                models.PhotoTag.objects.create(tag=eventag, photo=photo, accepted=True)
            if photo.year % 10 == 0:
                models.PhotoTag.objects.create(tag=endswithzero, photo=photo, accepted=True)
            elif photo.year % 3 == 0:
                models.PhotoTag.objects.create(tag=endswithzero, photo=photo, accepted=False)
        self.assertEqual(
            models.Tag.index(),
            [
                {'name': 'even year', 'count': 3, 'href': eventag.get_absolute_url()},
                {'name': 'new decade', 'count': 1, 'href': endswithzero.get_absolute_url()},
            ],
        )

    def testYearIndex(self):
        for i, photo in enumerate(models.Photo.objects.year_index()):
            self.assertEqual(photo.row_number, i)
            self.assertEqual(photo.page_number(), i//10 + 1)


    def testShouldRedirectToCorrectPageForPhoto(self):
        photos = self.photos
        for page in range(1, 6):
            thispage = photos[:10]
            photos = photos[10:]
            for photo in thispage:
                resp = self.client.get(reverse('photoview', kwargs={'page': page % 5 + 1, 'photo':photo.accession_number}))
                self.assertRedirects(resp, reverse('photoview', kwargs={'page': page, 'photo':photo.accession_number}))

    def testGridViewShouldDisplayAllPhotosInOrder(self):
        photo_ids = {photo.id for photo in self.photos}
        currentpage = 1
        last = None
        while True:
            resp = self.client.get(reverse('gridview', kwargs={'page': currentpage}), {'display': 16})
            for photo in resp.context['page_obj']:
                self.assertIn(photo.id, photo_ids)
                if last:
                    self.assertTrue(last.year < photo.year)
                last = photo

                photo_ids.remove(photo.id)
            currentpage += 1
            if not resp.context['page_obj'].has_next():
                break
        self.assertEqual(len(photo_ids), 0)

    def testGridShouldRespectTermFilters(self):
        term = models.Term.objects.create(term="test term")
        photos = [self.photos[2], self.photos[3], self.photos[1]]
        for photo in photos:
            photo.terms.add(term)
        resp = self.client.get(term.get_absolute_url())
        self.assertEqual(len(resp.context['page_obj']), len(photos))
        our_ids = {photo.id for photo in photos}
        got_ids = {photo.id for photo in resp.context['page_obj']}
        self.assertEqual(our_ids, got_ids)

    def testGridShouldHandleNonexistantTags(self):
        resp = self.client.get(reverse('gridview', kwargs={'page': 1}), {'tag': "lakdsjflkasdf"})
        self.assertEqual(len(resp.context['page_obj']), 0)

    def testGridShouldRespectTagFilters(self):
        tag = models.Tag.objects.create(tag="test tag")
        photos = [self.photos[2], self.photos[0], self.photos[3]]
        for photo in photos:
            models.PhotoTag.objects.create(tag=tag, photo=photo, accepted=True)
        resp = self.client.get(tag.get_absolute_url())
        self.assertEqual(len(resp.context['page_obj']), len(photos))
        our_ids = {photo.id for photo in photos}
        got_ids = {photo.id for photo in resp.context['page_obj']}
        self.assertEqual(our_ids, got_ids)

    def testFilteringShouldNotShowUnapprovedTags(self):
        tag = models.Tag.objects.create(tag="test tag")
        photos = [self.photos[2], self.photos[1], self.photos[4]]
        for photo in photos:
            models.PhotoTag.objects.create(tag=tag, photo=photo, accepted=False)
        resp = self.client.get(reverse('gridview', kwargs={'page': 1}), {'tag': tag.slug})
        self.assertEqual(len(resp.context['page_obj']), 0)

    def testGridViewShouldHonorDisplayParameter(self):
        for disp in range(2, 5):
            resp = self.client.get(reverse('gridview', kwargs={'page': 1}), {'display': disp})
            self.assertEqual(len(resp.context['page_obj']), disp)

    def testUserProfile(self):
        users = [
            User.objects.create_user('testuser', 'user@email.com', 'testpassword'),
            User.objects.create_user('testuser2', 'user@email.com', 'testpassword'),
        ]
        collections = []
        i = 0
        for user in users:
            for privacy in models.Collection.PRIVACY_TYPES:
                coll = models.Collection.objects.create(
                    name='test collection{}'.format(i),
                    owner=user,
                    visibility=privacy[0],
                )
                coll.photos.set(self.photos[i:i+4])
                collections.append(coll)
                i += 4
        self.client.login(username='testuser', password='testpassword')
        resp = self.client.get(reverse('user-page', args=['testuser']))
        self.assertEqual(len(resp.context['object_list']), 3)
        for collection in resp.context['object_list']:
            self.assertEqual(collection.owner.get_username(), 'testuser')

        resp = self.client.get(reverse('user-page', args=['testuser2']))
        self.assertEqual(len(resp.context['object_list']), 1)
        for collection in resp.context['object_list']:
            self.assertEqual(collection.owner.get_username(), 'testuser2')

    def testUserProfileShould404IfUserDoesNotExist(self):
        resp = self.client.get(reverse('user-page', args=['notarealuser']))
        self.assertEqual(resp.status_code, 404)

@tag("fast")
class RegisterAccountTest(TestCase):
    def testUserIsHumanShouldReturnFalse(self):
        req = RequestFactory().post(reverse('register-account'), data={'g-recaptcha-response': ''})
        req.user = AnonymousUser()
        v = RegisterAccount()
        v.request = req
        self.assertFalse(v.user_is_human())






from archive.templatetags import timeline
@tag("fast")
class TimelineDisplay(SimpleTestCase):
    def assertIsPosition(self, obj):
        for key in ('x', 'y', 'width', 'height'):
            self.assertIn(key, obj)
            self.assertTrue(isinstance(obj[key], int) or isinstance(obj[key], float))
    def testShouldDefineMinorMarkerPositions(self):
        years = [(year, '/{}'.format(year), '/{}.json'.format(year)) for year in [1900, 1901, 1902, 1903, 1904, 1905]]
        result = timeline.make_timeline(years, width=60)
        self.assertIn('majornotches', result)
        self.assertEqual(len(result['majornotches']), 1)
        for notch in result['majornotches']:
            for key in ('target', 'json_target', 'box', 'notch', 'label'):
                self.assertIn(key, notch)
            for key in ('box', 'notch'):
                self.assertIsPosition(notch[key])
            for key in ('text', 'x', 'y'):
                self.assertIn(key, notch['label'])
        self.assertIn('minornotches', result)
        self.assertEqual(len(result['minornotches']), 5)
        for notch in result['minornotches']:
            for key in ('target', 'json_target', 'box', 'notch'):
                self.assertIn(key, notch)
            for key in ('box', 'notch'):
                self.assertIsPosition(notch[key])
