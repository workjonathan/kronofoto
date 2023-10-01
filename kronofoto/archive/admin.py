from django.contrib.gis import admin
from urllib.parse import quote as urlquote
from django.contrib import admin as base_admin
from django.contrib.admin.utils import quote
from django.core.files.base import ContentFile
from django.contrib.auth.models import User, Permission, Group
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth import get_permission_codename
from django.utils.safestring import mark_safe
from django.forms import widgets
from .models import Photo, PhotoSphere, PhotoSpherePair, Tag, Term, PhotoTag, Donor, NewCutoff, CSVRecord
from .models.photosphere import MainStreetSet
from .models.photo import Submission
from .models.archive import Archive, ArchiveUserPermission, ArchiveAgreement
from .models.csvrecord import ConnecticutRecord
from .forms import PhotoSphereAddForm, PhotoSphereChangeForm, PhotoSpherePairInlineForm
from django.db.models import Count, Q, Exists, OuterRef, F, ManyToManyField, QuerySet, ForeignKey
from django_stubs_ext import WithAnnotations
from django.db import IntegrityError, router, transaction
from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.contrib import messages
from django import forms
from functools import reduce, update_wrapper
import operator
from collections import defaultdict
from .auth.forms import FortepanAuthenticationForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from typing import Any, Optional, Type, DefaultDict, Set, Dict, Callable, List, Tuple, TypedDict, Sequence, TYPE_CHECKING
from django.urls import URLPattern
if TYPE_CHECKING:
    from django.contrib.admin.options import _FieldsetSpec
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.utils.html import format_html

admin.site.site_header = 'Fortepan Administration'
admin.site.site_title = 'Fortepan Administration'
admin.site.index_title = 'Fortepan Administration Index'
admin.site.login_form = FortepanAuthenticationForm

class HasPhotoFilter(base_admin.SimpleListFilter):
    title = "has photo"
    parameter_name = "photo"

    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> Tuple[Tuple[str, str], ...]:
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Photo]) -> QuerySet[Photo]:
        if self.value() == 'Yes':
            return queryset.exclude(photo__isnull=True)
        elif self.value() == 'No':
            return queryset.filter(photo__isnull=True)
        return queryset

class HasYearFilter(base_admin.SimpleListFilter):
    title = "has year"
    parameter_name = "cleaned_year__isnull"

    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> Tuple[Tuple[str, str], ...]:
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Photo]) -> QuerySet[Photo]:
        if self.value() == 'Yes':
            return queryset.filter(cleaned_year__isnull=False)
        elif self.value() == 'No':
            return queryset.filter(cleaned_year__isnull=True)
        return queryset

class IsPublishableFilter(base_admin.SimpleListFilter):
    title = "is publishable"
    parameter_name = "publishable"

    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> Tuple[Tuple[str, str], ...]:
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Photo]) -> QuerySet[Photo]:
        if self.value() == 'Yes':
            return queryset.filter(publishable=True)
        elif self.value() == 'No':
            return queryset.filter(publishable=False)
        return queryset

class LocationEnteredFilter(base_admin.SimpleListFilter):
    title = "location entered"
    parameter_name = "location"

    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> Tuple[Tuple[str, str], ...]:
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Photo]) -> QuerySet[Photo]:
        if self.value() == 'Yes':
            return queryset.exclude(cleaned_city='', cleaned_county='', cleaned_state='', cleaned_country='')
        elif self.value() == 'No':
            return queryset.filter(cleaned_city='', cleaned_county='', cleaned_state='', cleaned_country='')
        return queryset

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

    def thumbnail(self, obj: Any) -> str:
        src = 'https://ctdigitalarchive.org/islandora/object/{}/datastream/JPG'.format(str(obj))
        return mark_safe('<a href="{src}" target="_blank"><img src="{src}" width="200" /></a>'.format(src=src))

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    #def has_change_permission(self, request, obj=None):
    #    return False

class AgreementInline(admin.StackedInline):
    model = ArchiveAgreement
    extra = 0

@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    inlines = (AgreementInline,)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ['tag']

    def get_readonly_fields(self, request: HttpRequest, obj: Optional[Tag]=None) -> Sequence[str]:
        fields = super().get_readonly_fields(request, obj)
        if obj:
            fields = list(fields) + ['tag']
        return fields


@admin.register(NewCutoff)
class NewCutoffAdmin(admin.ModelAdmin):
    def has_add_permission(self, request: HttpRequest) -> bool:
        if NewCutoff.objects.all().exists():
            return False
        else:
            return super().has_add_permission(request)


