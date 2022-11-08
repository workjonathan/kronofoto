from django.contrib.gis import admin
from django.contrib import admin as base_admin
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from django.forms import widgets
from .models import Photo, PhotoSphere, PhotoSpherePair, Tag, Term, PhotoTag, Donor, NewCutoff, CSVRecord
from .forms import PhotoSphereAddForm, PhotoSphereChangeForm, PhotoSpherePairInlineForm
from django.db.models import Count
from django.db import IntegrityError
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django import forms
from django.forms import ModelForm, Textarea

admin.site.site_header = 'Fortepan Administration'
admin.site.site_title = 'Fortepan Administration'
admin.site.index_title = 'Fortepan Administration Index'

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
    pass


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    search_fields = ['last_name', 'first_name']

    list_display = ('__str__', 'donated', 'scanned')

    def scanned(self, obj):
        return '{} photos'.format(obj.scanned_count)

    def donated(self, obj):
        return '{} photos'.format(obj.donated_count)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate_scannedcount().annotate_donatedcount()

    scanned.admin_order_field = 'scanned_count'
    donated.admin_order_field = 'donated_count'


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    pass


class TagInline(admin.TabularInline):
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


class TagFilter(base_admin.SimpleListFilter):
    title = "tag status"
    parameter_name = "phototag__accepted"

    def lookups(self, request, model_admin):
        return (
            ("needs approval", "needs approval"),
            ("approved", "approved"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'approved':
            return queryset.filter(phototag__accepted=True)
        elif self.value() == "needs approval":
            return queryset.filter(phototag__accepted=False)


class YearIsSetFilter(base_admin.SimpleListFilter):
    title = "photo dated"
    parameter_name = "dated"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.filter(year__isnull=False)
        elif self.value() == 'No':
            return queryset.filter(year__isnull=True)


class IsPublishedFilter(base_admin.SimpleListFilter):
    title = "photo is published"
    parameter_name = "is published"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.filter(is_published=True)
        elif self.value() == 'No':
            return queryset.filter(is_published=False)

class HasLocationFilter(base_admin.SimpleListFilter):
    title = "photo has city or county"
    parameter_name = "is located"

    def lookups(self, request, model_admin):
        return (
            ("City", "City"),
            ("County", "County"),
            ("Neither", "Neither"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'County':
            return queryset.exclude(county="")
        elif self.value() == 'City':
            return queryset.exclude(city="")
        elif self.value() == 'Neither':
            return queryset.filter(city="") & queryset.filter(county="")

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


def publish_photos(modeladmin, request, queryset):
    try:
        queryset.update(is_published=True)
    except IntegrityError:
        modeladmin.message_user(request, 'All published photos must have a donor', messages.ERROR)

publish_photos.short_description = 'Publish photos'

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
class PhotoAdmin(admin.OSMGeoAdmin):
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
        return mark_safe('<img src="{}" width="{}" height="{}" />'.format(obj.h700.url, obj.h700.width, obj.h700.height))

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

class KronofotoUserAdmin(UserAdmin):
    inlines = (UserTagInline,)

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
