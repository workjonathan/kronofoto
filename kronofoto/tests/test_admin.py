from django.test import Client, RequestFactory, SimpleTestCase
from django.contrib.auth.models import AnonymousUser, User, Group
from hypothesis import given, strategies as st, note
from hypothesis.extra.django import TestCase, from_model
from io import BytesIO
from unittest.mock import Mock, sentinel, MagicMock
from django.contrib.admin.sites import AdminSite
from archive.admin import *
from archive.models.donor import Donor
from archive.models.archive import Archive
from archive.models.photo import Photo
from archive.models.photosphere import PhotoSphere
from .util import donors, small_gif, archives
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.contenttypes.models import ContentType

def test_permissionmixin_hasadd():
    class Base:
        opts = Mock()
        opts.app_label = 'testlabel'
        opts.model_name = 'testmodel'
        permission = True
        def has_add_permission(self, request):
            return self.permission
    class Cls(ArchivePermissionMixin, Base):
        pass
    instance = Cls()
    assert instance.has_add_permission(Mock())
    instance.permission = False
    request = Mock()
    request.user.has_perm.return_value = sentinel.perm
    assert instance.has_add_permission(request) == sentinel.perm
    request.user.has_perm.assert_called_once_with('testlabel.any.add_testmodel')



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

def test_donor_formfield():
    #model = Mock()
    #qs = Mock(spec=Donor.objects)
    #qs.annotate_scannedcount.return_value = qs
    #qs.annotate_donatedcount.return_value = qs
    #model._default_manager.get_queryset.return_value = qs
    admin = DonorAdmin(model=Donor, admin_site=AdminSite())
    request = RequestFactory().get('/')
    request.user = MagicMock()
    request.user.id = 1
    request.user.has_perm.return_value = False
    request.user.resolve_expression.return_value = 2
    db_field = Mock()
    db_field.name = 'archive'
    db_field.id = 1
    qs = admin.formfield_for_foreignkey(db_field, request)
    assert qs


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


class UserAdminTests(TestCase):
    @given(st.lists(from_model(Permission, content_type=from_model(ContentType))))
    def test_changeable_permissions(self, permissions):
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        user1.user_permissions.add(*permissions)
        group = Group.objects.create(name='groupname')
        group.permissions.add(*permissions)
        user2.groups.add(group)
        ma = KronofotoUserAdmin(model=User, admin_site=AdminSite())
        self.assertQuerysetEqual(ma._get_changeable_permissions(user1), ma._get_changeable_permissions(user2))

    @given(
        st.lists(from_model(Permission, content_type=from_model(ContentType))),
        st.lists(from_model(Permission, content_type=from_model(ContentType))),
    )
    def test_changeable_groups(self, perms1, perms2):
        group1 = Group.objects.create(name='group1')
        group1.permissions.add(*perms1)
        group2 = Group.objects.create(name='group2')
        group2.permissions.add(*perms2)
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        user1.groups.add(group1)
        user2.user_permissions.add(*perms1)
        ma = KronofotoUserAdmin(model=User, admin_site=AdminSite())
        self.assertQuerysetEqual(ma._get_changeable_groups(user1), ma._get_changeable_groups(user2), ordered=False)

    @given(
        st.booleans(),
        st.booleans(),
        st.lists(st.builds(Group), unique_by=lambda g: g.name),
        st.lists(st.builds(Archive), unique_by=lambda a: a.slug),
        st.data(),
    )
    def test_users_cannot_change_privileges_they_do_not_have(self, su1, su2, groups, archives, data):
        u1 = (User.objects.create_superuser if su1 else User.objects.create_user)("test1")
        u2 = (User.objects.create_superuser if su2 else User.objects.create_user)("test2")
        Group.objects.bulk_create(groups)
        Archive.objects.bulk_create(archives)
        archives = list(Archive.objects.all())
        perms = list(Permission.objects.all())
        groups = list(Group.objects.all())
        u1.user_permissions.set(data.draw(st.sets(st.sampled_from(perms))))
        u2.user_permissions.set(data.draw(st.sets(st.sampled_from(perms))))
        for group in groups:
            group.permissions.set(data.draw(st.sets(st.sampled_from(perms))))

        if groups:
            u1.groups.set(data.draw(st.sets(st.sampled_from(groups))))
            u2.groups.set(data.draw(st.sets(st.sampled_from(groups))))

        if archives:
            for archive in data.draw(st.sets(st.sampled_from(archives))):
                obj, created = Archive.users.through.objects.get_or_create(archive=archive, user=u1)
                userperms = data.draw(st.sets(st.sampled_from(perms)))
                if created:
                    obj.permission.add(*userperms)
                else:
                    obj.permission.set(userperms)
            for archive in data.draw(st.sets(st.sampled_from(archives))):
                obj, created = Archive.users.through.objects.get_or_create(archive=archive, user=u2)
                userperms = data.draw(st.sets(st.sampled_from(perms)))
                if created:
                    obj.permission.add(*userperms)
                else:
                    obj.permission.set(userperms)
        u1 = User.objects.get(pk=u1.id)
        u1_perm_set = u1.get_all_permissions()
        u2_perm_set_pre = u2.get_all_permissions()

        with block_escalation(editor=u1, user=u2):
            u2.user_permissions.set(data.draw(st.sets(st.sampled_from(perms))))
            if groups:
                u2.groups.set(data.draw(st.sets(st.sampled_from(groups))))
            u2.archiveuserpermission_set.all().delete()
            if archives:
                for archive in data.draw(st.sets(st.sampled_from(archives))):
                    obj, created = Archive.users.through.objects.get_or_create(archive=archive, user=u2)
                    userperms = data.draw(st.sets(st.sampled_from(perms)))
                    if created:
                        obj.permission.add(*userperms)
                    else:
                        obj.permission.set(userperms)
        u2 = User.objects.get(pk=u2.id)
        u2_perm_set_post = u2.get_all_permissions()
        assert u2_perm_set_pre.symmetric_difference(u2_perm_set_post) <= u1_perm_set




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
