from django.test import TestCase, tag, RequestFactory
from django.urls import reverse
from django.conf import settings
from django.http import QueryDict
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.utils.http import urlencode
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from os.path import join
from ..views.paginator import KeysetPaginator
from ..models import Photo, Term, Tag, CollectionQuery, Donor, Collection
from .util import TestImageMixin, photos, donors
from archive.search.expression import TagExactly

@tag("fast")
class PhotoTest(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.photo = cls.createPhoto()

    def testShouldDescribeItself(self):
        Photo.tags.through.objects.create(tag=Tag.objects.create(tag="dog"), photo=self.photo, accepted=True)
        Photo.tags.through.objects.create(tag=Tag.objects.create(tag="cat"), photo=self.photo, accepted=True)
        Photo.tags.through.objects.create(tag=Tag.objects.create(tag="car"), photo=self.photo, accepted=False)
        self.photo.terms.add(Term.objects.create(term="Animals"))
        self.photo.terms.add(Term.objects.create(term="Portraits"))
        self.photo.city = "Cedar Falls"
        self.photo.state = "IA"
        self.photo.county = "Black Hawk"
        self.photo.country = "USA"
        self.assertEqual(self.photo.describe(), {"dog", "cat", "Animals", "Portraits", "Cedar Falls, IA", "last, first", "history of Iowa", "Iowa", "Iowa History"})

    def testShouldNotAppearTwiceWhenTwoUsersSubmitSameTag(self):
        user = User.objects.create_user('testuser', 'user@email.com', 'testpassword')
        user2 = User.objects.create_user('testuser2', 'user@email.com', 'testpassword')
        photo = self.photo
        tag = Tag.objects.create(tag="test tag")
        phototag = Photo.tags.through.objects.create(tag=tag, photo=photo, accepted=True)
        phototag.creator.add(user2)
        phototag.creator.add(user)
        phototag.save()
        photo.save()
        self.assertEqual(Photo.objects.filter_photos(CollectionQuery(TagExactly("test tag"), user)).count(), 1)
        self.assertEqual(photo.get_accepted_tags().count(), 1)

    def testShouldEnforceUUIDFilename(self):
        photo = self.photo
        photo.original.save('badname.png', ContentFile(self.test_img))
        self.assertEqual(photo.original.path, join(settings.MEDIA_ROOT, 'original', '{}.jpg'.format(photo.uuid)))

    @tag("fast")
    def testShouldDisallowYearsBefore1800(self):
        photo = Photo(year=1799)
        with self.assertRaises(ValidationError) as cm:
            year = photo.clean_fields()
        self.assertIn('year', cm.exception.message_dict)

    @tag("fast")
    def testCityURL(self):
        photo = Photo(city='CityName', state='StateName')
        self.assertEqual(photo.get_city_url(), '{}?{}'.format(reverse('kronofoto:gridview'), urlencode({'city': photo.city, 'state': photo.state})))

    @tag("fast")
    def testCountyURL(self):
        photo = Photo(county='CountyName', state='StateName')
        self.assertEqual(photo.get_county_url(), '{}?{}'.format(reverse('kronofoto:gridview'), urlencode({'county': photo.county, 'state': photo.state})))

    def testShouldNotAllowGuestsToTagPhotos(self):
        resp = self.client.get(reverse('kronofoto:addtag', kwargs={'photo': self.photo.id}))
        self.assertEqual(resp.status_code, 302)

        resp = self.client.post(reverse('kronofoto:addtag', kwargs={'photo': self.photo.id}), {'tag': 'test tag'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(self.photo.get_proposed_tags()), 0)
        self.assertEqual(len(self.photo.get_accepted_tags()), 0)

    def testShouldBeAbleToTagPhotos(self):
        User.objects.create_user('testuser', 'user@email.com', 'testpassword')
        self.client.login(username='testuser', password='testpassword')
        resp = self.client.get(reverse('kronofoto:addtag', kwargs={'photo': self.photo.id}))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(reverse('kronofoto:addtag', kwargs={'photo': self.photo.id}), { 'tag': 'test tag'})
        self.assertEqual(len(self.photo.get_proposed_tags()), 1)
        self.assertEqual(self.photo.get_proposed_tags()[0].tag, 'test tag')
        self.assertEqual(len(self.photo.get_accepted_tags()), 0)

    def testShould404WhenPhotoNotFound(self):
        resp = self.client.get(reverse('kronofoto:photoview', kwargs={'photo': 99999}))
        self.assertEqual(resp.status_code, 404)

    def testShouldHaveUniqueDownloadPage(self):
        self.assertEqual(self.photo.get_download_page_url(), reverse('kronofoto:download', kwargs={'pk': self.photo.id}))
        resp = self.client.get(reverse('kronofoto:download', kwargs={'pk': self.photo.id}))
        self.assertEqual(resp.status_code, 200)
        templates = {template.name for template in resp.templates}
        self.assertIn('archive/download-page.html', templates)
        self.assertIn('archive/base.html', templates)
        self.assertEqual(resp.context['host_uri'], settings.HOST_URI)

    def testShouldHaveSearchFiltersOnDownloadUrl(self):
        self.assertEqual(self.photo.get_download_page_url(params=QueryDict('a=1')), reverse('kronofoto:download', kwargs={'pk': self.photo.id}) + '?a=1')


class WhenHave50Photos(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        Site.objects.update(domain='127.0.0.1:8000')
        Site.objects.clear_cache()
        cls.donor = donor = Donor.objects.create(
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
            Photo.county_index(),
            [
                {'name': 'county0, state0', 'count': 1, 'href': self.photos[2].get_county_url()},
                {'name': 'county1, state1', 'count': 2, 'href': self.photos[0].get_county_url()},
                {'name': 'county2, state2', 'count': 2, 'href': self.photos[1].get_county_url()},
            ]
        )

    def testCityIndex(self):
        self.assertEqual(
            Photo.city_index(),
            [
                {'name': 'city0, state0', 'count': 1, 'href': self.photos[2].get_city_url()},
                {'name': 'city1, state1', 'count': 2, 'href': self.photos[0].get_city_url()},
                {'name': 'city2, state2', 'count': 2, 'href': self.photos[1].get_city_url()},
            ]
        )

    def testDonorIndex(self):
        self.assertEqual(
            Donor.index(),
            [
                {'name': 'last, first', 'count': 5, 'href': self.donor.get_absolute_url()},
            ]
        )

    def testTermIndex(self):
        endswithzero = Term.objects.create(term="new decade")
        even = Term.objects.create(term="even year")
        no = Term.objects.create(term="none")
        for photo in self.photos:
            if photo.year % 2 == 0:
                photo.terms.add(even)
            if photo.year % 10 == 0:
                photo.terms.add(endswithzero)
        self.assertEqual(
            Term.index(),
            [
                {'name': 'even year', 'count': 3, 'href': even.get_absolute_url()},
                {'name': 'new decade', 'count': 1, 'href': endswithzero.get_absolute_url()},
            ],
        )

    def testTagIndex(self):
        endswithzero = Tag.objects.create(tag="new decade")
        eventag = Tag.objects.create(tag="even year")
        notags = Tag.objects.create(tag="none")
        for photo in self.photos:
            if photo.year % 2 == 0:
                Photo.tags.through.objects.create(tag=eventag, photo=photo, accepted=True)
            if photo.year % 10 == 0:
                Photo.tags.through.objects.create(tag=endswithzero, photo=photo, accepted=True)
            elif photo.year % 3 == 0:
                Photo.tags.through.objects.create(tag=endswithzero, photo=photo, accepted=False)
        self.assertEqual(
            Tag.index(),
            [
                {'name': 'even year', 'count': 3, 'href': eventag.get_absolute_url()},
                {'name': 'new decade', 'count': 1, 'href': endswithzero.get_absolute_url()},
            ],
        )

    def testYearIndex(self):
        for i, photo in enumerate(Photo.objects.year_index()):
            self.assertEqual(photo.row_number, i)
            self.assertEqual(photo.page_number(), i//10 + 1)


    def testGridViewShouldDisplayAllPhotosInOrder(self):
        photo_ids = {photo.id for photo in self.photos}
        currentpage = 1
        resp = self.client.get(reverse('kronofoto:gridview'))
        last = None
        while True:
            for photo in resp.context['page_obj']:
                self.assertIn(photo.id, photo_ids)
                if last:
                    self.assertTrue(last.year < photo.year)
                last = photo

                photo_ids.remove(photo.id)
            if not resp.context['page_obj'].has_next():
                break
            else:
                resp = self.client.get(reverse('kronofoto:gridview'), resp.context.next_page_number())
        self.assertEqual(len(photo_ids), 0)

    def testGridShouldRespectTermFilters(self):
        term = Term.objects.create(term="test term")
        photos = [self.photos[2], self.photos[3], self.photos[1]]
        for photo in photos:
            photo.terms.add(term)
        resp = self.client.get(term.get_absolute_url())
        self.assertEqual(len(resp.context['page_obj']), len(photos))
        our_ids = {photo.id for photo in photos}
        got_ids = {photo.id for photo in resp.context['page_obj']}
        self.assertEqual(our_ids, got_ids)

    def testGridShouldHandleNonexistantTags(self):
        tag = Tag.objects.create(tag="silly")
        photos = [self.photos[2], self.photos[0], self.photos[3]]
        for photo in photos:
            Photo.tags.through.objects.create(tag=tag, photo=photo, accepted=True)
        resp = self.client.get(reverse('kronofoto:gridview'), {'tag': "lakdsjflkasdf"})
        self.assertEqual(len(resp.context['page_obj']), 0)

    def testGridShouldRespectTagFilters(self):
        tag = Tag.objects.create(tag="test tag")
        photos = [self.photos[2], self.photos[0], self.photos[3]]
        for photo in photos:
            Photo.tags.through.objects.create(tag=tag, photo=photo, accepted=True)
        resp = self.client.get(tag.get_absolute_url())
        self.assertEqual(len(resp.context['page_obj']), len(photos))
        our_ids = {photo.id for photo in photos}
        got_ids = {photo.id for photo in resp.context['page_obj']}
        self.assertEqual(our_ids, got_ids)

    def testFilteringShouldNotShowUnapprovedTags(self):
        tag = Tag.objects.create(tag="silly")
        photos = [self.photos[0]]
        for photo in photos:
            Photo.tags.through.objects.create(tag=tag, photo=photo, accepted=True)
        tag = Tag.objects.create(tag="test tag")
        photos = [self.photos[2], self.photos[1], self.photos[4]]
        for photo in photos:
            Photo.tags.through.objects.create(tag=tag, photo=photo, accepted=False)
        resp = self.client.get(reverse('kronofoto:gridview'), {'tag': tag.slug})
        self.assertEqual(len(resp.context['page_obj']), 0)

    def testUserProfile(self):
        users = [
            User.objects.create_user('testuser', 'user@email.com', 'testpassword'),
            User.objects.create_user('testuser2', 'user@email.com', 'testpassword'),
        ]
        collections = []
        i = 0
        for user in users:
            for privacy in Collection.PRIVACY_TYPES:
                coll = Collection.objects.create(
                    name='test collection{}'.format(i),
                    owner=user,
                    visibility=privacy[0],
                )
                coll.photos.set(self.photos[i:i+4])
                collections.append(coll)
                i += 4
        self.client.login(username='testuser', password='testpassword')
        resp = self.client.get(reverse('kronofoto:user-page', args=['testuser']))
        self.assertEqual(len(resp.context['object_list']), 3)
        for collection in resp.context['object_list']:
            self.assertEqual(collection.owner.get_username(), 'testuser')

        resp = self.client.get(reverse('kronofoto:user-page', args=['testuser2']))
        self.assertEqual(len(resp.context['object_list']), 1)
        for collection in resp.context['object_list']:
            self.assertEqual(collection.owner.get_username(), 'testuser2')

    def testUserProfileShould404IfUserDoesNotExist(self):
        resp = self.client.get(reverse('kronofoto:user-page', kwargs=dict(username='notarealuser')))
        self.assertEqual(resp.status_code, 404)