class ArchivePermissionMixin:
    def has_add_permission(self, request: HttpRequest, *args: Any) -> Any:
        codename_add = get_permission_codename('add', self.opts)# type: ignore
        return (super().has_add_permission(request, *args)# type: ignore
            or request.user.has_perm("{}.any.{}".format(self.opts.app_label, codename_add)))# type: ignore

    def has_change_permission(self, request: HttpRequest, obj: Any=None) -> bool:
        codename_change = get_permission_codename('change', self.opts) # type: ignore
        return (super().has_change_permission(request, obj) # type: ignore
            or (request.user.has_perm("{}.archive.{}.{}".format(self.opts.app_label, obj.archive.slug, codename_change))# type: ignore
                if obj
                else request.user.has_perm("{}.any.{}".format(self.opts.app_label, codename_change)))# type: ignore
        )

    def has_view_permission(self, request: HttpRequest, obj: Any=None) -> bool:
        if super().has_view_permission(request, obj): # type: ignore
            return True
        opts = self.opts # type: ignore
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

    def has_delete_permission(self, request: HttpRequest, obj: Any=None) -> bool:
        codename_delete = get_permission_codename('delete', self.opts) # type: ignore
        return (super().has_delete_permission(request, obj) # type: ignore
            or (request.user.has_perm("{}.archive.{}.{}".format(self.opts.app_label, obj.archive.slug, codename_delete)) # type: ignore
                if obj
                else request.user.has_perm("{}.any.{}".format(self.opts.app_label, codename_delete)) # type: ignore
            ))

    def has_view_or_change_all(self, request: HttpRequest) -> bool:
        return super().has_view_permission(request) or super().has_change_permission(request) # type: ignore


class FilteringArchivePermissionMixin(ArchivePermissionMixin):
    def get_queryset(self, request: HttpRequest) -> WithAnnotations[Any]:
        qs = super().get_queryset(request) # type: ignore
        if not self.has_view_or_change_all(request):
            opts = self.opts # type: ignore
            codename_view = get_permission_codename('view', opts)
            codename_change = get_permission_codename('change', opts)
            related_query_name = qs.model._meta.get_field('archive').related_query_name()
            q = (
                (Q(codename=codename_change) | Q(codename=codename_view)) &
                Q(
                    content_type__model=opts.model_name,
                    archiveuserpermission__user=request.user,
                    **{'archiveuserpermission__archive__{}'.format(related_query_name): OuterRef('pk')},
                )
            )
            qs = qs.filter(Exists(Permission.objects.filter(q)))
        return qs

@admin.register(Donor)
class DonorAdmin(FilteringArchivePermissionMixin, admin.ModelAdmin):
    search_fields = ['last_name', 'first_name']

    list_display = ('__str__', 'donated', 'scanned', "photographed", "photography_collection")
    class WithScannedCount(TypedDict):
        scanned_count: int

    class WithDonatedCount(TypedDict):
        donated_count: int

    class WithPhotographedCount(TypedDict):
        photographed_count: int

    def scanned(self, obj: "WithAnnotations[Donor, WithScannedCount]") -> str:
        return '{} photos'.format(obj.scanned_count)

    def donated(self, obj: "WithAnnotations[Donor, WithDonatedCount]") -> str:
        return '{} photos'.format(obj.donated_count)

    def photographed(self, obj: "WithAnnotations[Donor, WithPhotographedCount]") -> str:
        return '{} photos'.format(obj.photographed_count)

    scanned.admin_order_field = 'scanned_count' # type: ignore
    donated.admin_order_field = 'donated_count' # type: ignore
    photographed.admin_order_field = 'photographed_count' # type: ignore

    def photography_collection(self, obj: Donor) -> str:
        return mark_safe('<a class="button" href="{}?query=photographer_exact:{}">View Photography Collection</a>'.format(reverse("kronofoto:gridview"), obj.id))

    def get_queryset(self, request: HttpRequest) -> WithAnnotations[Any]:
        qs = super().get_queryset(request)
        return qs.annotate_scannedcount().annotate_donatedcount().annotate_photographedcount()

    def formfield_for_foreignkey(
        self, db_field: ForeignKey, request: HttpRequest, **kwargs: Any
    ) -> forms.ModelChoiceField:
        if not self.has_view_or_change_all(request):
            opts = self.opts
            codename_add = get_permission_codename('add', opts)
            codename_change = get_permission_codename('change', opts)
            kwargs['queryset'] = Archive.objects.filter(Q(
                archiveuserpermission__user=request.user,
                archiveuserpermission__permission__content_type__model=opts.model_name,
            ) & (Q(archiveuserpermission__permission__codename=codename_add) | Q(archiveuserpermission__permission__codename=codename_change)))
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

    def submitter(self, instance: PhotoTag) -> str:
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

    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> Tuple[Tuple[str, str], ...]:
        return (
            ("0", "0"),
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("4+", "4+"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Photo]) -> QuerySet[Photo]:
        value = self.value()
        if value:
            queryset = queryset.annotate(Count("terms"))
        if value in ("0", "1", "2", "3"):
            return queryset.filter(terms__count=int(value))
        elif value == "4+":
            return queryset.filter(terms__count__gte=4)
        else:
            return queryset


