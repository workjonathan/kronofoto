from django.test import Client, RequestFactory, SimpleTestCase
from hypothesis import given, strategies as st, note
from hypothesis.extra.django import TestCase
from io import BytesIO
from unittest.mock import Mock, sentinel, MagicMock
from django.contrib.admin.sites import AdminSite
from archive.admin import *
from archive.models.donor import Donor
from archive.models.archive import Archive
from archive.models.photo import Photo
from archive.models.photosphere import PhotoSphere
from .util import donors, small_gif
from django.core.files.uploadedfile import SimpleUploadedFile

def test_queryset():
    model = Mock()
    qs = Mock(spec=Donor.objects)
    qs.annotate_scannedcount.return_value = qs
    qs.annotate_donatedcount.return_value = qs
    model._default_manager.get_queryset.return_value = qs
    admin = DonorAdmin(model=model, admin_site=AdminSite())
    request = RequestFactory().get('/')
    request.user = Mock()
    qs = admin.get_queryset(request)
    qs.annotate_scannedcount.assert_called_once_with()
    qs.annotate_donatedcount.assert_called_once_with()

@given(count=st.integers(min_value=0))
def test_scanned(count):
    model = Mock()
    admin = DonorAdmin(model=model, admin_site=AdminSite())
    obj = Mock()
    obj.scanned_count = count
    c, photos = admin.scanned(obj).split(' ')
    assert int(c) == count
    assert photos == 'photos'

@given(count=st.integers(min_value=0))
def test_donated(count):
    model = Mock()
    admin = DonorAdmin(model=model, admin_site=AdminSite())
    obj = Mock()
    obj.donated_count = count
    c, photos = admin.donated(obj).split(' ')
    assert int(c) == count
    assert photos == 'photos'

def test_tag_fields():
    model = Mock()
    admin = TagAdmin(model=model, admin_site=AdminSite())
    request = RequestFactory().get('/')
    fields = admin.get_readonly_fields(request)
    assert 'tag' not in fields
    fields = admin.get_readonly_fields(request, True)
    assert 'tag' in fields

def test_standardsimplelistfilter_lookups():
    model = Mock()
    ma = PhotoAdmin(model=model, admin_site=AdminSite())
    request = RequestFactory().get('/')
    class TestFilter(StandardSimpleListFilter):
        title = "title"
        parameter_name = "pm"
        field = "testfield"
        filters = (
            ("one", 1),
            ("two", 2),
            ("three", 3),
        )
    filter = TestFilter(request=request, params={}, model=model, model_admin=ma)
    choices = dict(filter.lookup_choices)
    for (k, v) in TestFilter.filters:
        assert k in choices
        assert choices[k] == k
        filter = TestFilter(request=request, params={'pm': k}, model=model, model_admin=ma)
        qs = Mock()
        filter.queryset(request, qs)
        qs.filter.assert_called_once_with(testfield=v)

def test_standard_filters():
    for cls in (TagFilter, YearIsSetFilter, IsPublishedFilter):
        for k, v in cls.filters:
            Photo.objects.filter(**{cls.field: v})

def test_execute_filters():
    model = Mock()
    ma = PhotoAdmin(model=model, admin_site=AdminSite())
    request = RequestFactory().get('/')
    for filter in (HasLocationFilter, HasGeoLocationFilter):
        lookups = filter(request=request, params={}, model=model, model_admin=ma).lookups(request, ma)
        for (lookup, title) in lookups:
            qs = filter(request=request, params={filter.parameter_name: lookup}, model=model, model_admin=ma).queryset(request, Photo.objects.all())

def test_mass_publish():
    model = Mock()
    ma = PhotoAdmin(model=model, admin_site=AdminSite())
    request = RequestFactory().get('/')
    qs = Mock(spec=Photo.objects)
    publish_photos(ma, request, qs)
    qs.update.assert_called_once_with(is_published=True)
    call_args = qs.update.call_args
    Photo.objects.filter(*call_args.args, **call_args.kwargs)


def test_mass_publish_error():
    model = Mock()
    ma = PhotoAdmin(model=model, admin_site=AdminSite())
    request = RequestFactory().get('/')
    qs = Mock()
    qs.update.side_effect = IntegrityError
    mamock = Mock(ma)
    publish_photos(mamock, request, qs)
    mamock.message_user.assert_called_once()

def test_mass_unpublished():
    model = Mock()
    ma = PhotoAdmin(model=model, admin_site=AdminSite())
    request = RequestFactory().get('/')
    qs = Mock(spec=Photo.objects)
    unpublish_photos(ma, request, qs)
    qs.update.assert_called_once_with(is_published=False)
    call_args = qs.update.call_args
    Photo.objects.filter(*call_args.args, **call_args.kwargs)

