from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Photo, Donor
from django.core.files.uploadedfile import SimpleUploadedFile
from hypothesis.extra.django import from_model
from hypothesis import strategies as st

small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)

donors = lambda: from_model(Donor)

def photos(**kwargs):
    return from_model(
        Photo,
        original=st.builds(
            lambda: SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        ),
        h700=st.builds(
            lambda: SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        ),
        thumbnail=st.builds(
            lambda: SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        ),
        **kwargs,
    )

class TestImageMixin:
    @classmethod
    def setUpClass(cls):
        cls.test_img = small_gif
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
