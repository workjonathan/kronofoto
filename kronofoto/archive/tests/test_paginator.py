from django.test import TestCase, SimpleTestCase, tag
from ..views import EMPTY_PNG, FAKE_PHOTO, FakeTimelinePage, TimelinePaginator
from ..views.paginator import KeysetPaginator
from ..models.photo import Photo
from hypothesis.extra.django import TestCase as HypoTestCase
from hypothesis import given, settings as hyposettings, HealthCheck, note
from hypothesis import strategies as st
from .util import photos, donors, archives, MockQuerySet, MockPhoto

@tag('newtests')
class Paginator2Test(HypoTestCase):
    @given(st.builds(MockQuerySet, st.lists(st.builds(MockPhoto), min_size=1, unique_by=lambda p: p.id)), st.integers(min_value=1))
    def testForwardConsistency(self, qs, page_size):
        note(qs)
        qs.sort()
        paginatorA = KeysetPaginator(qs, page_size)
        paginatorB = KeysetPaginator(qs, page_size*2)
        pageA = paginatorA.get_page({})
        if pageA.has_next():
            pageA = paginatorA.get_page(pageA.next_page_number())
            if pageA.has_next():
                pageA = paginatorA.get_page(pageA.next_page_number())
                pageAPhoto = pageA[0]
            else:
                pageAPhoto = None
        else:
            pageAPhoto = None
        pageB = paginatorB.get_page({})
        if pageB.has_next():
            pageB = paginatorB.get_page(pageB.next_page_number())
            pageBPhoto = pageB[0]
        else:
            pageBPhoto = None
        self.assertEqual(pageAPhoto, pageBPhoto)

    @given(st.builds(MockQuerySet, st.lists(st.builds(MockPhoto), min_size=1, unique_by=lambda p: p.id)), st.integers(min_value=1))
    def testBackwardConsistency(self, qs, page_size):
        note(qs)
        qs.sort()
        paginatorA = KeysetPaginator(qs, page_size)
        paginatorB = KeysetPaginator(qs, page_size*2)
        pageA = paginatorA.get_page(paginatorA.num_pages)
        if pageA.has_previous():
            pageA = paginatorA.get_page(pageA.previous_page_number())
            if pageA.has_previous():
                pageA = paginatorA.get_page(pageA.previous_page_number())
                pageAPhoto = pageA[-1]
            else:
                pageAPhoto = None
        else:
            pageAPhoto = None
        pageB = paginatorB.get_page(paginatorB.num_pages)
        if pageB.has_previous():
            pageB = paginatorB.get_page(pageB.previous_page_number())
            pageBPhoto = pageB[-1]
        else:
            pageBPhoto = None
        self.assertEqual(pageAPhoto, pageBPhoto)

    @given(st.builds(MockQuerySet, st.lists(st.builds(MockPhoto), min_size=10, unique_by=lambda p: p.id)), st.integers(min_value=1), st.fixed_dictionaries({'reverse': st.booleans(), 'id': st.integers(), 'year': st.integers()}))
    def testBothDirectionsConsistency(self, qs, page_size, first_page):
        note(qs)
        qs.sort()
        paginator = KeysetPaginator(qs, page_size)
        page = paginator.get_page(first_page)
        if page.has_next():
            page2 = paginator.get_page(page.next_page_number())
            if page2.has_next():
                page2 = paginator.get_page(page.next_page_number())
                self.assertTrue(page2.has_previous())
                same_page = paginator.get_page(page2.previous_page_number())
                self.assertEqual(page[0], same_page[0])


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
