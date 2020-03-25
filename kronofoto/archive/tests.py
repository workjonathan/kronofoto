from django.test import TestCase
from . import models
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

class WhenHave50Photos(TestCase):
    @classmethod
    def setUpTestData(cls):
        coll = models.Collection.objects.create(name='test collection')
        cls.photos = []
        for y in range(1900, 1950):
            p = models.Photo.objects.create(
                original=SimpleUploadedFile(
                    name='test_img.jpg',
                    content=open('testdata/test.jpg', 'rb').read(),
                    content_type='image/jpeg'),
                collection=coll,
                year=y,
                is_published=True,
            )
            cls.photos.append(p)


    def testShouldRedirectToCorrectPageForPhoto(self):
        photos = self.photos
        for page in range(1, 6):
            thispage = photos[:10]
            photos = photos[10:]
            for photo in thispage:
                resp = self.client.get(reverse('photoview', kwargs={'page': page % 5 + 1, 'photo':photo.accession_number}))
                self.assertRedirects(resp, reverse('photoview', kwargs={'page': page, 'photo':photo.accession_number}))
