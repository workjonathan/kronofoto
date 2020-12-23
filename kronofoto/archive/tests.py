from django.test import TestCase, SimpleTestCase, RequestFactory
from . import models, views
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User, AnonymousUser, Permission
from django.urls import reverse
from django.utils.http import urlencode
from archive.search import expression, evaluate, parser
from archive.search.expression import *
from .forms import TagForm


class CollectionQueryTest(TestCase):
    def setUp(self):
        self.donor = models.Donor.objects.create(first_name='First', last_name='Last')
        self.term = models.Term.objects.create(term='Airplane')
        self.tag = models.Tag.objects.create(tag='dog')

    def testShouldDescribeCounty(self):
        coll = models.CollectionQuery(dict(county='Place', state='State'), AnonymousUser)
        self.assertEqual(str(coll), 'Photos from Place County, State')

    def testShouldDescribeCity(self):
        coll = models.CollectionQuery(dict(city='CityTown', state='State'), AnonymousUser)
        self.assertEqual(str(coll), 'Photos from CityTown, State')

    def testShouldDescribeTag(self):
        coll = models.CollectionQuery(dict(tag=self.tag.slug), AnonymousUser)
        self.assertEqual(str(coll), 'Photos tagged with dog')

    def testShouldDescribeTerm(self):
        coll = models.CollectionQuery(dict(term=self.term.slug), AnonymousUser)
        self.assertEqual(str(coll), 'Photos termed with Airplane')

    def testShouldDescribeDonor(self):
        coll = models.CollectionQuery(dict(donor=self.donor.id), AnonymousUser)
        self.assertEqual(str(coll), 'Photos in First Last\'s Collection')

    def testShouldDescribeUnfilteredCollection(self):
        coll = models.CollectionQuery(dict(page=2), AnonymousUser)
        self.assertEqual(str(coll), 'All Photos')


class FakeImageTest(SimpleTestCase):
    def testShouldHaveThumbnail(self):
        self.assertEqual(views.FAKE_PHOTO['thumbnail']['url'], views.EMPTY_PNG)

    def testShouldHaveWidth(self):
        self.assertEqual(views.FAKE_PHOTO['thumbnail']['width'], 75)

    def testShouldHaveHeight(self):
        self.assertEqual(views.FAKE_PHOTO['thumbnail']['height'], 75)

class FakeTimelinePageTest(SimpleTestCase):
    def testShouldNotHavePhotos(self):
        self.assertEqual(len(list(views.FakeTimelinePage())), 0)

    def testShouldHaveAnObjectListWithTenFakePhotos(self):
        self.assertEqual(len(list(views.FakeTimelinePage().object_list)), 10)

class TimelinePaginatorTest(TestCase):
    def testInvalidPageShouldGetFakePage(self):
        page = views.TimelinePaginator(models.Photo.objects.all().order_by('id'), per_page=10).get_page(2)
        for photo in page.object_list:
            self.assertEqual(photo['thumbnail']['url'], views.EMPTY_PNG)

class PhotoTest(TestCase):
    def testShouldNotAppearTwiceWhenTwoUsersSubmitSameTag(self):
        user = User.objects.create_user('testuser', 'user@email.com', 'testpassword')
        user2 = User.objects.create_user('testuser2', 'user@email.com', 'testpassword')
        photo = models.Photo(
            original=SimpleUploadedFile(
                name='test_img.jpg',
                content=open('testdata/test.jpg', 'rb').read(),
                content_type='image/jpeg'),
            donor=models.Donor.objects.create(last_name='last', first_name='first'),
            is_published=True,
            year=1950,
        )
        photo.save()
        tag = models.Tag.objects.create(tag="test tag")
        phototag = models.PhotoTag.objects.create(tag=tag, photo=photo, accepted=True)
        phototag.creator.add(user2)
        phototag.creator.add(user)
        phototag.save()
        photo.save()
        self.assertEqual(models.Photo.objects.filter_photos(models.CollectionQuery({'tag': tag.slug}, user)).count(), 1)
        self.assertEqual(photo.get_accepted_tags().count(), 1)

    def testCityURL(self):
        photo = models.Photo(city='CityName', state='StateName')
        self.assertEqual(photo.get_city_url(), '{}?{}'.format(reverse('gridview'), urlencode({'city': photo.city, 'state': photo.state})))

    def testCountyURL(self):
        photo = models.Photo(county='CountyName', state='StateName')
        self.assertEqual(photo.get_county_url(), '{}?{}'.format(reverse('gridview'), urlencode({'county': photo.county, 'state': photo.state})))


