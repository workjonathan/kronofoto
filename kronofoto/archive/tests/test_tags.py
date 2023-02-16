from django.test import TestCase, tag
from .. import models
from .util import TestImageMixin
from django.utils.http import urlencode
from django.urls import reverse


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
class TagTest(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.photo = cls.createPhoto()

    def testSubstringSearchShouldNotReturnTooManyThings(self):
        photo = self.photo
        for x in range(11):
            tag = models.Tag.objects.create(tag="test tag {}".format(x))
            models.PhotoTag.objects.create(tag=tag, photo=photo, accepted=True)
        obj = self.client.get(reverse('kronofoto:tag-search'), dict(term='tag')).json()
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

        obj = self.client.get(reverse('kronofoto:tag-search'), dict(term='tag')).json()

        self.assertEqual(len(obj), 3)

    def testSubstringSearchShouldOnlyReturnAcceptedTags(self):
        photo = self.photo
        tag1 = models.Tag.objects.create(tag="test tag")
        models.PhotoTag.objects.create(tag=tag1, photo=photo, accepted=True)

        tag2 = models.Tag.objects.create(tag="j tag 1")
        tag3 = models.Tag.objects.create(tag="a tag 2")
        tag4 = models.Tag.objects.create(tag="dog")

        obj = self.client.get(reverse('kronofoto:tag-search'), dict(term='tag')).json()

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
        self.assertEqual(tag.get_absolute_url(), "{}?{}".format(reverse('kronofoto:gridview'), urlencode({'tag': tag.tag})))

    @tag("fast")
    def testShouldEnforceLowerCase(self):
        tag = models.Tag.objects.create(tag='CAPITALIZED')
        tag.refresh_from_db()
        self.assertEqual(tag.tag, 'capitalized')


