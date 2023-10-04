from django.test import Client, RequestFactory, SimpleTestCase
from django.contrib.auth.models import AnonymousUser, User, Group
from django.db import transaction
from hypothesis import given, strategies as st, note, settings as hsettings
from hypothesis.stateful import rule, invariant, Bundle, initialize, consumes, precondition
from hypothesis.extra.django import TestCase, from_model
from io import BytesIO
from unittest.mock import Mock, sentinel, MagicMock
from django.contrib.admin.sites import AdminSite
from archive.admin import *
from archive.models.donor import Donor
from archive.models.archive import Archive
from archive.models.photo import Photo
from archive.models.photosphere import PhotoSphere
from .util import donors, small_gif, archives, TransactionalRuleBasedStateMachine
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.contenttypes.models import ContentType
import pytest

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
    qs.annotate_photographedcount.return_value = qs
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
    assert ['title', 'description', 'image', 'heading', 'location', "mainstreetset", "links"] == list(ma.get_form(request, obj=PhotoSphere()).base_fields)

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

class UserPrivilegeEscalationTest(TransactionalRuleBasedStateMachine):
    permissions = Bundle("permissions")
    groups = Bundle("groups")
    some_permissions = Bundle("some_permissions")
    some_groups = Bundle("some_groups")
    a_group = Bundle("a_group")
    a_user = Bundle("a_user")
    #an_editor = Bundle("an_editor")
    uid = 0

    def __init__(self):
        super().__init__()
        self.editor = None

    @initialize(target=permissions)
    def initialize(self):
        return list(Permission.objects.all())

    @rule()
    def make_a_superuser(self):
        self.uid = self.uid + 1
        self.editor = User.objects.create_superuser(str(self.uid))
        self.editor.get_all_permissions()
        #return u

    @rule(target=a_user)
    def make_a_user(self):
        self.uid = self.uid + 1
        return User.objects.create_user(str(self.uid))

    @precondition(lambda self: self.editor)
    @invariant()
    def no_escalation(self):
        assert self.editor.get_all_permissions() >= User.objects.get(id=self.editor.id).get_all_permissions()


    @rule(data=st.data(), _=a_user)
    def pick_an_editor(self, data, _):
        self.editor = data.draw(st.sampled_from(list(User.objects.all())))
        self.editor.get_all_permissions()

    @rule(target=a_user, _=a_user, data=st.data())
    def pick_a_user(self, data, _):
        return data.draw(st.sampled_from(list(User.objects.all())))

    @rule(target=a_group, group=from_model(Group))
    def make_a_group(self, group):
        return group

    @rule(target=a_group, _=a_group, data=st.data())
    def pick_a_group(self, _, data):
        return data.draw(st.sampled_from(list(Group.objects.all())))

    @rule(target=some_groups, _=a_group, data=st.data())
    def pick_some_groups(self, data, _):
        return data.draw(st.sets(st.sampled_from(list(Group.objects.all()))))

    @rule(target=some_permissions, perms=permissions, data=st.data())
    def pick_some_permissions(self, perms, data):
        return data.draw(st.sets(st.sampled_from(perms)))

    @rule(target=groups, group=from_model(Group))
    def add_group(self, group):
        return list(Group.objects.all())

    @precondition(lambda self: self.editor)
    @rule(user=a_user, groups=some_groups)
    def change_user_groups(self, user, groups):
        with block_escalation(editor=self.editor, user=user):
            user.groups.set(groups)

    @precondition(lambda self: self.editor)
    @rule(user=a_user, perms=some_permissions)
    def change_user_perms(self, user, perms):
        with block_escalation(editor=self.editor, user=user):
            user.user_permissions.set(perms)

    @precondition(lambda self: self.editor)
    @rule(group=a_group, perms=some_permissions)
    def change_group_perms(self, perms, group):
        with block_group_escalation(editor=self.editor, group=group):
            group.permissions.set(perms)

UserPrivilegeEscalationTest.TestCase.settings = hsettings(max_examples = 10, stateful_step_count = 10, deadline=None)

class TestUserPrivileges(TestCase, UserPrivilegeEscalationTest.TestCase):
    pass

