from fortepan_us.kronofoto.templatetags.widgets import image_url
from django.test import Client, RequestFactory, TestCase
from django.core.files.storage import default_storage
from .util import small_gif
from django.core.files.base import ContentFile

class ImageUrlTest(TestCase):
    def test_image_url(self):
        c = ContentFile(small_gif)
        default_storage.save('img', c)
        url = image_url(id=1000, path="img", width=100, height=100)[len("//example.com"):]
        client = Client()
        resp = client.get(url)
        assert resp.status_code == 200
        resp = client.get(url[:-1])
        assert resp.status_code == 404
