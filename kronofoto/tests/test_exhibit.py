from django.test import Client, RequestFactory
import pytest
from pytest_django.asserts import assertTemplateUsed, assertRedirects, assertHTMLEqual
from django.urls import reverse
from fortepan_us.kronofoto.models import Exhibit
from .util import photos, donors, archives, small_gif, a_photo, a_category, an_archive, a_photosphere, a_photosphere_pair
from django.contrib.auth.models import User
from django.template.loader import render_to_string

@pytest.fixture
def user():
    return User.objects.create_user(username="test_user")

@pytest.fixture
def exhibit(user, a_photo):
    return Exhibit.objects.create(
        photo=a_photo,
        owner=user,
    )

@pytest.mark.django_db
def test_exhibit_delete_context(a_photo, user, exhibit):
    client = Client()
    client.force_login(user)
    url = "/"
    resp = client.get(reverse("kronofoto:exhibit-delete", kwargs={"pk": exhibit.pk}))
    assert resp.status_code == 200
    assert exhibit == resp.context['exhibit']
    assertTemplateUsed(resp, "kronofoto/pages/exhibit-delete.html")

@pytest.mark.django_db
def test_exhibit_delete_deletes_exhibit(a_photo, user, exhibit):
    client = Client()
    client.force_login(user)
    url = "/"
    resp = client.post(reverse("kronofoto:exhibit-delete", kwargs={"pk": exhibit.pk}))
    assert resp.status_code == 302
    assertRedirects(resp, "//example.com/kf/users/test_user", fetch_redirect_response=False)
    assert Exhibit.objects.filter(pk=exhibit.pk).count() == 0
