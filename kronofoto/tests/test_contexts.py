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
from archive.views.photo import PhotoView
from django.core.files.uploadedfile import SimpleUploadedFile
from .util import photos, donors, archives, small_gif

@given(photo=st.integers(min_value=1, max_value=100000))
def test_photo_hx_context(photo):
    request = RequestFactory().get(reverse('kronofoto:photoview', kwargs={'photo': photo}))
    photoview = PhotoView()
    photoview.request = request
    photoview.kwargs = {}
    from unittest.mock import patch
    with patch('django.template.loader.select_template') as mock:
        photoview.get_hx_context()
        assert mock.called_with(['archive/base.html'])

@given(photo=st.integers(min_value=1, max_value=100000))
def test_photo_hx_context_swap(photo):
    request = RequestFactory().get(reverse('kronofoto:photoview', kwargs={'photo': photo}), HTTP_HX_TARGET='fi-image-tag')
    photoview = PhotoView()
    photoview.request = request
    assert photoview.get_hx_context()['base_template'] == 'archive/photo_partial.html'


class Tests(TestCase):

    @settings(deadline=1000, max_examples=20)
    @given(
        user=from_model(User, is_staff=st.booleans()),
        data=st.data()
    )
    def test_photo_user_context(self, user, data):
        archive = Archive.objects.create()
        donor = Donor.objects.create(archive=archive)
        photo = Photo.objects.create(archive=archive, donor=donor, is_published=True, year=1900, original=SimpleUploadedFile('small.gif', small_gif, content_type='image/gif'), h700=SimpleUploadedFile('small.gif', small_gif, content_type='image/gif'), thumbnail=SimpleUploadedFile('small.gif', small_gif, content_type='image/gif'))
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


    @settings(max_examples=1, deadline=300)
    @given(photo=photos(donor=donors(archive=archives()), is_published=st.just(True), year=st.integers(min_value=1900, max_value=1950)))
    def test_photo_context(self, photo):
        request = RequestFactory().get(reverse('kronofoto:photoview', kwargs={'photo': photo.id}))
        request.user = AnonymousUser()
        resp = PhotoView.as_view(
            get_object=Mock(return_value=photo),
            get_hx_context=Mock(return_value={'hxstuff': True}),
        )(request)
        assert resp.status_code == 200
        assert 'photo' in resp.context_data
        assert resp.context_data['hxstuff']
        assert resp.context_data['photo'].id == photo.id
        assert 'carousel_has_prev' in resp.context_data
        assert 'carousel_has_next' in resp.context_data


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
        resp = Client().get(reverse('kronofoto:mainstreetview', kwargs={'pk': pair.id}))
        assertTemplateUsed(resp, 'archive/photosphere_detail.html')
        assert resp.status_code == 200
        assert 'sphere_data' in resp.context


    @settings(max_examples=1)
    @given(photo=photos(donor=donors(archive=archives()), is_published=st.just(True), year=st.integers(min_value=1900, max_value=1950)))
    def test_randomimage_context(self, photo):
        resp = Client().options('/kf/', HTTP_ACCESS_CONTROL_REQUEST_HEADERS="embedded")
        assert resp.status_code == 200
        resp = Client().options('/kf/')
        assert resp.status_code == 302
