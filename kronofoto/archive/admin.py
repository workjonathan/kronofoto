from django.contrib.gis import admin
from django.contrib import admin as base_admin
from django.contrib.auth.models import User, Permission, Group
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_permission_codename
from django.utils.safestring import mark_safe
from django.forms import widgets
from .models import Photo, PhotoSphere, PhotoSpherePair, Tag, Term, PhotoTag, Donor, NewCutoff, CSVRecord
from .models.archive import Archive, ArchiveUserPermission
from .models.csvrecord import ConnecticutRecord
from .forms import PhotoSphereAddForm, PhotoSphereChangeForm, PhotoSpherePairInlineForm
from django.db.models import Count, Q, Exists, OuterRef, F
from django.db import IntegrityError
from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.contrib import messages
from django import forms
from django.forms import ModelForm, Textarea
from functools import reduce
import operator
from collections import defaultdict

admin.site.site_header = 'Fortepan Administration'
admin.site.site_title = 'Fortepan Administration'
admin.site.index_title = 'Fortepan Administration Index'

class HasPhotoFilter(base_admin.SimpleListFilter):
    title = "has photo"
    parameter_name = "photo"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.exclude(photo__isnull=True)
        elif self.value() == 'No':
            return queryset.filter(photo__isnull=True)

class HasYearFilter(base_admin.SimpleListFilter):
    title = "has year"
    parameter_name = "cleaned_year__isnull"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.filter(cleaned_year__isnull=False)
        elif self.value() == 'No':
            return queryset.filter(cleaned_year__isnull=True)

class IsPublishableFilter(base_admin.SimpleListFilter):
    title = "is publishable"
    parameter_name = "publishable"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.filter(publishable=True)
        elif self.value() == 'No':
            return queryset.filter(publishable=False)

class LocationEnteredFilter(base_admin.SimpleListFilter):
    title = "location entered"
    parameter_name = "location"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.exclude(cleaned_city='', cleaned_county='', cleaned_state='', cleaned_country='')
        elif self.value() == 'No':
            return queryset.filter(cleaned_city='', cleaned_county='', cleaned_state='', cleaned_country='')

@admin.register(ConnecticutRecord)
class ConnecticutRecordAdmin(admin.ModelAdmin):
    raw_id_fields = ['photo']
    list_editable = ['publishable']
    search_fields = (
        'title',
        'year',
        'cleaned_year',
        'contributor',
        'description',
        'location',
        'cleaned_city',
        'cleaned_county',
        'cleaned_state',
        'cleaned_country',
    )
    list_display = (
        'file_id1',
        'file_id2',
        'thumbnail',
        'title',
        'year',
        'cleaned_year',
        'publishable',
        'contributor',
        'description',
        'location',
        'cleaned_city',
        'cleaned_county',
        'cleaned_state',
        'cleaned_country',
    )
    list_filter = (HasPhotoFilter, HasYearFilter, IsPublishableFilter, LocationEnteredFilter)

    def thumbnail(self, obj):
        src = 'https://ctdigitalarchive.org/islandora/object/{}/datastream/JPG'.format(str(obj))
        return mark_safe('<a href="{src}" target="_blank"><img src="{src}" width="200" /></a>'.format(src=src))

    def has_add_permission(self, request):
        return False

    #def has_change_permission(self, request, obj=None):
    #    return False


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    pass

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ['tag']

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj:
            fields += ('tag',)
        return fields



@admin.register(NewCutoff)
class NewCutoffAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if NewCutoff.objects.all().exists():
            return False
        else:
            return super().has_add_permission(request)


class ArchivePermissionMixin:
    def has_add_permission(self, request, *args):
        codename_add = get_permission_codename('add', self.opts)
        return (super().has_add_permission(request, *args)
            or request.user.has_perm("{}.any.{}".format(self.opts.app_label, codename_add)))

    def has_change_permission(self, request, obj=None):
        codename_change = get_permission_codename('change', self.opts)
        return (super().has_change_permission(request, obj)
            or (request.user.has_perm("{}.archive.{}.{}".format(self.opts.app_label, obj.archive.slug, codename_change))
                if obj
                else request.user.has_perm("{}.any.{}".format(self.opts.app_label, codename_change)))
        )

    def has_view_permission(self, request, obj=None):
        if super().has_view_permission(request, obj):
            return True
        opts = self.opts
        codename_view = get_permission_codename('view', opts)
        codename_change = get_permission_codename('change', opts)
        if obj:
            return (
                request.user.has_perm("{}.archive.{}.{}".format(opts.app_label, obj.archive.slug, codename_view)) or
                request.user.has_perm("{}.archive.{}.{}".format(opts.app_label, obj.archive.slug, codename_change))
            )
        else:
            return (
                request.user.has_perm("{}.any.{}".format(opts.app_label, codename_view)) or
                request.user.has_perm("{}.any.{}".format(opts.app_label, codename_change))
            )

    def has_delete_permission(self, request, obj=None):
        codename_delete = get_permission_codename('delete', self.opts)
        return (super().has_delete_permission(request, obj)
            or (request.user.has_perm("{}.archive.{}.{}".format(self.opts.app_label, obj.archive.slug, codename_delete))
                if obj
                else request.user.has_perm("{}.any.{}".format(self.opts.app_label, codename_delete))
            ))

