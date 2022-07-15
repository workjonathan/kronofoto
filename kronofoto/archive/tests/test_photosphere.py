from django.test import TestCase, tag
from django.core.files.uploadedfile import SimpleUploadedFile
from .util import TestImageMixin
from ..models import PhotoSphere

class PhotoSpherePairTest(TestImageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.photo = cls.createPhoto()
        cls.photosphere = PhotoSphere.objects.create(
            image=SimpleUploadedFile(
                name="photosphere.jpg",
                content=cls.test_img,
                content_type="image/jpeg",
            ),
            heading=235.5,
            location="POINT(-92.46 42.515)",
        )
        cls.pair = PhotoSphere.photos.through.objects.create(
            photo=cls.photo, photosphere=cls.photosphere, azimuth=90, inclination=4, distance=550
        )

    def test_test(self): # low quality test
        self.assertEqual(self.photosphere.heading, 235.5)
        self.assertEqual(self.photosphere.photospherepair_set.all()[0].azimuth, 90)
        self.assertTrue(self.photosphere.photos.all()[0].is_published)