class StandardSimpleListFilter(base_admin.SimpleListFilter):
    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> List[Tuple[str, str]]:
        return [(label, label) for (label, value) in self.filters] # type: ignore

    def queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> QuerySet[Any]:
        for label, value in self.filters: # type: ignore
            if self.value() == label:
                return queryset.filter(**{self.field: value}).distinct() # type: ignore
        return queryset


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

    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> Tuple[Tuple[str, str], ...]:
        return (
            ("City", "City"),
            ("County", "County"),
            ("State only", "State only"),
            ("Country only", "Country only"),
            ("No location", "No location"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Photo]) -> QuerySet[Photo]:
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
        return queryset

class HasGeoLocationFilter(base_admin.SimpleListFilter):
    title = "photo is geolocated"
    parameter_name = "is geolocated"

    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> Tuple[Tuple[str, str], ...]:
        return (
            ("Yes", "Point and Polygon"),
            ("Maybe", "Point or Polygon"),
            ("Point only", "Point only"),
            ("Polygon only", "Polygon only"),
            ("No", "No"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Photo]) -> QuerySet[Photo]:
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
        return queryset


@admin.action(permissions=["change"])
def publish_photos(modeladmin: Any, request: Any, queryset: QuerySet[Photo]) -> None:
    try:
        queryset.update(is_published=True)
    except IntegrityError:
        modeladmin.message_user(request, 'All published photos must have a donor', messages.ERROR)

publish_photos.short_description = 'Publish photos' # type: ignore

@admin.action(permissions=["change"])
def unpublish_photos(modeladmin: Any, request: Any, queryset: QuerySet[Photo]) -> None:
    queryset.update(is_published=False)
unpublish_photos.short_description = 'Unpublish photos' # type: ignore

@admin.register(MainStreetSet)
class MainStreetSetAdmin(base_admin.ModelAdmin):
    pass

class PhotoInline(admin.StackedInline):
    model = PhotoSpherePair
    extra = 0
    fields = ['photo', 'position']
    raw_id_fields = ['photo']
    form = PhotoSpherePairInlineForm

class MainstreetSetIsSetFilter(StandardSimpleListFilter):
    # should be deleted when db constraint is enabled
    title = "belongs to set"
    parameter_name = "in_set"
    field = 'mainstreetset__isnull'

    filters = (
        ("Yes", False),
        ("No", True),
    )


