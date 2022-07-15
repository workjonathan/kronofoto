from django.test import TestCase, SimpleTestCase, tag
from ..views import EMPTY_PNG, FAKE_PHOTO, FakeTimelinePage, TimelinePaginator

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
