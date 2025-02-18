from django.test import Client, RequestFactory, SimpleTestCase
from django.contrib.auth.models import AnonymousUser, User, Group
from django.db import transaction
from hypothesis import given, strategies as st, note, settings as hsettings
from hypothesis.stateful import rule, invariant, Bundle, initialize, consumes, precondition
from hypothesis.extra.django import TestCase, from_model
from io import BytesIO
from unittest.mock import Mock, sentinel, MagicMock
from django.contrib.admin.sites import AdminSite
from fortepan_us.kronofoto.admin import *
from fortepan_us.kronofoto.models import Donor
from fortepan_us.kronofoto.models import Archive
from fortepan_us.kronofoto.models import Photo
from fortepan_us.kronofoto.models import PhotoSphere
from django.core.files.uploadedfile import SimpleUploadedFile
from .util import donors, small_gif, archives, TransactionalRuleBasedStateMachine
from django.contrib.contenttypes.models import ContentType
import pytest

#@given(st.sets(st.integers()), st.sets(st.integers()), st.sets(st.integers()), st.sets(st.integers()))
#def test_set_theory(a, b, c, d):
#    assert  (a - (b | c)) | ((b | c) & d) == (a - (b & c)) | ((b | c) & d)


#@given(st.sets(st.integers()), st.sets(st.integers()), st.sets(st.integers()))
#def test_set_theory(a, b, c):
#    assert  (a - b) | (b & c) == (a - b) | (b | c)


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
    for filter in (HasLocationFilter,):
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
    assert ['title', 'description', 'is_published', 'image', 'heading', 'location', "mainstreetset", "links"] == list(ma.get_form(request, obj=PhotoSphere()).base_fields)

class Photo2:
    def __init__(self):
        self.thumbnail = Mock(spec=['url', 'width', 'height'])
        self.thumbnail.url = 'url'
        self.thumbnail.width = 123
        self.thumbnail.height = 456
        self.h700 = Mock(spec=['url', 'width', 'height'])
        self.h700.url = 'url'
        self.h700.width = 123
        self.h700.height = 456
def test_photoadmin_thumb():
    ma = PhotoAdmin(model=Photo, admin_site=AdminSite())
    photo = Photo2()
    tag = ma.thumb_image(photo)
    assert 'src="url"' in tag
    assert 'width="123"' in tag
    assert 'height="456"' in tag

def test_photoadmin_h700():
    ma = PhotoAdmin(model=Photo, admin_site=AdminSite())
    photo = Photo2()
    tag = ma.h700_image(photo)
    assert 'src="url"' in tag
    assert 'width="123"' in tag
    assert 'height="456"' in tag
    photo.h700 = None
    assert '-' == ma.h700_image(photo)

def test_photoadmin_save_form():
    ma = PhotoAdmin(model=Photo, admin_site=AdminSite())
    img = BytesIO(small_gif)
    img.name = "small.gif"
    request = RequestFactory().post('/', {"attachment": img})
    form = Mock()
    change = Mock()
    ma.save_form(request, form, change)
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

class SubmissionAdminTest(TestCase):
    def test_acceptance_logging(self):
        from django.contrib.admin.models import LogEntry, DELETION, ADDITION
        from fortepan_us.kronofoto.models import Submission
        archive = Archive.objects.create(slug="any-slug")
        category = Category.objects.create(slug="any-slug")
        donor = Donor.objects.create(archive=archive)
        image = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        user = User.objects.create_user("test", "test", "test")

        obj = Photo.objects.create(
            archive=archive,
            category=category,
            original=image,
            donor=donor,
            caption="asdf",
        )
        SubmissionLogger(
            user=user,
            object_name="the repr goes here",
            old_object_id=13,
            new_obj=obj,
            photo_opts=Photo._meta,
            factory=None,
        ).log()
        assert LogEntry.objects.filter(object_id=13, action_flag=DELETION).exists()
        entry = LogEntry.objects.get(object_id=13, action_flag=DELETION)
        assert "Submission accepted" in entry.change_message
        assert obj.accession_number in entry.change_message

        assert LogEntry.objects.filter(object_id=obj.id, action_flag=ADDITION).exists()
        entry = LogEntry.objects.get(object_id=obj.id, action_flag=ADDITION)
        assert "Created from Submission" in entry.change_message

    def test_submission_to_photo(self):
        from fortepan_us.kronofoto.models import Submission
        archive = Archive.objects.create(slug="any-slug")
        category = Category.objects.create(slug="any-slug")
        donor = Donor.objects.create(archive=archive)
        image = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')

        form = SubmissionAdmin.AcceptForm({'is_published': True, 'is_featured': False})
        self.assertTrue(form.is_valid())
        obj = Submission.objects.create(
            archive=archive,
            category=category,
            image=image,
            donor=donor,
            caption="asdf",
            photographer=donor,
        )
        terms = [Term.objects.create(term="term1"), Term.objects.create(term="term2")]
        obj.terms.set(terms)
        photo = SaveRecord(
            obj=obj,
            form=form,
        ).photo
        fields = {
            field.name
            for field in Submission._meta.fields
            if field.name not in ('id', 'uuid')
        } & {field.name for field in Photo._meta.fields}

        for field in fields:
            assert getattr(obj, field) == getattr(photo, field)
        for term in terms:
            assert term in photo.terms.all()