class DonorTest(TestCase):
    def testURL(self):
        donor = models.Donor.objects.create(
            last_name='last',
            first_name='first',
        )
        self.assertEqual(donor.get_absolute_url(), "{}?{}".format(reverse('gridview'), urlencode({'donor': donor.id})))

class TermTest(TestCase):
    def testURL(self):
        term = models.Term.objects.create(term="test term")
        self.assertEqual(term.get_absolute_url(), "{}?{}".format(reverse('gridview'), urlencode({'term': term.slug})))

class TagTest(TestCase):
    def testSubstringSearchShouldNotReturnTooManyThings(self):
        photo = models.Photo.objects.create(
            original=SimpleUploadedFile(
                    name='test_img.jpg',
                    content=open('testdata/test.jpg', 'rb').read(),
                    content_type='image/jpeg'
            ),
            donor=models.Donor.objects.create(last_name='last', first_name='first'),
        )
        for x in range(11):
            tag = models.Tag.objects.create(tag="test tag {}".format(x))
            models.PhotoTag.objects.create(tag=tag, photo=photo, accepted=True)

        obj = self.client.get(reverse('tag-search'), dict(term='tag')).json()

        self.assertEqual(len(obj), 10)

    def testSubstringSearchShouldOnlyReturnMatchingTags(self):
        photo = models.Photo.objects.create(
            original=SimpleUploadedFile(
                    name='test_img.jpg',
                    content=open('testdata/test.jpg', 'rb').read(),
                    content_type='image/jpeg'
            ),
            donor=models.Donor.objects.create(last_name='last', first_name='first'),
        )
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
        photo = models.Photo.objects.create(
            original=SimpleUploadedFile(
                    name='test_img.jpg',
                    content=open('testdata/test.jpg', 'rb').read(),
                    content_type='image/jpeg'
            ),
            donor=models.Donor.objects.create(last_name='last', first_name='first'),
        )
        tag1 = models.Tag.objects.create(tag="test tag")
        models.PhotoTag.objects.create(tag=tag1, photo=photo, accepted=True)

        tag2 = models.Tag.objects.create(tag="j tag 1")
        tag3 = models.Tag.objects.create(tag="a tag 2")
        tag4 = models.Tag.objects.create(tag="dog")

        obj = self.client.get(reverse('tag-search'), dict(term='tag')).json()

        self.assertEqual(len(obj), 1)


    def testFindDeadTags(self):
        photo = models.Photo.objects.create(
            original=SimpleUploadedFile(
                    name='test_img.jpg',
                    content=open('testdata/test.jpg', 'rb').read(),
                    content_type='image/jpeg'
            ),
            donor=models.Donor.objects.create(last_name='last', first_name='first'),
        )
        tag1 = models.Tag.objects.create(tag="test tag")
        tag2 = models.Tag.objects.create(tag="dead tag 1")
        tag3 = models.Tag.objects.create(tag="dead tag 2")
        models.PhotoTag.objects.create(tag=tag1, photo=photo, accepted=False)
        self.assertEqual(models.Tag.dead_tags().count(), 2)
        for tag in models.Tag.dead_tags():
            self.assertNotEqual(tag.tag, tag1.tag)

    def testURL(self):
        tag = models.Tag.objects.create(tag="test tag")
        self.assertEqual(tag.get_absolute_url(), "{}?{}".format(reverse('gridview'), urlencode({'tag': tag.slug})))

    def testShouldEnforceLowerCase(self):
        tag = models.Tag.objects.create(tag='CAPITALIZED')
        tag.refresh_from_db()
        self.assertEqual(tag.tag, 'capitalized')


class TagFormTest(TestCase):
    def setUp(self):
        self.photo = models.Photo.objects.create(
            original=SimpleUploadedFile(
                    name='test_img.jpg',
                    content=open('testdata/test.jpg', 'rb').read(),
                    content_type='image/jpeg'
            ),
            donor=models.Donor.objects.create(last_name='last', first_name='first'),
        )
        self.user = User.objects.create_user('testuser', 'user@email.com', 'testpassword')
        self.admin = User.objects.create_superuser('testuser2', 'user2@email.com', 'testpassword')

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
                    content=open('testdata/test.jpg', 'rb').read(),
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