def test_photosphere_form():
    ma = PhotoSphereAdmin(model=PhotoSphere, admin_site=AdminSite())
    request = RequestFactory().get('/')
    assert ['title', 'description', 'image'] == list(ma.get_form(request, obj=None).base_fields)
    assert ['title', 'description', 'image', 'heading', 'location'] == list(ma.get_form(request, obj=PhotoSphere()).base_fields)

def test_photoadmin_thumb():
    ma = PhotoAdmin(model=Photo, admin_site=AdminSite())
    photo = Photo()
    photo.thumbnail = Mock(spec=['url', 'width', 'height'])
    photo.thumbnail.url = 'url'
    photo.thumbnail.width = 123
    photo.thumbnail.height = 456
    tag = ma.thumb_image(photo)
    assert 'src="url"' in tag
    assert 'width="123"' in tag
    assert 'height="456"' in tag

def test_photoadmin_h700():
    ma = PhotoAdmin(model=Photo, admin_site=AdminSite())
    photo = Photo()
    photo.h700 = Mock(spec=['url', 'width', 'height'])
    photo.h700.url = 'url'
    photo.h700.width = 123
    photo.h700.height = 456
    tag = ma.h700_image(photo)
    assert 'src="url"' in tag
    assert 'width="123"' in tag
    assert 'height="456"' in tag
    photo.h700 = None
    assert '-' == ma.h700_image(photo)

def test_photoadmin_save_form():
    #model = Mock()
    ma = PhotoAdmin(model=Photo, admin_site=AdminSite())
    img = BytesIO(small_gif)
    img.name = "small.gif"
    request = RequestFactory().post('/', {"attachment": img})
    form = Mock()
    change = Mock()
    ma.save_form(request, form, change)
    assert form.save().thumbnail == None
    assert form.save().h700 == None
    assert [] == change.mock_calls

def test_usertaginline():
    ma = UserTagInline(Photo, admin_site=AdminSite())
    mock = Mock(spec=PhotoTag.creator.through, autospec=True)
    mock.phototag.photo.id = 1
    mock.phototag.photo.thumbnail.url = 'url'
    mock.phototag.photo.thumbnail.width = '123'
    mock.phototag.photo.thumbnail.height = '456'
    tag = ma.thumb_image(mock)
    assert 'src="url"' in tag
    assert 'width="123"' in tag
    assert 'height="456"' in tag

def test_usertaginline_tag():
    ma = UserTagInline(Photo, admin_site=AdminSite())
    assert "tag" == ma.tag(PhotoTag.creator.through(phototag=PhotoTag(tag=Tag(tag="tag"))))

def test_usertaginline_accepted():
    ma = UserTagInline(Photo, admin_site=AdminSite())
    assert "yes" == ma.accepted(PhotoTag.creator.through(phototag=PhotoTag(accepted=True)))
    assert "no" == ma.accepted(PhotoTag.creator.through(phototag=PhotoTag(accepted=False)))

def test_userarchivepermissionsinline_accepted():
    # This test has no assertions, but would not execute successfully if the query being executed referenced model
    # fields which do not exist.
    ma = UserArchivePermissionsInline(User, admin_site=AdminSite())
    request = RequestFactory().post('/')
    formfield = ma.formfield_for_manytomany(Archive.users.through.permission.field, request)

def test_taginline_submitter():
    ma = TagInline(Photo, admin_site=AdminSite())
    mock = Mock(spec=PhotoTag())
    mock.creator.all.return_value = [Mock(spec=['id', 'username'])]
    mock.creator.all()[0].id = 123
    mock.creator.all()[0].username = 'user'
    tag = ma.submitter(mock)
    assert '/123/' in tag
    assert '>user</a>' in tag


def test_termfilter():
    model = Mock()
    ma = PhotoAdmin(model=model, admin_site=AdminSite())
    request = RequestFactory().get('/')
    filter = TermFilter(request=request, params={}, model=model, model_admin=ma)
    choices = filter.lookup_choices
    for (lookup, title) in choices:
        filter = TermFilter(request=request, params={TermFilter.parameter_name: lookup}, model=model, model_admin=ma)
        qs = Mock()
        result = filter.queryset(request, qs)
        if lookup == "4+":
            qs.annotate().filter.assert_called_once_with(terms__count__gte=4)
        else:
            qs.annotate().filter.assert_called_once_with(terms__count=int(lookup))