class UserPrivilegeEscalationTest(TransactionalRuleBasedStateMachine):
    permissions = Bundle("permissions")
    groups = Bundle("groups")
    archives = Bundle("archives")
    some_permissions = Bundle("some_permissions")
    some_groups = Bundle("some_groups")
    a_group = Bundle("a_group")
    a_user = Bundle("a_user")
    #an_editor = Bundle("an_editor")
    uid = 0

    def __init__(self):
        super().__init__()
        self.editor = None
        self.editor_perms = {}

    @initialize(target=permissions)
    def initialize_permissions(self):
        return list(Permission.objects.all())

    def make_an_archive(self, archive):
        return archive

    @initialize(target=archives, archive=from_model(Archive, id=st.none()))
    def make_an_archive_init(self, archive):
        return self.make_an_archive(archive)

    @rule(target=archives, archive=from_model(Archive, id=st.none()))
    def make_an_archive_rule(self, archive):
        archive = self.make_an_archive(archive)
        if self.editor:
            self.editor_perms = User.objects.get(id=self.editor.id).get_all_permissions()
        return archive


    @initialize(target=a_user, archive=archives, data=st.data())
    def make_a_user(self, archive, data):
        self.uid = self.uid + 1
        self.editor = User.objects.create_user(str(self.uid))
        perms = list(Permission.objects.all())
        self.editor.user_permissions.set(data.draw(st.sets(st.sampled_from(perms))))
        obj, created = Archive.users.through.objects.get_or_create(archive=archive, user=self.editor)
        obj.permission.set(data.draw(st.sets(st.sampled_from(perms))))
        self.editor_perms = self.editor.get_all_permissions()
        return self.editor

    @initialize(target=a_group, archive=archives, group=from_model(Group, id=st.none()), data=st.data())
    def make_a_group(self, archive, group, data):
        perms = list(Permission.objects.all())
        group.permissions.set(data.draw(st.sets(st.sampled_from(perms))))
        obj, created = Archive.groups.through.objects.get_or_create(archive=archive, group=group)
        obj.permission.set(data.draw(st.sets(st.sampled_from(perms))))
        return group

    @precondition(lambda self: self.editor and not self.editor.is_superuser)
    @invariant()
    def no_escalation(self):
        assert self.editor_perms >= User.objects.get(id=self.editor.id).get_all_permissions()

    @rule(target=some_groups, _=a_group, data=st.data())
    def pick_some_groups(self, data, _):
        return data.draw(st.sets(st.sampled_from(list(Group.objects.all()))))

    @rule(groups=some_groups)
    def assign_groups(self, groups):
        self.editor.groups.set(groups)
        self.editor_perms = User.objects.get(id=self.editor.id).get_all_permissions()

    @rule(target=some_permissions, perms=permissions, data=st.data())
    def pick_some_permissions(self, perms, data):
        return data.draw(st.sets(st.sampled_from(perms)))

    @precondition(lambda self: self.editor)
    @rule(user=a_user, archive=archives, perms=some_permissions)
    def set_user_archive_permissions(self, user, archive, perms):
        obj, created = Archive.users.through.objects.get_or_create(archive=archive, user=user)
        with block_escalation(editor=self.editor, user=user):
            obj.permission.set(perms)

    @rule(archive=archives, aup=a_user.flatmap(lambda u: st.sampled_from(list(u.archiveuserpermission_set.all())) if u.archiveuserpermission_set.exists() else st.nothing()))
    def change_aup_target(self, archive, aup):
        if not archive.archiveuserpermission_set.filter(user=aup.user.id).exists():
            with block_escalation(editor=self.editor, user=self.editor):
                aup.archive = archive
                aup.save()

    @precondition(lambda self: self.editor)
    @rule(group=a_group, archive=archives, perms=some_permissions)
    def set_group_archive_permissions(self, group, archive, perms):
        obj, created = Archive.groups.through.objects.get_or_create(archive=archive, group=group)
        with block_group_escalation(editor=self.editor, group=group):
            obj.permission.set(perms)

    @rule(target=groups, group=from_model(Group, id=st.none()))
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

UserPrivilegeEscalationTest.TestCase.settings = hsettings(max_examples = 5, stateful_step_count = 5, deadline=None)

# This was very useful for finding things users could do to escalate their privileges.
# It's slow and has been replaced by a bunch of fast tests.
# It would be nice to restore this if database access is ever not required for the checks.
#class TestUserPrivileges(TestCase, UserPrivilegeEscalationTest.TestCase):
#    pass

