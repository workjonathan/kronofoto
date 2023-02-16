from django.test import TestCase, SimpleTestCase, tag
from ..views import EMPTY_PNG, FAKE_PHOTO, FakeTimelinePage, TimelinePaginator
from ..views.paginator import KeysetPaginator
from ..models.photo import Photo
from hypothesis.extra.django import TestCase as HypoTestCase
from hypothesis import given, settings as hyposettings, HealthCheck
from hypothesis import strategies as st
from .util import photos, donors, archives

class PaginatorTest(HypoTestCase):
    @given(
        st.integers(min_value=1, max_value=3),
        st.lists(
            archives().flatmap(lambda archive: donors(archive=st.just(archive)).flatmap((lambda donor:
                photos(
                    year=st.integers(min_value=1850, max_value=1990),
                    is_published=st.just(True),
                    donor=st.just(donor),
                    archive=st.just(archive),
                )))),
            min_size=1,
            max_size=6,
        ).flatmap(lambda photos: st.sampled_from(photos)),
    )
    def testPaginator(self, page_size, photo):
        paginator = KeysetPaginator(Photo.objects.all().order_by('year', 'id'), per_page=page_size)
        page = paginator.get_page(dict(year=photo.year, id=photo.id-1, reverse=False))
        if page.has_next() and page.has_previous():
            self.assertEqual(len(page), page_size)
        if page.has_previous():
            page2 = paginator.get_page(paginator.get_page(page.previous_page_number()).next_page_number())
            for (p1, p2) in zip(page, page2):
                self.assertEqual(p1.id, p2.id)
        if page.has_next():
            page2 = paginator.get_page(paginator.get_page(page.next_page_number()).previous_page_number())
            for (p1, p2) in zip(page, page2):
                self.assertEqual(p1.id, p2.id)

@tag("fast")
class FakeImageTest(SimpleTestCase):
    def testShouldHaveThumbnail(self):
        self.assertEqual(FAKE_PHOTO['thumbnail']['url'], EMPTY_PNG)

    def testShouldHaveWidth(self):
        self.assertEqual(FAKE_PHOTO['thumbnail']['width'], 75)

    def testShouldHaveHeight(self):
        self.assertEqual(FAKE_PHOTO['thumbnail']['height'], 75)

@tag("fast")
class FakeTimelinePageTest(SimpleTestCase):
    def testShouldNotHavePhotos(self):
        self.assertEqual(len(list(FakeTimelinePage())), 0)

    def testShouldHaveAnObjectListWithTenFakePhotos(self):
        self.assertEqual(len(list(FakeTimelinePage().object_list)), 10)

@tag("fast")
class TimelinePaginatorTest(TestCase):
    def testInvalidPageShouldGetFakePage(self):
        page = TimelinePaginator([], per_page=10).get_page(2)
        for photo in page.object_list:
            self.assertEqual(photo['thumbnail']['url'], EMPTY_PNG)