class WhenHave50Photos(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.donor = donor = models.Donor.objects.create(
            last_name='last',
            first_name='first',
        )
        cls.photos = []
        for y in range(1900, 1950):
            p = models.Photo.objects.create(
                original=SimpleUploadedFile(
                    name='test_img.jpg',
                    content=open('testdata/test.jpg', 'rb').read(),
                    content_type='image/jpeg'),
                donor=donor,
                year=y,
                is_published=True,
                city='city{}'.format(y % 3),
                state='state{}'.format(y % 3),
                county='county{}'.format(y % 3),
            )
            cls.photos.append(p)

    def testShouldAutomaticallyRemoveDeadTags(self):
        tag = models.Tag.objects.create(tag='unused tag')
        phototag = models.PhotoTag.objects.create(tag=tag, photo=self.photos[0], accepted=False)
        phototag.delete()
        self.assertEqual(models.Tag.objects.filter(tag='unused tag').count(), 0)

    def testShouldNotAutomaticallyRemoveLiveTags(self):
        tag = models.Tag.objects.create(tag='still used tag')
        phototag = models.PhotoTag.objects.create(tag=tag, photo=self.photos[0], accepted=False)
        phototag = models.PhotoTag.objects.create(tag=tag, photo=self.photos[1], accepted=False)
        phototag.delete()
        self.assertEqual(models.Tag.objects.filter(tag='still used tag').count(), 1)

    def testCountyIndex(self):
        self.assertEqual(
            models.Photo.county_index(),
            [
                {'name': 'county0, state0', 'count': 16, 'href': self.photos[2].get_county_url()},
                {'name': 'county1, state1', 'count': 17, 'href': self.photos[0].get_county_url()},
                {'name': 'county2, state2', 'count': 17, 'href': self.photos[1].get_county_url()},
            ]
        )

    def testCityIndex(self):
        self.assertEqual(
            models.Photo.city_index(),
            [
                {'name': 'city0, state0', 'count': 16, 'href': self.photos[2].get_city_url()},
                {'name': 'city1, state1', 'count': 17, 'href': self.photos[0].get_city_url()},
                {'name': 'city2, state2', 'count': 17, 'href': self.photos[1].get_city_url()},
            ]
        )

    def testDonorIndex(self):
        self.assertEqual(
            models.Donor.index(),
            [
                {'name': 'last, first', 'count': 50, 'href': self.donor.get_absolute_url()},
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
                {'name': 'even year', 'count': 25, 'href': even.get_absolute_url()},
                {'name': 'new decade', 'count': 5, 'href': endswithzero.get_absolute_url()},
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
                {'name': 'even year', 'count': 25, 'href': eventag.get_absolute_url()},
                {'name': 'new decade', 'count': 5, 'href': endswithzero.get_absolute_url()},
            ],
        )


    def testYearIndex(self):
        for i, photo in enumerate(models.Photo.objects.year_index()):
            self.assertEqual(photo.row_number, i)
            self.assertEqual(photo.page_number(), i//10 + 1)

    def testSearchShouldSupportBooleanLogic(self):
        expr1 = expression.YearEquals(1911) & expression.YearEquals(1912)
        expr2 = expression.YearEquals(1911) | expression.YearEquals(1912)
        self.assertEqual(len(evaluate(expr1, models.Photo.objects)), 0)
        self.assertEqual(len(evaluate(~expr1, models.Photo.objects)), 50)
        photomatches = evaluate(expr2, models.Photo.objects)
        self.assertEqual(len(photomatches), 2)
        for photo in photomatches:
            self.assertIn(photo.year, (1911, 1912))
        photomatches = evaluate(~expr2, models.Photo.objects)
        self.assertEqual(len(photomatches), 48)
        for photo in photomatches:
            self.assertNotIn(photo.year, (1911, 1912))

    def testShouldNotAllowGuestsToTagPhotos(self):
        resp = self.client.get(reverse('addtag', kwargs={'photo': self.photos[0].accession_number}))
        self.assertEqual(resp.status_code, 302)

        resp = self.client.post(reverse('addtag', kwargs={'photo': self.photos[0].accession_number}), { 'tag': 'test tag'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(self.photos[0].get_proposed_tags()), 0)
        self.assertEqual(len(self.photos[0].get_accepted_tags()), 0)

    def testShouldBeAbleToTagPhotos(self):
        User.objects.create_user('testuser', 'user@email.com', 'testpassword')
        self.client.login(username='testuser', password='testpassword')
        resp = self.client.get(reverse('addtag', kwargs={'photo': self.photos[0].accession_number}))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(reverse('addtag', kwargs={'photo': self.photos[0].accession_number}), { 'tag': 'test tag'})
        self.assertEqual(len(self.photos[0].get_proposed_tags()), 1)
        self.assertEqual(self.photos[0].get_proposed_tags()[0].tag, 'test tag')
        self.assertEqual(len(self.photos[0].get_accepted_tags()), 0)

    def testShould404WhenPhotoNotFound(self):
        resp = self.client.get(reverse('photoview', kwargs={'page': 1, 'photo': 'FI99999'}))
        self.assertEqual(resp.status_code, 404)

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

    def testGridViewShouldHaveNavigationButtons(self):
        pages = ["{}?{}".format(reverse('gridview', kwargs={'page': page}), urlencode({'display': 16})) for page in [1,2,3,4]]
        resp = self.client.get(pages[0])
        self.assertInHTML('<div id="navigation">First Previous <a href="{}">Next</a> <a href="{}">Last</a></div>'.format(pages[1], pages[-1]), resp.content.decode('utf-8'))
        resp = self.client.get(pages[1])
        self.assertInHTML('<div id="navigation"><a href="{}">First</a> <a href="{}">Previous</a> <a href="{}">Next</a> <a href="{}">Last</a></div>'.format(pages[0], pages[0], pages[2], pages[-1]), resp.content.decode('utf-8'))
        resp = self.client.get(pages[2])
        self.assertInHTML('<div id="navigation"><a href="{}">First</a> <a href="{}">Previous</a> <a href="{}">Next</a> <a href="{}">Last</a></div>'.format(pages[0], pages[1], pages[3], pages[-1]), resp.content.decode('utf-8'))
        resp = self.client.get(pages[3])
        self.assertInHTML('<div id="navigation"><a href="{}">First</a> <a href="{}">Previous</a> Next Last'.format(pages[0], pages[2]), resp.content.decode('utf-8'))

    def testGridShouldRespectTermFilters(self):
        term = models.Term.objects.create(term="test term")
        photos = [self.photos[2], self.photos[5], self.photos[15]]
        for photo in photos:
            photo.terms.add(term)
        resp = self.client.get(reverse('gridview', kwargs={'page': 1}), {'term': term.slug})
        self.assertEqual(len(resp.context['page_obj']), len(photos))
        our_ids = {photo.id for photo in photos}
        got_ids = {photo.id for photo in resp.context['page_obj']}
        self.assertEqual(our_ids, got_ids)

    def testGridShouldHandleNonexistantTags(self):
        resp = self.client.get(reverse('gridview', kwargs={'page': 1}), {'tag': "lakdsjflkasdf"})
        self.assertEqual(len(resp.context['page_obj']), 0)

    def testGridShouldRespectTagFilters(self):
        tag = models.Tag.objects.create(tag="test tag")
        photos = [self.photos[2], self.photos[5], self.photos[15]]
        for photo in photos:
            models.PhotoTag.objects.create(tag=tag, photo=photo, accepted=True)
        resp = self.client.get(reverse('gridview', kwargs={'page': 1}), {'tag': tag.slug})
        self.assertEqual(len(resp.context['page_obj']), len(photos))
        our_ids = {photo.id for photo in photos}
        got_ids = {photo.id for photo in resp.context['page_obj']}
        self.assertEqual(our_ids, got_ids)

    def testFilteringShouldNotShowUnapprovedTags(self):
        tag = models.Tag.objects.create(tag="test tag")
        photos = [self.photos[2], self.photos[5], self.photos[15]]
        for photo in photos:
            models.PhotoTag.objects.create(tag=tag, photo=photo, accepted=False)
        resp = self.client.get(reverse('gridview', kwargs={'page': 1}), {'tag': tag.slug})
        self.assertEqual(len(resp.context['page_obj']), 0)

    def testGridViewShouldHonorDisplayParameter(self):
        for disp in range(15, 24):
            resp = self.client.get(reverse('gridview', kwargs={'page': 1}), {'display': disp})
            self.assertEqual(len(resp.context['page_obj']), disp)

    def testGridViewShouldDisplayPhotoCount(self):
        currentpage = 1
        while True:
            resp = self.client.get(reverse('gridview', kwargs={'page': currentpage}), {'display': 16})
            self.assertInHTML(
                '<div id="position">Items {} - {} of {}</div>'.format(
                    (currentpage-1)*16+1, min(50, currentpage*16), 50
                ),
                resp.content.decode('utf-8'),
            )
            currentpage += 1
            if not resp.context['page_obj'].has_next():
                break

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

class RegisterAccountTest(TestCase):
    def testUserIsHumanShouldReturnFalse(self):
        req = RequestFactory().post(reverse('register-account'), data={'g-recaptcha-response': ''})
        req.user = AnonymousUser()
        v = views.RegisterAccount()
        v.request = req
        self.assertFalse(v.user_is_human())


class ParserTest(SimpleTestCase):
    def testParserShouldParseTypedNumbers(self):
        self.assertEqual(parser.tokenize.parse('year:1912'), [YearEquals(1912)])
        self.assertEqual(parser.parse('year:1912'), YearEquals(1912))

    def testParserShouldParseTypedStrings(self):
        self.assertEqual(parser.tokenize.parse('caption:dog'), [Caption('dog')])
        self.assertEqual(parser.parse('caption:dog'), Caption('dog'))

    def testParserShouldParseUntypedStrings(self):
        self.assertEqual(
            parser.tokenize.parse('dog'),
            [Or(Donor('dog'), Or(Caption('dog'), Or(State('dog'), Or(Country('dog'), Or(County('dog'), Or(City('dog'), Or(Tag('dog'), Term('dog'))))))))],
        )
        self.assertEqual(
            parser.parse('dog'),
            Or(Donor('dog'), Or(Caption('dog'), Or(State('dog'), Or(Country('dog'), Or(County('dog'), Or(City('dog'), Or(Tag('dog'), Term('dog')))))))),
        )

    def testParserShouldParseUntypedNumbers(self):
        self.assertEqual(parser.tokenize.parse('1912'), [Or(YearEquals(1912), Or(Donor('1912'), Or(Caption('1912'), Or(State('1912'), Or(Country('1912'), Or(County('1912'), Or(City('1912'), Or(Tag('1912'), Term('1912')))))))))])
        self.assertEqual(parser.parse('1912'), Or(YearEquals(1912), Or(Donor('1912'), Or(Caption('1912'), Or(State('1912'), Or(Country('1912'), Or(County('1912'), Or(City('1912'), Or(Tag('1912'), Term('1912'))))))))))

    def testParserShouldNegateTerms(self):
        self.assertEqual(parser.tokenize.parse('-caption:dog'), ['-', Caption('dog')])
        self.assertEqual(parser.parse('-caption:dog'), Not(Caption('dog')))

    def testParserShouldParseAndExpressions(self):
        self.assertEqual(parser.tokenize.parse('caption:dog AND caption:cat'), [Caption('dog'), 'AND', Caption('cat')])
        self.assertEqual(parser.parse('caption:dog AND caption:cat'), And(Caption('dog'), Caption('cat')))

    def testParserShouldParseOrExpressions(self):
        self.assertEqual(parser.tokenize.parse('caption:dog OR caption:cat'), [Caption('dog'), 'OR', Caption('cat')])
        self.assertEqual(parser.parse('caption:dog OR caption:cat'), Or(Caption('dog'), Caption('cat')))

    def testParserShouldSupportOrderOfOperations(self):
        self.assertEqual(
            parser.tokenize.parse('caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            [Caption('bird'), 'AND', Caption('dog'), "OR", Caption('cat'), "AND", Caption('banana')],
        )
        self.assertEqual(
            parser.parse('caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            Or(And(Caption('bird'), Caption('dog')), And(Caption('cat'), Caption('banana'))),
        )

    def testParserShouldSupportOrderOfOperations(self):
        self.assertEqual(
            parser.tokenize.parse('caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            [Caption('bird'), 'AND', Caption('dog'), 'OR', Caption('cat'), 'AND', Caption('banana')],
        )
        self.assertEqual(
            parser.parse('caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            Or(And(Caption('bird'), Caption('dog')), And(Caption('cat'), Caption('banana'))),
        )
        self.assertEqual(
            parser.tokenize.parse('-caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            ['-', Caption('bird'), 'AND', Caption('dog'), 'OR', Caption('cat'), 'AND', Caption('banana')],
        )
        self.assertEqual(
            parser.parse('-caption:bird AND caption:dog OR caption:cat AND caption:banana'),
            Or(And(Not(Caption('bird')), Caption('dog')), And(Caption('cat'), Caption('banana'))),
        )

    def testParserShouldSupportParentheses(self):
        self.assertEqual(parser.tokenize.parse('(caption:bird)'), ['(', Caption('bird'), ')'])
        self.assertEqual(parser.parse('(caption:bird)'), Caption('bird'))
        self.assertEqual(
            parser.tokenize.parse('caption:bird AND (caption:dog OR caption:cat) AND caption:banana'),
            [Caption('bird'), 'AND', '(', Caption('dog'), 'OR', Caption('cat'), ')', 'AND', Caption('banana')]
        )
        self.assertEqual(
            parser.parse('caption:bird AND (caption:dog OR caption:cat) AND caption:banana'),
            And(And(Caption('bird'), Or(Caption('dog'), Caption('cat'))), Caption('banana')),
        )
        self.assertEqual(
            parser.tokenize.parse('(caption:bird OR caption:dog) AND (caption:cat OR caption:banana)'),
            ['(', Caption('bird'), 'OR', Caption('dog'), ')', 'AND', '(', Caption('cat'), 'OR', Caption('banana'), ')'],
        )
        self.assertEqual(
            parser.parse('(caption:bird OR caption:dog) AND (caption:cat OR caption:banana)'),
            And(Or(Caption('bird'), Caption('dog')), Or(Caption('cat'), Caption('banana'))),
        )
        self.assertEqual(
            parser.tokenize.parse('((caption:bird OR caption:dog) AND (caption:cat caption:banana))'),
            ['(', '(', Caption('bird'), 'OR', Caption('dog'), ')', 'AND', '(', Caption('cat'), Caption('banana'), ')', ')'],
        )
        self.assertEqual(
            parser.parse('((caption:bird OR caption:dog) AND (caption:cat caption:banana))'),
            And(Or(Caption('bird'), Caption('dog')), Or(Caption('cat'), Caption('banana'))),
        )

    def testParserShouldSupportNegatedParentheses(self):
        self.assertEqual(parser.tokenize.parse('-(caption:bird)'), ['-', '(', Caption('bird'), ')'])
        self.assertEqual(parser.parse('-(caption:bird)'), Not(Caption('bird')))
        self.assertEqual(
            parser.tokenize.parse('caption:bird AND -(caption:dog OR caption:cat) AND caption:banana'),
            [Caption('bird'), 'AND', '-', '(', Caption('dog'), 'OR', Caption('cat'), ')', 'AND', Caption('banana')],
        )
        self.assertEqual(
            parser.parse('caption:bird AND -(caption:dog OR caption:cat) AND caption:banana'),
            And(And(Caption('bird'), Not(Or(Caption('dog'), Caption('cat')))), Caption('banana')),
        )
        self.assertEqual(
            parser.tokenize.parse('-(caption:bird OR caption:dog) AND (-caption:cat OR caption:banana)'),
            ['-', '(', Caption('bird'), 'OR', Caption('dog'), ')', 'AND', '(', '-', Caption('cat'), 'OR', Caption('banana'), ')'],
        )
        self.assertEqual(
            parser.parse('-(caption:bird OR caption:dog) AND (-caption:cat OR caption:banana)'),
            And(Not(Or(Caption('bird'), Caption('dog'))), Or(Not(Caption('cat')), Caption('banana'))),
        )

    def testParserShouldNotTripOverExtraneousSpacesAndRandomStuff(self):
        self.assertEqual(parser.tokenize.parse('((caption:bird))'), ['(', '(', Caption('bird'), ')', ')'])
        self.assertEqual(parser.parse('((caption:bird))'), Caption('bird'))
        self.assertEqual(
            parser.tokenize.parse(' -( caption:bird OR caption:dog  )AND(- caption:cat OR caption:banana) '),
            ['-', '(', Caption('bird'), 'OR', Caption('dog'), ')', 'AND', '(', '-', Caption('cat'), 'OR', Caption('banana'), ')'],
        )
        self.assertEqual(
            parser.parse(' -( caption:bird OR caption:dog  )AND(- caption:cat OR caption:banana) '),
            And(Not(Or(Caption('bird'), Caption('dog'))), Or(Not(Caption('cat')), Caption('banana'))),
        )

    def testParserShouldNotDieDueToUnmatchedParens(self):
        with self.assertRaises(parser.UnexpectedParenthesis) as cm:
            parser.parse('caption:bird OR caption:dog) AND (-caption:cat OR caption:banana)')
        self.assertEqual(cm.exception.index, 3)

        with self.assertRaises(parser.ExpectedParenthesis):
            parser.parse('(caption:bird OR caption:dog) AND (-caption:cat OR caption:banana')

        with self.assertRaises(parser.UnexpectedParenthesis):
            parser.parse('() AND (-caption:cat OR caption:banana')


from archive.templatetags import timeline
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