class UserAdminTests(TestCase):
    def test_can_remove_archive_permission_from_group_with_universal_permission(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        user1.user_permissions.set([permission])
        group = Group.objects.create(name="group")
        archive_perms = Archive.groups.through.objects.create(archive=archive, group=group)
        archive_perms.permission.set([permission])
        with block_group_escalation(editor=user1, group=group):
            archive_perms.permission.set([])
        assert not archive_perms.permission.filter(pk=permission.pk).exists()

    def test_cannot_add_permission_to_group_without_permission(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        group = Group.objects.create(name="group")
        with block_group_escalation(editor=user1, group=group):
            group.permissions.set([permission])
        assert not group.permissions.filter(pk=permission.pk).exists()

    def test_cannot_remove_permission_from_group_without_permission(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        group = Group.objects.create(name="group")
        group.permissions.set([permission])
        with block_group_escalation(editor=user1, group=group):
            group.permissions.set([])
        assert group.permissions.filter(pk=permission.pk).exists()

    def test_cannot_delete_archive_permission_from_group_without_permission(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        group = Group.objects.create(name="group")
        archive_perms = Archive.groups.through.objects.create(archive=archive, group=group)
        archive_perms.permission.set([permission])
        with block_group_escalation(editor=user1, group=group):
            archive_perms.delete()
        assert Archive.groups.through.objects.filter(archive=archive, group=group).exists()


    def test_cannot_add_second_archive_permission_without_permission(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        archive2 = Archive.objects.create(slug="slug2")
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        archive_perms = Archive.users.through.objects.create(archive=archive, user=user2)
        archive_perms.permission.set([permission])
        with block_escalation(editor=user1, user=user2):
            archive_perms2 = Archive.users.through.objects.create(archive=archive2, user=user2)
            archive_perms2.permission.set([permission])
        assert not archive_perms2.permission.filter(pk=permission.pk).exists()

    def test_removing_all_archive_permissions_removes_m2m_db_object(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        user1.user_permissions.add(permission)
        archive_perms = Archive.users.through.objects.create(archive=archive, user=user2)
        archive_perms.permission.set([permission])
        with block_escalation(editor=user1, user=user2):
            archive_perms.permission.clear()
        assert not Archive.users.through.objects.filter(archive=archive, user=user2).exists()

    def test_can_add_archive_permissions_to_group_if_have_it_through_a_group(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        group = Group.objects.create(name="group")
        group2 = Group.objects.create(name="group2")
        archive_perms = Archive.groups.through.objects.create(archive=archive, group=group)
        archive_perms.permission.set([permission])
        user1.groups.add(group)
        with block_group_escalation(editor=user1, group=group2):
            archive_perms2 = Archive.groups.through.objects.create(archive=archive, group=group2)
            archive_perms2.permission.set([permission])
        assert archive_perms2.permission.filter(pk=permission.pk).exists()

    def test_can_add_archive_permissions_if_have_universal_permissions(self):
        permissions = Permission.objects.all()[:3]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        archive_perms = Archive.users.through.objects.create(archive=archive, user=user2)
        archive_perms.permission.set(permissions)
        user1.user_permissions.set(permissions)
        with block_escalation(editor=user1, user=user2):
            archive_perms.permission.set(permissions)
        assert archive_perms.permission.filter(pk=permissions[0].pk).exists()

    def test_cannot_add_group_to_user_without_permission(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        group1 = Group.objects.create(name="group1")
        group1.permissions.set([permission])
        with block_escalation(editor=user1, user=user2):
            user2.groups.add(group1)
        assert not user2.groups.filter(pk=group1.pk).exists()

    def test_cannot_add_permission_to_user_without_permission(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        with block_escalation(editor=user1, user=user2):
            user2.user_permissions.set([permission])
        assert not user2.user_permissions.filter(pk=permission.pk).exists()

    def test_cannot_remove_permission_from_user_without_permission(self):
        permission = Permission.objects.all()[0]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        user2.user_permissions.set([permission])
        with block_escalation(editor=user1, user=user2):
            user2.user_permissions.set([])
        assert user2.user_permissions.filter(pk=permission.pk).exists()

    def test_can_remove_archive_permissions_if_have_universal_permissions(self):
        permissions = Permission.objects.all()[:3]
        archive = Archive.objects.create(slug="slug")
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        archive_perms = Archive.users.through.objects.create(archive=archive, user=user2)
        archive_perms.permission.set(permissions)
        user1.user_permissions.set(permissions)
        with block_escalation(editor=user1, user=user2):
            archive_perms.permission.clear()
        assert not archive_perms.permission.exists()

    def test_cannot_remove_group_from_other(self):
        permissions = Permission.objects.all()
        group1 = Group.objects.create(name="group1")
        group1.permissions.add(*permissions[:5])
        group2 = Group.objects.create(name="group2")
        group2.permissions.add(*permissions[5:10])
        user1 = User.objects.create_user("test1")
        user2 = User.objects.create_user("test2")
        user1.groups.add(group1)
        user2.groups.add(group2)
        user2.save()
        with block_escalation(editor=user1, user=user2):
            user2.groups.clear()
        assert group2 in user2.groups.all()


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