class UserAdminTests(TestCase):
    @given(st.data())
    def test_changeable_permissions(self, data):
        permissions = data.draw(st.sets(st.sampled_from(list(Permission.objects.all()[:10]))))
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        user1.user_permissions.add(*permissions)
        group = Group.objects.create(name='groupname')
        group.permissions.add(*permissions)
        user2.groups.add(group)
        self.assertQuerysetEqual(PermissionAnalyst(user1).get_changeable_permissions(), PermissionAnalyst(user2).get_changeable_permissions())

    @given(st.data())
    def test_changeable_groups(self, data):
        permissions = list(Permission.objects.all()[:10])
        perms1 = data.draw(st.sets(st.sampled_from(permissions)))
        perms2 = data.draw(st.sets(st.sampled_from(permissions)))
        group1 = Group.objects.create(name='group1')
        group1.permissions.add(*perms1)
        group2 = Group.objects.create(name='group2')
        group2.permissions.add(*perms2)
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        user1.groups.add(group1)
        user2.user_permissions.add(*perms1)
        ma = KronofotoUserAdmin(model=User, admin_site=AdminSite())
        self.assertQuerysetEqual(PermissionAnalyst(user1).get_changeable_groups(), PermissionAnalyst(user2).get_changeable_groups(), ordered=False)

    @hsettings(deadline=None)
    @given(
        st.booleans(),
        st.booleans(),
        st.lists(st.builds(Group), unique_by=lambda g: g.name),
        st.lists(st.builds(Archive), unique_by=lambda a: a.slug, min_size=1),
        st.data(),
    )
    def test_users_cannot_change_privileges_they_do_not_have(self, su1, su2, groups, archives, data):
        u1 = (User.objects.create_superuser if su1 else User.objects.create_user)("test1")
        u2 = (User.objects.create_superuser if su2 else User.objects.create_user)("test2")
        Group.objects.bulk_create(groups)
        Archive.objects.bulk_create(archives)
        archives = list(Archive.objects.all())
        perms = list(Permission.objects.filter(content_type__app_label='archive')[:10])
        groups = list(Group.objects.all())
        note('drawing u1 perms')
        u1.user_permissions.set(data.draw(st.sets(st.sampled_from(perms))))
        note('drawing u2 perms')
        u2.user_permissions.set(data.draw(st.sets(st.sampled_from(perms))))
        for group in groups:
            note(f'drawing group {group.id} perms')
            group.permissions.set(data.draw(st.sets(st.sampled_from(perms))))

        if groups:
            note(f'drawing groups for u1')
            u1.groups.set(data.draw(st.sets(st.sampled_from(groups))))
            note(f'drawing groups for u2')
            u2.groups.set(data.draw(st.sets(st.sampled_from(groups))))

        if archives:
            note('drawing archives for u1 perms')
            for archive in data.draw(st.sets(st.sampled_from(archives))):
                obj, created = Archive.users.through.objects.get_or_create(archive=archive, user=u1)
                note('drawing archive perms for u1')
                userperms = data.draw(st.sets(st.sampled_from(perms)))
                obj.permission.set(userperms)
            note('drawing archives for u2 perms')
            for archive in data.draw(st.sets(st.sampled_from(archives))):
                note('drawing archive perms for u2')
                obj, created = Archive.users.through.objects.get_or_create(archive=archive, user=u2)
                userperms = data.draw(st.sets(st.sampled_from(perms)))
                obj.permission.set(userperms)
        u1 = User.objects.get(pk=u1.id)
        u1_perm_set = u1.get_all_permissions()
        u2_perm_set_pre = u2.get_all_permissions()

        with block_escalation(editor=u1, user=u2):
            note('drawing new perms for u2')
            assign_perms = data.draw(st.sets(st.sampled_from(perms)))
            u2.user_permissions.set(assign_perms)
            assign_groups = []
            if groups:
                note('drawing new groups for u2')
                assign_groups = data.draw(st.sets(st.sampled_from(groups)))
                u2.groups.set(assign_groups)
            u2.archiveuserpermission_set.all().delete()
            assign_archive_perms = {}
            if archives:
                note('drawing new archives for u2 perms')
                for archive in data.draw(st.sets(st.sampled_from(archives))):
                    obj, created = Archive.users.through.objects.get_or_create(archive=archive, user=u2)
                    note('drawing new archive perms for u2')
                    userperms = data.draw(st.sets(st.sampled_from(perms)))
                    assign_archive_perms[archive.slug] = userperms
                    if created:
                        obj.permission.add(*userperms)
                    else:
                        obj.permission.set(userperms)
            requested_set = User.objects.get(pk=u2.id).get_all_permissions()
        u2 = User.objects.get(pk=u2.id)
        u2_perm_set_post = u2.get_all_permissions()
        assert u2_perm_set_pre.symmetric_difference(u2_perm_set_post) <= u1_perm_set
        # every permission which is assigned should be there either because it was there before or because it was requested.
        assert u2_perm_set_post <= (u2_perm_set_pre | requested_set)



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
