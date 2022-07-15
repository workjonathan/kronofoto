from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Photo, Donor


class TestImageMixin:
    @classmethod
    def setUpClass(cls):
        with open('testdata/test.jpg', 'rb') as f:
            cls.test_img = f.read()
        super().setUpClass()

    @classmethod
    def createPhoto(cls, is_published=True, year=1950, donor=None, **kwargs):
        donor = donor or Donor.objects.create(last_name='last', first_name='first')
        return Photo.objects.create(
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