class FilteringArchivePermissionMixin(ArchivePermissionMixin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not super().has_view_permission(request) and not super().has_change_permission(request):
            opts = self.opts
            codename_view = get_permission_codename('view', opts)
            codename_change = get_permission_codename('change', opts)
            qs = qs.filter(Q(
                archive__archiveuserpermission__user=request.user,
                archive__archiveuserpermission__permission__content_type__model=opts.model_name,
            ) & Q(archive__archiveuserpermission__permission__codename=codename_view) | Q(archive__archiveuserpermission__permission__codename=codename_change))
        return qs

@admin.register(Donor)
class DonorAdmin(FilteringArchivePermissionMixin, admin.ModelAdmin):
    search_fields = ['last_name', 'first_name']

    list_display = ('__str__', 'donated', 'scanned')

    def scanned(self, obj):
        return '{} photos'.format(obj.scanned_count)

    def donated(self, obj):
        return '{} photos'.format(obj.donated_count)

    scanned.admin_order_field = 'scanned_count'
    donated.admin_order_field = 'donated_count'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate_scannedcount().annotate_donatedcount()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not super().has_change_permission(request) and not super().has_add_permission(request):
            opts = self.opts
            codename_add = get_permission_codename('add', opts)
            codename_change = get_permission_codename('change', opts)
            kwargs['queryset'] = Archive.objects.filter(Q(
                archiveuserpermission__user=request.user,
                archiveuserpermission__permission__content_type__model=opts.model_name,
            ) & Q(archiveuserpermission__permission__codename=codename_add) | Q(archiveuserpermission__permission__codename=codename_change)).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    pass


class TagInline(ArchivePermissionMixin, admin.TabularInline):
    model = PhotoTag
    extra = 1
    fields = ['tag', 'accepted', 'submitter']
    raw_id_fields = ['tag']
    readonly_fields = ['submitter']

    def submitter(self, instance):
        creators = ', '.join(
            '<a href="{url}">{username}</a>'.format(
                url=reverse('admin:auth_user_change', args=[user.id]),
                username=user.username,
            )
            for user in instance.creator.all()
        )
        return mark_safe(creators)

    def has_add_permission(self, request, *args):
        return super().has_add_permission(request, *args)


class TermFilter(base_admin.SimpleListFilter):
    title = "term count"
    parameter_name = "terms__count"

    def lookups(self, request, model_admin):
        return (
            ("0", "0"),
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("4+", "4+"),
        )

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.annotate(Count("terms"))
        if self.value() in ("0", "1", "2", "3"):
            return queryset.filter(terms__count=int(self.value()))
        elif self.value() == "4+":
            return queryset.filter(terms__count__gte=4)


class StandardSimpleListFilter(base_admin.SimpleListFilter):
    def lookups(self, request, model_admin):
        return [(label, label) for (label, value) in self.filters]

    def queryset(self, request, queryset):
        for label, value in self.filters:
            if self.value() == label:
                return queryset.filter(**{self.field: value}).distinct()


class TagFilter(StandardSimpleListFilter):
    title = "tag status"
    parameter_name = "phototag__accepted"
    field = 'phototag__accepted'
    filters = (
        ("needs approval", False),
        ("approved", True),
    )


class YearIsSetFilter(StandardSimpleListFilter):
    title = "photo dated"
    parameter_name = "dated"
    field = 'year__isnull'

    filters = (
        ("Yes", False),
        ("No", True),
    )


class IsPublishedFilter(StandardSimpleListFilter):
    title = "photo is published"
    parameter_name = "is published"
    field = 'is_published'

    filters = (
        ("Yes", True),
        ("No", False),
    )

class HasLocationFilter(base_admin.SimpleListFilter):
    title = "photo has city or county"
    parameter_name = "is located"

    def lookups(self, request, model_admin):
        return (
            ("City", "City"),
            ("County", "County"),
            ("State only", "State only"),
            ("Country only", "Country only"),
            ("No location", "No location"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'County':
            return queryset.exclude(county="")
        elif self.value() == 'City':
            return queryset.exclude(city="")
        elif self.value() == 'State only':
            return queryset.filter(city="", county="").exclude(state="")
        elif self.value() == 'Country only':
            return queryset.filter(city="", county="", state="", country__isnull=False).exclude(country='')
        elif self.value() == 'No location':
            queryset = queryset.filter(city="", county="", state="")
            return queryset.filter(country="") | queryset.filter(country__isnull=True)

class HasGeoLocationFilter(base_admin.SimpleListFilter):
    title = "photo is geolocated"
    parameter_name = "is geolocated"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Point and Polygon"),
            ("Maybe", "Point or Polygon"),
            ("Point only", "Point only"),
            ("Polygon only", "Polygon only"),
            ("No", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.filter(location_point__isnull=False) & queryset.filter(location_bounds__isnull=False)
        elif self.value() == 'Maybe':
            return queryset.filter(location_point__isnull=False) | queryset.filter(location_bounds__isnull=False)
        elif self.value() == 'Point only':
            return queryset.filter(location_point__isnull=False) & queryset.filter(location_bounds__isnull=True)
        elif self.value() == 'Polygon only':
            return queryset.filter(location_point__isnull=True) & queryset.filter(location_bounds__isnull=False)
        elif self.value() == 'No':
            return queryset.filter(location_point__isnull=True) & queryset.filter(location_bounds__isnull=True)


@admin.action(permissions=["change"])
def publish_photos(modeladmin, request, queryset):
    try:
        queryset.update(is_published=True)
    except IntegrityError:
        modeladmin.message_user(request, 'All published photos must have a donor', messages.ERROR)

publish_photos.short_description = 'Publish photos'

@admin.action(permissions=["change"])
def unpublish_photos(modeladmin, request, queryset):
    queryset.update(is_published=False)
unpublish_photos.short_description = 'Unpublish photos'


class PhotoInline(admin.StackedInline):
    model = PhotoSpherePair
    extra = 0
    fields = ['photo', 'position']
    raw_id_fields = ['photo']
    form = PhotoSpherePairInlineForm


@admin.register(PhotoSphere)
class PhotoSphereAdmin(admin.OSMGeoAdmin):
    form = PhotoSphereChangeForm
    add_form = PhotoSphereAddForm
    list_display = ('title', 'description')
    search_fields = ('title', 'description')
    inlines = (PhotoInline,)

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            fieldsets = (
                (None, {
                    'fields': ('title', 'description', 'image'),
                    'description': "First fill out these options. After clicking Save and continue editing, you'll be able to edit more options.",
                }),
            )

        else:
            fieldsets = super().get_fieldsets(request, obj)
        return fieldsets


@admin.register(CSVRecord)
class CSVRecordAdmin(admin.ModelAdmin):
    search_fields = (
        'filename',
        'donorFirstName',
        'donorLastName',
        'city',
        'county',
        'state',
        'country',
        'comments',
    )
    list_display = (
        'filename',
        'donorFirstName',
        'donorLastName',
        'year',
        'circa',
        'scanner',
        'photographer',
        'address',
        'city',
        'county',
        'state',
        'country',
        'comments',
        'added_to_archive',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(photo__isnull=True)


@admin.register(Photo)
class PhotoAdmin(FilteringArchivePermissionMixin, admin.OSMGeoAdmin):
    readonly_fields = ["h700_image"]
    inlines = (TagInline,)
    list_filter = (TermFilter, TagFilter, YearIsSetFilter, IsPublishedFilter, HasGeoLocationFilter, HasLocationFilter)
    list_display = ('thumb_image', 'accession_number', 'donor', 'year', 'caption')
    actions = [publish_photos, unpublish_photos]
    search_fields = [
        'city',
        'state',
        'county',
        'donor__last_name',
        'donor__first_name',
        'caption',
        'year',
    ]

    def thumb_image(self, obj):
        return mark_safe('<img src="{}" width="{}" height="{}" />'.format(obj.thumbnail.url, obj.thumbnail.width, obj.thumbnail.height))

    def h700_image(self, obj):
        if obj.h700:
            return mark_safe('<img src="{}" width="{}" height="{}" />'.format(obj.h700.url, obj.h700.width, obj.h700.height))
        else:
            return "-"

    def save_form(self, request, form, change):
        photo = super().save_form(request, form, change)
        if len(request.FILES):
            photo.thumbnail = None
            photo.h700 = None
        return photo

class UserTagInline(admin.TabularInline):
    model = PhotoTag.creator.through
    extra = 0
    fields = ['thumb_image', 'tag', 'accepted']
    readonly_fields = ['thumb_image', 'tag', 'accepted']

    def thumb_image(self, instance):
        return mark_safe(
            '<a href="{edit_url}"><img src="{thumb}" width="{width}" height="{height}" /></a>'.format(
                edit_url=reverse('admin:archive_photo_change', args=(instance.phototag.photo.id,)),
                thumb=instance.phototag.photo.thumbnail.url,
                width=instance.phototag.photo.thumbnail.width,
                height=instance.phototag.photo.thumbnail.height,
            )
        )

    def tag(self, instance):
        return instance.phototag.tag.tag

    def accepted(self, instance):
        return 'yes' if instance.phototag.accepted else 'no'

class UserArchivePermissionsInline(base_admin.TabularInline):
    model = Archive.users.through
    extra = 1

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'permission':
            models = [
                'donor',
                'photo',
                #'photosphere',
                #'photospherepair',
                'phototag',
            ]
            clauses = (
                Q(content_type__model=model)
                for model in models
            )
            combined = reduce(operator.__or__, clauses)
            supported_permissions = Q(content_type__app_label='archive') & combined
            kwargs['queryset'] = Permission.objects.filter(supported_permissions)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class KronofotoUserAdmin(UserAdmin):
    inlines = (UserArchivePermissionsInline, UserTagInline,)

    def save_related(self, request, form, formsets, change):
        instance = form.instance
        changeable_archive_permissions = self._get_archive_permissions(request.user)
        old_archives = set(instance.archiveuserpermission_set.all())
        old_archive_permissions = self._get_archive_permissions(instance)

        old_perms = set(instance.user_permissions.all())
        old_groups = set(instance.groups.all())
        changeable_perms = set(self._get_changeable_permissions(request.user))
        changeable_groups = set(self._get_changeable_groups(request.user))
        super().save_related(request, form, formsets, change)
        new_perms = set(instance.user_permissions.all())
        new_groups = set(instance.groups.all())
        instance.user_permissions.set((old_perms - changeable_perms) | (changeable_perms & new_perms))
        instance.groups.set((old_groups - changeable_groups) | (changeable_groups & new_groups))

        new_archives = set(instance.archiveuserpermission_set.all())
        new_archive_permissions = self._get_archive_permissions(instance)
        changed_archive_perms = old_archives | new_archives
        for related in changed_archive_perms:
            assign = (old_archive_permissions[related.archive.id] - (changeable_archive_permissions[related.archive.id] | changeable_perms)) | ((changeable_archive_permissions[related.archive.id] | changeable_perms) & new_archive_permissions[related.archive.id])
            try:
                obj = instance.archiveuserpermission_set.get(archive__id=related.archive.id)
                obj.permission.set(assign)
            except Archive.users.through.DoesNotExist:
                if assign:
                    obj = Archive.users.through.objects.create(archive=related.archive, user=instance)
                    obj.permission.set(assign)



    def _get_archive_permissions(self, user):
        sets = defaultdict(set)
        objects = (Permission.objects
            .filter(archiveuserpermission__user__id=user.id)
            .annotate(archive_id=F('archiveuserpermission__archive__id'))
        )
        for obj in objects:
            sets[obj.archive_id].add(obj)
        return sets

    def _get_changeable_permissions(self, user):
        if user.is_superuser:
            return Permission.objects.all()
        q = Q(pk=user.id) & (Q(user_permissions=OuterRef('pk')) | Q(groups__permissions=OuterRef('pk')))
        return Permission.objects.filter(Exists(User.objects.filter(q)))

    def _get_changeable_groups(self, user):
        if user.is_superuser:
            return Group.objects.all()
        # Exclude groups which have at least one permission this user does not effectively have.

        # Get permissions this user does not have.
        # Filter them to match any given group.
        q = Q(pk=user.id) & (Q(user_permissions=OuterRef('pk')) | Q(groups__permissions=OuterRef('pk')))
        missing = Exists(Permission.objects.exclude(Exists(User.objects.filter(q))).filter(group=OuterRef('pk')))
        # Exclude groups which have at least one match.
        return Group.objects.exclude(missing)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'groups':
            kwargs['queryset'] = self._get_changeable_groups(request.user)
        if db_field.name == 'user_permissions':
            kwargs['queryset'] = self._get_changeable_permissions(request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


admin.site.unregister(User)
admin.site.register(User, KronofotoUserAdmin)

@admin.register(LogEntry)
class LogEntryAdmin(base_admin.ModelAdmin):
    date_hierarchy = 'action_time'

    list_filter = [
        'user',
        'content_type',
        'action_flag',
    ]

    search_fields = [
        'object_repr',
        'change_message',
    ]

    list_display = [
        'action_time',
        'user',
        'content_type',
        'action_flag',
    ]

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False

    def has_view_permission(self, request, *args, **kwargs):
        return request.user.is_superuser
