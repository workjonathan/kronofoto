from django.test.utils import override_settings
from django.test import Client, RequestFactory
from django.http import Http404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import AnonymousUser, User, Permission
from django.urls import reverse
from hypothesis.extra.django import from_model, register_field_strategy, TestCase
from unittest.mock import Mock
from hypothesis import strategies as st, given, note, settings
import pytest
from pytest_django.asserts import assertTemplateUsed, assertRedirects
from archive.models.photo import Photo
from archive.models.photosphere import PhotoSphere
from archive.models.archive import Archive
from archive.models.donor import Donor
from archive.models import Category
from archive.views.photo import PhotoView
from django.core.files.uploadedfile import SimpleUploadedFile
from .util import photos, donors, archives, small_gif

class Tests(TestCase):

    @settings(deadline=1000, max_examples=5)
    @given(
        user=from_model(User, is_staff=st.booleans()),
        data=st.data()
    )
    def test_photo_user_context(self, user, data):
        archive = Archive.objects.create()
        donor = Donor.objects.create(archive=archive)
        category = Category.objects.create()
        photo = Photo.objects.create(archive=archive, donor=donor, category=category, is_published=True, year=1900, original=SimpleUploadedFile('small.gif', small_gif, content_type='image/gif'))
        permissions = data.draw(st.lists(st.sampled_from(list(Permission.objects.all().order_by('id')))))
        user.user_permissions.add(*permissions)
        from archive.templatetags.permissions import has_view_or_change_permission
        has_perm = has_view_or_change_permission(user, photo)
        note(f'{user.is_staff=}')
        client = Client()
        client.force_login(user)
        if has_perm:
            assert client.get(photo.get_edit_url()[13:]).status_code == 200
        elif user.is_staff:
            assert client.get(photo.get_edit_url()[13:]).status_code == 403
        else:
            assert client.get(photo.get_edit_url()[13:]).status_code == 302


    @settings(max_examples=5)
    @given(archive=archives(), id=st.integers(min_value=1, max_value=100000))
    def test_photo_get_object(self, archive, id):
        photoview = PhotoView()
        photoview.kwargs = {'photo': id}
        if Archive.objects.filter(id=id).exists():
            assert id == photoview.get_object(Archive.objects.all()).id
        else:
            with pytest.raises(Http404):
                photoview.get_object(Archive.objects.all())



    @settings(max_examples=1)
    @given(from_model(PhotoSphere.photos.through, photo=photos(), photosphere=from_model(PhotoSphere, id=st.none(), image=st.builds(lambda: SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')))))
    def test_photosphere_context(self, pair):
        resp = Client().get(f"{reverse('kronofoto:mainstreetview')}?id={pair.id}")

        assertTemplateUsed(resp, 'archive/photosphere_detail.html')
        assert resp.status_code == 200
        assert 'object' in resp.context and resp.context['object'].id == pair.photosphere.id
