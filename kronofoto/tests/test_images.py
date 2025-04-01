from fortepan_us.kronofoto.templatetags.widgets import image_url
from django.test import Client, RequestFactory, TestCase
from django.core.files.storage import default_storage
from .util import small_gif, a_photo, a_category, an_archive
from django.core.files.base import ContentFile
from unittest.mock import Mock
import pytest

@pytest.mark.django_db()
def test_image_url(a_photo):
    url = image_url(photo=a_photo, width=100, height=100)[len("//example.com"):]
    client = Client()
    resp = client.get(url)
    assert resp.status_code == 200
    resp = client.get(url[:-1])
    assert resp.status_code == 404