@admin.register(PhotoSphere)
class PhotoSphereAdmin(admin.OSMGeoAdmin):
    form = PhotoSphereChangeForm
    add_form = PhotoSphereAddForm
    list_filter = (MainstreetSetIsSetFilter,) # should be deleted when db constraint is enabled
    list_display = ('title', 'description')
    search_fields = ('title', 'description')
    inlines = (PhotoInline,)

    def get_form(
        self, request: HttpRequest, obj: Optional[PhotoSphere] = None, change: bool=False, **kwargs: Any
    ) -> "Type[forms.ModelForm[PhotoSphere]]":
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, change, **defaults)

    def get_fieldsets(self, request: HttpRequest, obj: Optional[Any] = ...) -> "_FieldsetSpec":
        if obj is None:
            fieldsets: "_FieldsetSpec" = (
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

    def has_add_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def has_change_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> QuerySet[CSVRecord]:
        qs = super().get_queryset(request)
        return qs.filter(photo__isnull=True)


@admin.register(Submission)
class SubmissionAdmin(FilteringArchivePermissionMixin, admin.OSMGeoAdmin):
    change_form_template = 'admin/custom_changeform.html'
    readonly_fields = ["image_display"]
    class AcceptForm(forms.ModelForm):
        class Meta:
            model = Photo
            fields = ['is_published', 'is_featured']

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.fields['is_published'].label_suffix = ''
            self.fields['is_featured'].label_suffix = ''


    def get_urls(self) -> List[URLPattern]:
        from django.urls import path
        def wrap(view: Callable[..., object]) -> Callable[..., HttpResponse]:
            def wrapper(*args: Any, **kwargs: Any) -> HttpResponse:
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self # type: ignore
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name
        return [path("<int:object_id>/accept/", wrap(self.accept_view), name="{}_{}_accept".format(*info))] + super().get_urls()

    def accept_view(self, request: HttpRequest, object_id: int, form_url: str='', extra_context: Optional[Dict[Any, Any]]=None) -> HttpResponse:
        extra_context = extra_context or {}
        form_class = self.AcceptForm
        model = self.model
        opts = model._meta
        if request.method and request.method.lower() == 'post':
            form = form_class(request.POST)
            if form.is_valid():
                target_model = Photo
                photo_opts = target_model._meta
                codename_add = get_permission_codename('add', photo_opts)
                with transaction.atomic(using=router.db_for_write(model)):
                    obj: Optional[Submission] = self.get_object(request, quote(str(object_id)))
                    user = request.user
                    assert not user.is_anonymous
                    if obj:
                        if self.has_delete_permission(request, obj) and (user.has_perm('{}.archive.{}.{}'.format(photo_opts.app_label, obj.archive.slug, codename_add)) or user.has_perm('{}.any.{}'.format(photo_opts.app_label, codename_add))):
                            file = ContentFile(obj.image.read())
                            file.name = "submittedphoto"
                            file.close()
                            file.open()
                            new_obj = target_model(
                                archive=obj.archive,
                                donor=obj.donor,
                                photographer=obj.photographer,
                                address=obj.address,
                                city=obj.city,
                                county=obj.county,
                                state=obj.state,
                                country=obj.country,
                                year=obj.year,
                                circa=obj.circa,
                                caption=obj.caption,
                                scanner=obj.scanner,
                                original=file,
                                is_published=form.cleaned_data['is_published'],
                                is_featured=form.cleaned_data['is_featured'],
                            )
                            new_obj.save()
                            new_obj_url = reverse("admin:{}_{}_change".format(photo_opts.app_label, photo_opts.model_name), args=[new_obj.pk], current_app=self.admin_site.name)
                            msg_list = [photo_opts.verbose_name, format_html('<a href="{}">{}</a>', new_obj_url, str(new_obj))]
                            msg_continue = format_html('The {} "{}" was accepted successfully. You may edit it below.', *msg_list)
                            msg_accept = format_html('The {} "{}" was accepted successfully. You may accept or edit other submissions below', *msg_list)
                            obj.image.delete(save=False)
                            obj.delete()
                            if '_accept' in request.POST:
                                url = reverse("admin:{}_{}_changelist".format(opts.app_label, opts.model_name), current_app=self.admin_site.name)
                                self.message_user(request, msg_accept, messages.SUCCESS)
                                return HttpResponseRedirect(url)
                            else:
                                self.message_user(request, msg_continue, messages.SUCCESS)
                                return HttpResponseRedirect(new_obj_url)
                        else:
                            raise PermissionDenied
                    else:
                        msg = '{name} with ID “{key}” doesn’t exist. Perhaps it was deleted?'.format(
                            name=opts.verbose_name,
                            key=object_id,
                        )
                        self.message_user(request, msg, messages.WARNING)
                        url = reverse('admin:index', current_app=self.admin_site.name)
                        return HttpResponseRedirect(url)
            else:
                # form invalid. Should probably render form by itself at this point.
                # although there is no way for this form to be invalid.
                # For now, message user.
                self.message_user(request, "The accept submission form was invalid.", messages.ERROR)
                obj_url = reverse("admin:{}_{}_change".format(opts.app_label, opts.model_name), args=[object_id], current_app=self.admin_site.name)
                return HttpResponseRedirect(obj_url)
        else:
            obj_url = reverse("admin:{}_{}_change".format(opts.app_label, opts.model_name), args=[object_id], current_app=self.admin_site.name)
            return HttpResponseRedirect(obj_url)

    def change_view(self, request: HttpRequest, object_id: str, form_url: str='', extra_context: Optional[Dict[Any, Any]]=None) -> HttpResponse:
        extra_context = extra_context or {}
        extra_context['accept_form'] = self.AcceptForm({"is_published": True})
        return super().change_view(request, object_id, form_url, extra_context)
    #def response_change(self, request, obj: Submission):
    #    if '_accept_submission' in request.POST:
    #        pass
    #    else:
    #        return super().response_change(request, obj)

    def image_display(self, obj: Submission) -> str:
        return mark_safe('<img src="{}" width="{}" height="{}" />'.format(obj.image.url, obj.image.width, obj.image.height))

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

    def thumb_image(self, obj: Photo) -> str:
        return mark_safe('<img src="{}" width="{}" height="{}" />'.format(obj.thumbnail.url, obj.thumbnail.width, obj.thumbnail.height))

    def h700_image(self, obj: Photo) -> str:
        if obj.h700:
            return mark_safe('<img src="{}" width="{}" height="{}" />'.format(obj.h700.url, obj.h700.width, obj.h700.height))
        else:
            return "-"

    def formfield_for_foreignkey(
        self, db_field: ForeignKey, request: HttpRequest, **kwargs: Any
    ) -> forms.ModelChoiceField:
        if db_field.name == 'donor':
            kwargs['queryset'] = Donor.objects.filter(is_contributor=True)
        if db_field.name == 'photographer':
            kwargs['queryset'] = Donor.objects.filter(is_photographer=True)
        if db_field.name == 'scanner':
            kwargs['queryset'] = Donor.objects.filter(is_scanner=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_form(self, request: HttpRequest, form: Any, change: Any) -> Photo:
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

    def thumb_image(self, instance: Any) -> str:
        return mark_safe(
            '<a href="{edit_url}"><img src="{thumb}" width="{width}" height="{height}" /></a>'.format(
                edit_url=reverse('admin:archive_photo_change', args=(instance.phototag.photo.id,)),
                thumb=instance.phototag.photo.thumbnail.url,
                width=instance.phototag.photo.thumbnail.width,
                height=instance.phototag.photo.thumbnail.height,
            )
        )

    def tag(self, instance: Any) -> str:
        return instance.phototag.tag.tag

    def accepted(self, instance: Any) -> str:
        return 'yes' if instance.phototag.accepted else 'no'

class UserArchivePermissionsInline(base_admin.TabularInline):
    model = Archive.users.through
    extra = 1

    def formfield_for_manytomany(self, db_field: ManyToManyField, request: HttpRequest, **kwargs: Any) -> Optional[forms.ModelMultipleChoiceField]:
        if db_field.name == 'permission':
            models = [
                'donor',
                'photo',
                'submission',
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

class PermissionAnalyst:
    def __init__(self, user: User) -> None:
        self.user = user
    class WithArchiveId(TypedDict):
        archive_id: int
    def get_archive_permissions(self) -> DefaultDict[int, Set["WithAnnotations[Permission, WithArchiveId]"]]:
        sets = defaultdict(set)
        objects = (Permission.objects
            .filter(archiveuserpermission__user__id=self.user.id)
            .annotate(archive_id=F('archiveuserpermission__archive__id'))
        )
        for obj in objects:
            sets[obj.archive_id].add(obj)
        return sets

    def get_changeable_permissions(self) -> QuerySet[Permission]:
        if self.user.is_superuser:
            return Permission.objects.all()
        q = Q(pk=self.user.id) & (Q(user_permissions=OuterRef('pk')) | Q(groups__permissions=OuterRef('pk')))
        return Permission.objects.filter(Exists(User.objects.filter(q)))

    def get_changeable_groups(self) -> QuerySet[Group]:
        if self.user.is_superuser:
            return Group.objects.all()
        # Exclude groups which have at least one permission this user does not effectively have.

        # Get permissions this user does not have.
        # Filter them to match any given group.
        q = Q(pk=self.user.id) & (Q(user_permissions=OuterRef('pk')) | Q(groups__permissions=OuterRef('pk')))
        missing = Exists(Permission.objects.exclude(Exists(User.objects.filter(q))).filter(group=OuterRef('pk')))
        # Exclude groups which have at least one match.
        return Group.objects.exclude(missing)

class block_group_escalation:
    def __init__(self, *, editor: User, group: Group, PAClass: Type[PermissionAnalyst]=PermissionAnalyst):
        self.editor = PAClass(editor)
        self.group = group

    def __enter__(self) -> None:
        self.changeable_perms = set(self.editor.get_changeable_permissions())
        self.old_perms = set(self.group.permissions.all())

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        new_perms = set(self.group.permissions.all())
        self.group.permissions.set((self.old_perms - self.changeable_perms) | (self.changeable_perms & new_perms))

class block_escalation:
    def __init__(self, *, editor: User, user: User, PAClass: Type[PermissionAnalyst]=PermissionAnalyst) -> None:
        self.editor = PAClass(editor)
        self.user = user
        self.user_analyst = PAClass(user)

    def __enter__(self) -> None:
        self.changeable_archive_permissions = self.editor.get_archive_permissions()
        self.old_archives = set(self.user.archiveuserpermission_set.all())
        self.old_archive_permissions = self.user_analyst.get_archive_permissions()

        self.old_perms = set(self.user.user_permissions.all())
        self.old_groups = set(self.user.groups.all())
        self.changeable_perms = set(self.editor.get_changeable_permissions())
        self.changeable_groups = set(self.editor.get_changeable_groups())

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        new_perms = set(self.user.user_permissions.all())
        new_groups = set(self.user.groups.all())
        self.user.user_permissions.set((self.old_perms - self.changeable_perms) | (self.changeable_perms & new_perms))
        self.user.groups.set((self.old_groups - self.changeable_groups) | (self.changeable_groups & new_groups))

        new_archives = set(self.user.archiveuserpermission_set.all())
        new_archive_permissions = self.user_analyst.get_archive_permissions()
        changed_archive_perms = self.old_archives | new_archives
        for related in changed_archive_perms:

            assign = (self.old_archive_permissions[related.archive.id] - (self.changeable_archive_permissions[related.archive.id] | self.changeable_perms)) | ((self.changeable_archive_permissions[related.archive.id] | self.changeable_perms) & new_archive_permissions[related.archive.id]) # type: ignore
            try:
                obj = self.user.archiveuserpermission_set.get(archive__id=related.archive.id)
                obj.permission.set(assign)
            except ObjectDoesNotExist:
                if assign:
                    obj = Archive.users.through.objects.create(archive=related.archive, user=self.user) # type: ignore
                    obj.permission.set(assign)


class KronofotoUserAdmin(UserAdmin):
    inlines = (UserArchivePermissionsInline, UserTagInline,)

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: Any) -> None:
        # the symmetric difference of before edit and after edit will be a subset of editor's privileges
        # (a ^ a') <= e

        # a user editing their own account will never have more privileges.
        # e' <= e

        instance = form.instance
        if not request.user.is_anonymous:
            with block_escalation(editor=request.user, user=instance):
                super().save_related(request, form, formsets, change)

    def formfield_for_manytomany(self, db_field: ManyToManyField, request: HttpRequest, **kwargs: Any) -> Optional[forms.ModelMultipleChoiceField]:
        assert not request.user.is_anonymous
        permission_analyst = PermissionAnalyst(request.user)
        if db_field.name == 'groups':
            kwargs['queryset'] = permission_analyst.get_changeable_groups()
        if db_field.name == 'user_permissions':
            kwargs['queryset'] = permission_analyst.get_changeable_permissions()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_fieldsets(self, request: HttpRequest, obj: Optional[Any] = ...) -> "_FieldsetSpec":
        fieldsets = super().get_fieldsets(request, obj)
        if obj and not request.user.is_superuser:
            fieldsets[2][1]['fields'] = ('is_active', 'is_staff', 'groups', 'user_permissions')
        return fieldsets




class KronofotoGroupAdmin(GroupAdmin):

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: Any) -> None:
        instance = form.instance
        if not request.user.is_anonymous:
            with block_group_escalation(editor=request.user, group=instance):
                super().save_related(request, form, formsets, change)

    def formfield_for_manytomany(self, db_field: ManyToManyField, request: HttpRequest, **kwargs: Any) -> Optional[forms.ModelMultipleChoiceField]:
        assert not request.user.is_anonymous
        if db_field.name == 'permissions':
            kwargs['queryset'] = PermissionAnalyst(request.user).get_changeable_permissions()
        return super().formfield_for_manytomany(db_field, request, **kwargs)


admin.site.unregister(User)
admin.site.register(User, KronofotoUserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, KronofotoGroupAdmin)

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

    def has_add_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def has_change_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def has_delete_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def has_view_permission(self, request: HttpRequest, *args: Any, **kwargs: Any) -> bool:
        return request.user.is_superuser
