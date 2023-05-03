from django.test import TestCase, SimpleTestCase, tag
from archive.views import EMPTY_PNG, FAKE_PHOTO, FakeTimelinePage, TimelinePaginator
from archive.views.paginator import KeysetPaginator
from archive.models.photo import Photo
from hypothesis.extra.django import TestCase as HypoTestCase
from hypothesis import given, settings as hyposettings, HealthCheck, note
from hypothesis import strategies as st
from .util import photos, donors, archives, MockQuerySet, MockPhoto

@tag('newtests')
class Paginator2Test(SimpleTestCase):
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

    @given(st.builds(MockQuerySet, st.lists(st.builds(MockPhoto), min_size=1, unique_by=lambda p: p.id)), st.integers(min_value=1), st.fixed_dictionaries({'reverse': st.booleans(), 'id': st.integers(), 'year': st.integers()}))
    def testBothDirectionsConsistency(self, qs, page_size, first_page):
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


