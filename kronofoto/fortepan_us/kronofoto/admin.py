from django.contrib.gis import admin
from urllib.parse import quote as urlquote
from django.contrib import admin as base_admin
from django.template import Template, RequestContext
from django.contrib.admin.utils import quote
from django.core.files.base import ContentFile
from mptt.admin import MPTTModelAdmin # type: ignore
from django.contrib.auth.models import User, Permission, Group
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth import get_permission_codename
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from django.forms import widgets
from fortepan_us.kronofoto.models import Photo, PhotoSphere, PhotoSpherePair, Tag, Term, PhotoTag, Donor, NewCutoff, CSVRecord, TermGroup, Place, Exhibit, PhotoSphereInfo
from fortepan_us.kronofoto.models.photosphere import MainStreetSet
from mptt.admin import MPTTModelAdmin # type: ignore
from fortepan_us.kronofoto.models.photo import Submission
from fortepan_us.kronofoto.models.archive import Archive, ArchiveUserPermission, ArchiveAgreement, ArchiveGroupPermission
from fortepan_us.kronofoto.models.category import Category, ValidCategory
from fortepan_us.kronofoto.models.csvrecord import ConnecticutRecord
from fortepan_us.kronofoto.forms import PhotoSphereAddForm, PhotoSphereChangeForm, PhotoSpherePairInlineForm, SubmissionForm, PhotoForm, PhotoSphereInfoInlineForm
from django.db.models import Count, Q, Exists, OuterRef, F, ManyToManyField, QuerySet, ForeignKey, Model, Manager
from django.db import IntegrityError, router, transaction
from django.db.models.options import Options
from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.contrib import messages
from django import forms
from functools import reduce, update_wrapper, cached_property
import operator
from collections import defaultdict
from fortepan_us.kronofoto.auth.forms import FortepanAuthenticationForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from typing import Any, Optional, Type, DefaultDict, Set, Dict, Callable, List, Tuple, TypedDict, Sequence, TYPE_CHECKING, TypeVar, Protocol, ContextManager, Union
from django.urls import URLPattern
if TYPE_CHECKING:
    from django.contrib.admin.options import _FieldsetSpec
    from django_stubs_ext import WithAnnotations
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.utils.html import format_html, format_html_join, html_safe
from django.shortcuts import get_object_or_404
from dataclasses import dataclass

admin.site.site_header = 'Fortepan Administration'
admin.site.site_title = 'Fortepan Administration'
admin.site.index_title = 'Fortepan Administration Index'
admin.site.login_form = FortepanAuthenticationForm

from .models import Exhibit, Card, PhotoCard, Figure

class CardInline(admin.StackedInline):
    model = Card
    extra = 1
    raw_id_fields = ['photo',]
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).filter(card_type=0)

class PhotoCardInline(admin.StackedInline):
    model = Card
    raw_id_fields = ['photo',]
    extra = 1
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).exclude(card_type=0)


@admin.register(Exhibit)
class ExhibitAdmin(admin.ModelAdmin):
    raw_id_fields = ['photo', 'owner']
    inlines = (CardInline, PhotoCardInline)

class HasPhotoFilter(base_admin.SimpleListFilter):
    title = "has photo"
    parameter_name = "photo"

    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> Tuple[Tuple[str, str], ...]:
        return (
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[ConnecticutRecord]) -> QuerySet[ConnecticutRecord]:
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

    def queryset(self, request: HttpRequest, queryset: QuerySet[ConnecticutRecord]) -> QuerySet[ConnecticutRecord]:
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

    def queryset(self, request: HttpRequest, queryset: QuerySet[ConnecticutRecord]) -> QuerySet[ConnecticutRecord]:
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

    def queryset(self, request: HttpRequest, queryset: QuerySet[ConnecticutRecord]) -> QuerySet[ConnecticutRecord]:
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

class CategoryInline(admin.TabularInline):
    model = ValidCategory
    extra = 0

@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    inlines = (CategoryInline, AgreementInline)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ['tag']

    def get_readonly_fields(self, request: HttpRequest, obj: Optional[Tag]=None) -> List[str]:
        fields = list(super().get_readonly_fields(request, obj))
        if obj:
            fields = fields + ['tag']
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
    def get_queryset(self, request: HttpRequest) -> "WithAnnotations[Any]":
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
    class WithCounts(TypedDict):
        photographed_count: int
        donated_count: int
        scanned_count: int

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

    def get_queryset(self, request: HttpRequest) -> "QuerySet[WithAnnotations[Donor, WithCounts]]":
        qs = super().get_queryset(request)
        return qs.annotate_scannedcount().annotate_donatedcount().annotate_photographedcount()

    def formfield_for_foreignkey(
        self, db_field: ForeignKey, request: HttpRequest, **kwargs: Any
    ) -> Optional[forms.ModelChoiceField]:
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
    list_display = ("term", "group")


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

class HasPlaceFilter(base_admin.SimpleListFilter):
    title = "place status"
    parameter_name = "place__isnull"

    def lookups(self, request: HttpRequest, model_admin: "admin.ModelAdmin[Any]") -> Tuple[Tuple[str, str], ...]:
        return (
            ("has place", "has place"),
            ("has no place", "has no place"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Photo]) -> QuerySet[Photo]:
        value = self.value()
        if value  == "has place":
            return queryset.filter(place__isnull=False)
        elif value == "has no place":
            return queryset.filter(place__isnull=True)
        else:
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
            ("Yes", "Yes"),
            ("No", "No"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[Photo]) -> QuerySet[Photo]:
        if self.value() == 'Yes':
            return queryset.filter(location_point__isnull=False)
        elif self.value() == 'No':
            return queryset.filter(location_point__isnull=True)
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

@admin.register(TermGroup)
class TermGroupAdmin(base_admin.ModelAdmin):
    pass
@admin.register(MainStreetSet)
class MainStreetSetAdmin(base_admin.ModelAdmin):
    pass

class PhotoInfoInline(admin.StackedInline):
    model = PhotoSphereInfo
    extra = 0
    form = PhotoSphereInfoInlineForm
    fields = ['text', 'position']

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

#@html_safe
class ImportMap:
    def __html__(self) -> str:
        return """<script type="importmap">
            {
                "imports": {
                    "three": "https://cdn.jsdelivr.net/npm/three/build/three.module.js",
                    "@photo-sphere-viewer/core": "https://cdn.jsdelivr.net/npm/@photo-sphere-viewer/core/index.module.js",
                    "@photo-sphere-viewer/compass-plugin": "https://cdn.jsdelivr.net/npm/@photo-sphere-viewer/compass-plugin/index.module.js"
                }
            }
        </script>"""

@dataclass(frozen=True)
class ResourceIntegrity:
    src: str
    integrity: str
    crossorigin: str = ""
    format_str: str = ""

    def __html__(self) -> str:
       return self.format_str.format(location=self.src, integrity=self.integrity, crossorigin=self.crossorigin) # type: ignore


def JSWIntegrity(*, src: str, integrity: str, crossorigin: str="") -> ResourceIntegrity:
    return ResourceIntegrity(src=src, integrity=integrity, crossorigin=crossorigin, format_str="""<script src="{location}" integrity="{integrity}" crossorigin="{crossorigin}"></script>""")

def CSSWIntegrity(*, src: str, integrity: str, crossorigin: str="") -> ResourceIntegrity:
    return ResourceIntegrity(src=src, integrity=integrity, crossorigin=crossorigin, format_str="""<link rel="stylesheet" href="{location}" integrity="{integrity}" crossorigin="{crossorigin}" />""")


import django.contrib.admin.views.main
class MapChangeList(django.contrib.admin.views.main.ChangeList):
    pass

class ConfirmConnectForm(forms.Form):
    pk_a = forms.IntegerField(widget=forms.HiddenInput)
    pk_b = forms.IntegerField(widget=forms.HiddenInput)
from djgeojson.serializers import Serializer as GeoJSONSerializer # type: ignore

@admin.register(PhotoSphere)
class PhotoSphereAdmin(admin.GISModelAdmin):
    form = PhotoSphereChangeForm
    add_form = PhotoSphereAddForm
    list_filter = (MainstreetSetIsSetFilter, 'mainstreetset') # should be deleted when db constraint is enabled
    list_display = ('title', 'description')
    search_fields = ('title', 'description')
    inlines = (PhotoInline, PhotoInfoInline)

    class Media:
        js = [
            ImportMap(),
            JSWIntegrity(
                src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
                integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=",
            ),
            JSWIntegrity(
                src="https://unpkg.com/htmx.org@2.0.2",
                integrity="sha384-Y7hw+L/jvKeWIRRkqWYfPcvVxHzVzn5REgzbawhxAuQGwX1XWe70vji+VSeHOThJ",
                crossorigin="anonymous",
            ),
        ]
        css = {"all": [
            "https://cdn.jsdelivr.net/npm/@photo-sphere-viewer/core/index.min.css",
            "https://cdn.jsdelivr.net/npm/@photo-sphere-viewer/markers-plugin/index.min.css",
            "https://cdn.jsdelivr.net/npm/@photo-sphere-viewer/compass-plugin/index.min.css",
            CSSWIntegrity(src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="),
        ]}

    def get_urls(self) -> List[URLPattern]:
        from django.urls import path
        def wrap(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
            def wrapper(*args: Any, **kwargs: Any) -> HttpResponse:
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self # type: ignore
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path("map_edit", wrap(self.map_edit_view), name="{}_{}_map_edit".format(*info)),
            path("map_refresh_point/<int:pk>", wrap(self.map_refresh_point), name="{}_{}_map_refresh_point".format(*info)),
            path("map_propose_connection/<int:pk>", wrap(self.map_propose_connection), name="{}_{}_map_propose_connection".format(*info)),
            path("map_confirm_connection", wrap(self.map_confirm_connection), name="{}_{}_map_confirm_connection".format(*info)),
            path("map_propose_delete/<int:pk>", wrap(self.map_propose_delete), name="{}_{}_map_propose_delete".format(*info)),
            path("map_confirm_delete", wrap(self.map_confirm_delete), name="{}_{}_map_confirm_delete".format(*info)),
        ] + super().get_urls()

    def map_confirm_connection(self, request: HttpRequest) -> HttpResponse:
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        form = ConfirmConnectForm(request.POST)
        if form.is_valid():
            photosphere_a = get_object_or_404(PhotoSphere.objects.all(), pk=form.cleaned_data['pk_a'])
            photosphere_b = get_object_or_404(PhotoSphere.objects.all(), pk=form.cleaned_data['pk_b'])
            photosphere_a.links.add(photosphere_b)
            links = PhotoSphere.links.through.objects.filter(
                from_photosphere_id=photosphere_a.id,
            )
            response = HttpResponse()
            import json
            response['Hx-Trigger'] = json.dumps({
                "admin:add_line": json.loads(GeoJSONSerializer().serialize([self.link_to_json(link) for link in links])),
            })
            return response
        return HttpResponse()

    def map_confirm_delete(self, request: HttpRequest) -> HttpResponse:
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        form = ConfirmConnectForm(request.POST)
        if form.is_valid():
            pk_a = form.cleaned_data['pk_a']
            pk_b = form.cleaned_data['pk_b']
            PhotoSphereThrough = PhotoSphere.links.through
            PhotoSphereThrough.objects.filter(from_photosphere_id=pk_a, to_photosphere_id=pk_b).delete()
            PhotoSphereThrough.objects.filter(from_photosphere_id=pk_b, to_photosphere_id=pk_a).delete()
            response = HttpResponse()
            import json
            response['Hx-Trigger'] = json.dumps({
                "admin:remove_line": {'a': pk_a, 'b': pk_b},
            })
            return response
        return HttpResponse("", status=400)

    def map_propose_delete(self, request: HttpRequest, pk: int) -> HttpResponse:
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        link = get_object_or_404(PhotoSphere.links.through.objects.all(), pk=pk)
        template = Template("""
            Delete this connection from {{ photosphere_a.title }} to {{ photosphere_b.title }}?<br>
            <div>
                <input type="hidden" name="pk_a" value="{{ photosphere_a.pk }}">
                <input type="hidden" name="pk_b" value="{{ photosphere_b.pk }}">
                <button hx-target="closest div" hx-include="closest div" hx-swap="none" hx-post="{% url "admin:kronofoto_photosphere_map_confirm_delete" %}">Delete</button>
            </div>
        """)
        return HttpResponse(template.render(
            context=RequestContext(request, {'photosphere_a': link.from_photosphere, 'photosphere_b': link.to_photosphere})
        ))

    def map_propose_connection(self, request: HttpRequest, pk: int) -> HttpResponse:
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        photosphere_a = get_object_or_404(PhotoSphere.objects.all(), pk=pk)
        photosphere_b = get_object_or_404(PhotoSphere.objects.all(), pk=request.GET.get("pk", -1))
        template = Template("""
            Connect {{ photosphere_a.title }} to {{ photosphere_b.title }}?<br>
            <div>
                <input type="hidden" name="pk_a" value="{{ photosphere_a.pk }}">
                <input type="hidden" name="pk_b" value="{{ photosphere_b.pk }}">
                <button hx-target="closest div" hx-include="closest div" hx-swap="none" hx-post="{% url "admin:kronofoto_photosphere_map_confirm_connection" %}">Connect</button>
            </div>
        """)
        return JsonResponse({
            "coordinates": [
                [photosphere_a.location.y, photosphere_a.location.x], # type: ignore
                [photosphere_b.location.y, photosphere_b.location.x], # type: ignore
            ],
            "content": template.render(
                context=RequestContext(request, {"photosphere_a": photosphere_a, 'photosphere_b': photosphere_b}),
            ),
        })

    def map_refresh_point(self, request: HttpRequest, pk: int) -> HttpResponse:
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        photosphere = get_object_or_404(PhotoSphere.objects.all(), pk=pk)
        PhotoSphereThrough = PhotoSphere.links.through
        links = PhotoSphereThrough.objects.filter(Q(to_photosphere_id=pk) | Q(from_photosphere_id=pk))
        assert photosphere.location
        import json

        return JsonResponse({
            "coordinates": [photosphere.location.y, photosphere.location.x],
            "links": json.loads(GeoJSONSerializer().serialize([self.link_to_json(link) for link in links])),
            "content": format_html('<a href="{}" target="_blank">Edit (new tab)</a><h3>{}</h3><div>{}</div>', reverse("admin:kronofoto_photosphere_change", kwargs={"object_id": photosphere.id}), photosphere.title, photosphere.description),
            "pk": photosphere.pk,
            "connect": reverse("admin:kronofoto_photosphere_map_propose_connection", kwargs={"pk": photosphere.pk}),
            "closeOnClick": False,
        })

    def link_to_json(self, link: Any) -> Dict[str, Any]:
        from django.contrib.gis.geos import LineString
        return {
            'geom': LineString([
                [link.from_photosphere.location.x, link.from_photosphere.location.y],
                [link.to_photosphere.location.x, link.to_photosphere.location.y],
            ]),
            'pk': link.pk,
            'from_pk': link.from_photosphere.pk,
            'to_pk': link.to_photosphere.pk,
            'delete': reverse("admin:kronofoto_photosphere_map_propose_delete", kwargs={"pk": link.pk}),
        }

    def map_edit_view(self, request: HttpRequest) -> HttpResponse:
        app_label = self.opts.app_label
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        # Add the action checkboxes if any actions are available.
        if self.get_actions(request):
            list_display = ["action_checkbox", *list_display]
        sortable_by = self.get_sortable_by(request)
        ChangeList = MapChangeList
        cl = ChangeList(
            request,
            self.model,
            list_display,
            list_display_links,
            self.get_list_filter(request),
            self.date_hierarchy,
            self.get_search_fields(request),
            self.get_list_select_related(request),
            99999999,
            99999999,
            self.list_editable,
            self,
            None,
            "",
        )
        serialized = GeoJSONSerializer().serialize(
            [
                {
                    'geom': object.location,
                    'refresh': reverse("admin:kronofoto_photosphere_map_refresh_point", kwargs={"pk": object.pk}),
                    'pk': object.pk,
                }
                for object in cl.get_queryset(request)
            ],
            with_modelname=False,
        )
        links_serialized = GeoJSONSerializer().serialize(
            [
                self.link_to_json(link)
                for link in cl.opts.model.links.through.objects.filter( # type: ignore
                    to_photosphere_id__in=cl.get_queryset(request),
                    from_photosphere_id__in=cl.get_queryset(request)
                ) # type: ignore
            ],
            with_modelname=False,
        )
        import json
        context = {
            **self.admin_site.each_context(request),
            "module_name": str(self.opts.verbose_name_plural),
            "selection_note": "",
            "selection_note_all": "",
            "title": cl.title,
            "subtitle": None,
            "is_popup": cl.is_popup,
            "to_field": cl.to_field,
            "cl": cl,
            "media": self.media,
            "has_add_permission": self.has_add_permission(request),
            "map_points": json.loads(serialized),
            "map_links": json.loads(links_serialized),
            "opts": cl.opts,
            "actions_on_top": self.actions_on_top,
            "actions_on_bottom": self.actions_on_bottom,
            "actions_selection_counter": self.actions_selection_counter,
            "preserved_filters": self.get_preserved_filters(request),
        }

        request.current_app = self.admin_site.name
        return TemplateResponse(
            request=request,
            template="admin/kronofoto/photosphere/map_edit.html",
            context=context,
        )


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



@base_admin.register(Place)
class PlaceAdmin(MPTTModelAdmin):
    search_fields = ['fullname']
    raw_id_fields = ["parent"]
    list_display = ['fullname', "place_type"]


class PhotoBaseAdmin(FilteringArchivePermissionMixin, admin.GISModelAdmin):
    autocomplete_fields = ['donor', 'scanner', 'photographer', 'place']
    def get_urls(self) -> List[URLPattern]:
        from django.urls import path
        def wrap(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
            def wrapper(*args: Any, **kwargs: Any) -> HttpResponse:
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self # type: ignore
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path("categories", wrap(self.categories_view), name="{}_{}_categories".format(*info)),
        ] + super().get_urls()

    def categories_view(self, request: HttpRequest) -> HttpResponse:
        if request.GET.get('archive', ""):
            categories = Category.objects.filter(archive__id=int(request.GET['archive']))
        else:
            categories = Category.objects.none()
        return TemplateResponse(request, "admin/widgets/categories.html", {'objects': categories})

    def formfield_for_foreignkey(
        self, db_field: ForeignKey, request: HttpRequest, **kwargs: Any
    ) -> Optional[forms.ModelChoiceField]:
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'archive':
            url = reverse('admin:kronofoto_photo_categories')
            if field:
                field.widget.attrs.update({
                    'hx-get': url,
                    'hx-trigger': 'change',
                    'data-archive': '',
                    'hx-target': '[data-category]',
                })
        return field

class AdminCommunication(Protocol):
    @property
    def response(self) -> HttpResponse:
        ...
    @property
    def message(self) -> str:
        ...
    @property
    def message_level(self) -> int:
        ...
class NotifyFactory(Protocol):
    def notify_action(self, *, new_obj: Photo) -> AdminCommunication:
        ...
@dataclass
class AcceptanceFactory:
    current_app: str
    request: HttpRequest
    object_id: int
    admin: admin.ModelAdmin
    user: User
    opts: "Options[Submission]" = Submission._meta
    photo_opts: "Options[Photo]" = Photo._meta
    def notify_action(self, *, new_obj: Photo) -> AdminCommunication:
        if '_accept' in self.request.POST:
            return SubmissionAdmin.AcceptAction(photo_opts=self.photo_opts, app_label=self.opts.app_label, model_name=self.opts.model_name, current_app=self.current_app, new_obj=new_obj)
        else:
            return SubmissionAdmin.ContinueEditAction(photo_opts=self.photo_opts, current_app=self.current_app, new_obj=new_obj)

    def saver(self, *, obj: Submission, form: "SubmissionAdmin.AcceptForm", codename_add: str) -> "SaveRecord":
        if not self.admin.has_delete_permission(self.request, obj) or not self.user.has_perm('{}.archive.{}.{}'.format(self.photo_opts.app_label, obj.archive.slug, codename_add)) and not self.user.has_perm('{}.any.{}'.format(self.photo_opts.app_label, codename_add)):
            raise PermissionDenied
        else:
            return SaveRecord(obj=obj, form=form)

    def get_obj_responder(self, *, obj: Optional[Submission], form: "SubmissionAdmin.AcceptForm", codename_add: str) -> AdminCommunication:
        if not obj:
            return SubmissionAdmin.SubmissionDoesNotExist(opts=self.opts, object_id=self.object_id, current_app=self.current_app)
        else:
            return SubmissionAdmin.SubmissionExists(
                factory=LogFactory(base_factory=self, object_name=str(obj)),
                saver=self.saver(obj=obj, form=form, codename_add=codename_add)
            )

    def get_form_responder(self, *, model: Type[Model] = Submission) -> AdminCommunication:
        form = SubmissionAdmin.AcceptForm(self.request.POST)
        if not form.is_valid():
            return SubmissionAdmin.SubmissionFormInvalidResponse(app_label=self.opts.app_label, model_name=self.opts.model_name, object_id=self.object_id, current_app=self.current_app)
        else:
            return SubmissionAdmin.SubmissionFormValidResponse(admin=self.admin, request=self.request, model=model, factory=self, form=form, object_id=self.object_id, photo_opts=self.photo_opts)

@dataclass
class LogFactory:
    base_factory: AcceptanceFactory
    object_name: str

    def notify_action(self, *, new_obj: Photo) -> AdminCommunication:
        return SubmissionLogger(
            old_object_id=self.base_factory.object_id,
            new_obj=new_obj,
            user=self.base_factory.user,
            object_name=self.object_name,
            photo_opts=self.base_factory.photo_opts,
            factory=self.base_factory,
        )

@dataclass
class SubmissionLogger:
    old_object_id: int
    new_obj: Photo
    user: User
    object_name: str
    photo_opts: "Options[Photo]"
    factory: AcceptanceFactory

    old_model: Type[Model] = Submission
    new_model: Type[Model] = Photo

    def log(self) -> None:
        LogEntry.objects.log_action(
            user_id=self.user.id,
            content_type_id=ContentType.objects.get_for_model(self.old_model).id,
            object_repr=self.object_name,
            object_id=self.old_object_id,
            action_flag=DELETION,
            change_message='Submission accepted as <a href="{href}">{name}</a>.'.format(
                href=reverse("admin:{app_label}_{model_name}_change".format(
                    app_label=self.photo_opts.app_label,
                    model_name=self.photo_opts.model_name
                ), kwargs={"object_id": self.new_obj.id}),
                name=str(self.new_obj),
            )
        ) # type: ignore
        LogEntry.objects.log_action(
            user_id=self.user.id,
            content_type_id=ContentType.objects.get_for_model(self.new_model).id,
            object_repr=repr(self.new_obj),
            object_id=self.new_obj.id,
            action_flag=ADDITION,
            change_message='Created from Submission',
        ) # type: ignore

    @property
    def message_level(self) -> int:
        return self.action.message_level

    @property
    def message(self) -> str:
        return self.action.message

    @cached_property
    def action(self) -> AdminCommunication:
        self.log()
        return self.factory.notify_action(new_obj=self.new_obj)

    @property
    def response(self) -> HttpResponse:
        return self.action.response

@dataclass
class SaveRecord:
    obj: Submission
    form: "SubmissionAdmin.AcceptForm"

    @property
    def photo(self) -> Photo:
        file = ContentFile(self.obj.image.read())
        file.name = "submittedphoto"
        file.close()
        file.open()
        new_obj = Photo(
            category=self.obj.category,
            archive=self.obj.archive,
            donor=self.obj.donor,
            photographer=self.obj.photographer,
            address=self.obj.address,
            city=self.obj.city,
            county=self.obj.county,
            state=self.obj.state,
            country=self.obj.country,
            year=self.obj.year,
            circa=self.obj.circa,
            caption=self.obj.caption,
            scanner=self.obj.scanner,
            original=file,
            is_published=self.form.cleaned_data['is_published'],
            is_featured=self.form.cleaned_data['is_featured'],
        )
        new_obj.save()
        new_obj.terms.set(self.obj.terms.all())
        self.obj.image.delete(save=False)
        self.obj.delete()
        return new_obj

@admin.register(Submission)
class SubmissionAdmin(PhotoBaseAdmin):
    change_form_template = 'admin/custom_changeform.html'
    readonly_fields = ["image_display", "uploader"]
    form = SubmissionForm
    exclude = ('city', 'state', 'address', 'county', 'country')
    fields = [
        'archive',
        'category',
        'donor',
        'image',
        'year',
        'circa',
        'photographer',
        'terms',
        'place',
        'location_point',
        'caption',
        'scanner',
        'uploader',
    ]

    class Media:
        js = ('https://unpkg.com/htmx.org@1.9.6',)

    class AcceptForm(forms.ModelForm):
        class Meta:
            model = Photo
            fields = ['is_published', 'is_featured']

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.fields['is_published'].label_suffix = ''
            self.fields['is_featured'].label_suffix = ''

    def formfield_for_foreignkey(
        self, db_field: ForeignKey, request: HttpRequest, **kwargs: Any
    ) -> Optional[forms.ModelChoiceField]:
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'category':
            url = reverse('admin:kronofoto_photo_terms')
            if field:
                field.widget.attrs.update({
                    'data-category': '',
                })
        return field

    def get_urls(self) -> List[URLPattern]:
        from django.urls import path
        def wrap(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
            def wrapper(*args: Any, **kwargs: Any) -> HttpResponse:
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self # type: ignore
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name
        return [path("<int:object_id>/accept/", wrap(self.accept_view), name="{}_{}_accept".format(*info))] + super().get_urls()

    def accept_view(self, request: HttpRequest, object_id: int, form_url: str='', extra_context: Optional[Dict[Any, Any]]=None, *, factory_class: Type[AcceptanceFactory]=AcceptanceFactory) -> HttpResponse:
        assert not request.user.is_anonymous
        factory = factory_class(
            current_app=self.admin_site.name,
            request=request,
            object_id=object_id,
            admin=self,
            user=request.user,
        )
        extra_context = extra_context or {}
        model = self.model
        opts = model._meta
        obj_url = reverse("admin:{}_{}_change".format(opts.app_label, opts.model_name), args=[object_id], current_app=self.admin_site.name)
        if not request.method or request.method.lower() != 'post':
            return HttpResponseRedirect(obj_url)
        else:
            responder = factory.get_form_responder()
            self.message_user(request, responder.message, responder.message_level)
            return responder.response

    @dataclass
    class SubmissionFormInvalidResponse:
        app_label: str
        model_name: Optional[str]
        object_id: int
        current_app: str
        @property
        def message(self) -> str:
            return "The accept submission form was invalid."

        @property
        def message_level(self) -> int:
            return messages.ERROR

        @property
        def redirect_url(self) -> str:
            return reverse("admin:{}_{}_change".format(self.app_label, self.model_name), args=[self.object_id], current_app=self.current_app)

        @property
        def response(self) -> HttpResponse:
            return HttpResponseRedirect(self.redirect_url)

    @dataclass
    class SubmissionFormValidResponse:
        admin: admin.ModelAdmin
        model: Type[Model]
        request: HttpRequest
        object_id: int
        factory: AcceptanceFactory
        form: "SubmissionAdmin.AcceptForm"
        photo_opts: "Options[Photo]"

        @cached_property
        def responder(self) -> AdminCommunication:
            codename_add = get_permission_codename('add', self.photo_opts)
            with transaction.atomic(using=router.db_for_write(self.model)):
                obj: Optional[Submission] = self.admin.get_object(self.request, quote(str(self.object_id)))

                return self.factory.get_obj_responder(
                    obj=obj,
                    form=self.form,
                    codename_add=codename_add,
                )

        @property
        def message_level(self) -> int:
            return self.responder.message_level

        @property
        def message(self) -> str:
            return self.responder.message

        @property
        def response(self) -> HttpResponse:
            return self.responder.response

    @dataclass
    class SubmissionDoesNotExist:
        opts: "Options[Submission]"
        object_id: int
        current_app: str
        @property
        def message_level(self) -> int:
            return messages.WARNING

        @property
        def message(self) -> str:
            return '{name} with ID “{key}” doesn’t exist. Perhaps it was deleted?'.format(
                name=self.opts.verbose_name,
                key=self.object_id,
            )

        @property
        def redirect_url(self) -> str:
            return reverse('admin:index', current_app=self.current_app)

        @property
        def response(self) -> HttpResponse:
            return HttpResponseRedirect(self.redirect_url)

    @dataclass
    class SubmissionExists:
        saver: SaveRecord
        factory: NotifyFactory

        @property
        def message_level(self) -> int:
            return self.action.message_level

        @property
        def message(self) -> str:
            return self.action.message

        @cached_property
        def action(self) -> AdminCommunication:
            new_obj = self.saver.photo
            return self.factory.notify_action(new_obj=new_obj)

        @property
        def response(self) -> HttpResponse:
            return self.action.response


    @dataclass
    class SaveAction:
        photo_opts: "Options[Photo]"
        current_app: str
        new_obj: Photo

        @property
        def message_level(self) -> int:
            return messages.SUCCESS

        @property
        def new_obj_url(self) -> str:
            return reverse("admin:{}_{}_change".format(self.photo_opts.app_label, self.photo_opts.model_name), args=[self.new_obj.pk], current_app=self.current_app)

        @property
        def message(self) -> str:
            msg_list = [self.photo_opts.verbose_name, format_html('<a href="{}">{}</a>', self.new_obj_url, str(self.new_obj))]
            return format_html(self.saved_message_format, *msg_list)

        @property
        def response(self) -> HttpResponse:
            return HttpResponseRedirect(self.redirect_url)

        @property
        def saved_message_format(self) -> str:
            raise NotImplementedError

        @property
        def redirect_url(self) -> str:
            raise NotImplementedError

    @dataclass
    class AcceptAction(SaveAction):
        app_label: str
        model_name: Optional[str]
        @property
        def saved_message_format(self) -> str:
            return 'The {} "{}" was accepted successfully. You may accept or edit other submissions below'

        @property
        def redirect_url(self) -> str:
            return reverse("admin:{}_{}_changelist".format(self.app_label, self.model_name), current_app=self.current_app)

    @dataclass
    class ContinueEditAction(SaveAction):
        @property
        def saved_message_format(self) -> str:
            return 'The {} "{}" was accepted successfully. You may edit it below.'

        @property
        def redirect_url(self) -> str:
            return self.new_obj_url

    def change_view(self, request: HttpRequest, object_id: str, form_url: str='', extra_context: Optional[Dict[Any, Any]]=None) -> HttpResponse:
        obj: Optional[Submission] = self.get_object(request, object_id)
        user = request.user
        assert not user.is_anonymous
        target_model = Photo
        photo_opts = target_model._meta
        codename_add = get_permission_codename('add', photo_opts)
        extra_context = extra_context or {}
        extra_context['accept_form'] = self.AcceptForm({"is_published": True})
        if obj:
            extra_context['can_accept_submission'] = (
                self.has_delete_permission(request, obj) and
                (
                    user.has_perm('{}.archive.{}.{}'.format(photo_opts.app_label, obj.archive.slug, codename_add)) or
                    user.has_perm('{}.any.{}'.format(photo_opts.app_label, codename_add))
                )
            )
        return super().change_view(request, object_id, form_url, extra_context)
    #def response_change(self, request, obj: Submission):
    #    if '_accept_submission' in request.POST:
    #        pass
    #    else:
    #        return super().response_change(request, obj)

    def image_display(self, obj: Submission) -> str:
        return mark_safe('<img src="{}" width="{}" height="{}" />'.format(obj.image.url, obj.image.width, obj.image.height))


@admin.register(Photo)
class PhotoAdmin(PhotoBaseAdmin):
    readonly_fields = ['county', 'state', 'city', 'country', "h700_image"]
    inlines = (TagInline,)
    list_filter = (TermFilter, TagFilter, YearIsSetFilter, IsPublishedFilter, HasGeoLocationFilter, HasLocationFilter, HasPlaceFilter)
    list_display = ('thumb_image', 'accession_number', 'donor', 'year', 'caption')
    actions = [publish_photos, unpublish_photos]
    form = PhotoForm
    search_fields = [
        'donor__last_name',
        'donor__first_name',
        'caption',
        'year',
        'place__fullname',
    ]

    fields = [
        'archive',
        'category',
        'donor',
        'original',
        'h700_image',
        'year',
        'circa',
        'photographer',
        'terms',
        'place',
        'location_point',
        'address',
        'city',
        'county',
        'state',
        'country',
        'caption',
        'is_featured',
        'is_published',
        'local_context_id',
        'scanner',
    ]
    class Media:
        js = ('https://unpkg.com/htmx.org@1.9.6',)

    def thumb_image(self, obj: Photo) -> str:
        thumbnail = obj.thumbnail
        if thumbnail:
            return mark_safe('<img src="{}" width="{}" height="{}" />'.format(thumbnail.url, thumbnail.width, thumbnail.height))
        else:
            return ""

    def h700_image(self, obj: Photo) -> str:
        h700 = obj.h700
        if h700:
            return mark_safe('<img src="{}" width="{}" height="{}" />'.format(h700.url, h700.width, h700.height))
        else:
            return "-"

    def get_urls(self) -> List[URLPattern]:
        from django.urls import path
        def wrap(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
            def wrapper(*args: Any, **kwargs: Any) -> HttpResponse:
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self # type: ignore
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path("terms", wrap(self.terms_view), name="{}_{}_terms".format(*info)),
        ] + super().get_urls()

    def terms_view(self, request: HttpRequest) -> HttpResponse:
        if request.GET.get('archive', "") and request.GET.get("category", ""):
            vc = get_object_or_404(
                ValidCategory.objects.all(),
                archive__id=int(request.GET['archive']),
                category__id=int(request.GET['category']),
            )
            terms = vc.terms.all()
        else:
            terms = Term.objects.none()
        return TemplateResponse(request, "admin/widgets/terms.html", {'objects': terms })


    def formfield_for_foreignkey(
        self, db_field: ForeignKey, request: HttpRequest, **kwargs: Any
    ) -> Optional[forms.ModelChoiceField]:
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'category':
            url = reverse('admin:kronofoto_photo_terms')
            if field:
                field.widget.attrs.update({
                    'hx-get': url,
                    'hx-trigger': 'change',
                    'data-category': '',
                    'hx-include': '[data-archive]',
                    'hx-target': '[data-terms]',
                })
        return field

    def formfield_for_manytomany(self, db_field: ManyToManyField, request: HttpRequest, **kwargs: Any) -> Optional[forms.ModelMultipleChoiceField]:
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == 'terms' and field:
            field.widget.attrs.update({
                'data-terms': '',
            })
        return field

class UserTagInline(admin.TabularInline):
    model = PhotoTag.creator.through
    extra = 0
    fields = ['thumb_image', 'tag', 'accepted']
    readonly_fields = ['thumb_image', 'tag', 'accepted']
    can_delete = False

    def thumb_image(self, instance: Any) -> str:
        return mark_safe(
            '<a href="{edit_url}"><img src="{thumb}" width="{width}" height="{height}" /></a>'.format(
                edit_url=reverse('admin:kronofoto_photo_change', args=(instance.phototag.photo.id,)),
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
            supported_permissions = Q(content_type__app_label='kronofoto') & combined
            kwargs['queryset'] = Permission.objects.filter(supported_permissions)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

class GroupArchivePermissionsInline(base_admin.TabularInline):
    model = Archive.groups.through
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
            supported_permissions = Q(content_type__app_label='kronofoto') & combined
            kwargs['queryset'] = Permission.objects.filter(supported_permissions)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

class WithArchiveId(TypedDict):
    archive_id: int
class PermissionAnalyst:
    def __init__(self, user: User) -> None:
        self.user = user
    def get_archive_permissions(self) -> DefaultDict[int, Set[Any]]:
        sets = defaultdict(set)
        objects : Any = (Permission.objects
            .filter(archiveuserpermission__user__id=self.user.id)
            .annotate(archive_id=F('archiveuserpermission__archive__id'))
        )
        for obj in objects:
            sets[obj.archive_id].add(obj)
        for obj in Archive.groups.through.objects.filter(group__user__id=self.user.id):
            for permission in obj.permission.all():
                sets[obj.archive.id].add(permission)
        #objects = (Permission.objects
        #    .filter(archivegrouppermission__group__user__id=self.user.id)
        #    .annotate(archive_id=F('group__archivegrouppermission__archive__id'))
        #)
        #for obj in objects:
        #    sets[obj.archive_id].add(obj)
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
        user_group_perms = Q(pk=self.user.id) & (Q(user_permissions=OuterRef('pk')) | Q(groups__permissions=OuterRef('pk')))
        missing = Exists(Permission.objects.exclude(Exists(User.objects.filter(user_group_perms))).filter(group=OuterRef('pk')))
        # Exclude groups which have at least one match.
        groups = Group.objects.exclude(missing)

        # For a group to be valid, user must have the same permissions, and every GAP associated with it must be valid.
        # GAP is valid if the UAPs grant the same Permission and Archive pairs,
        # or if the user directly has the permission, or if the user has permission through groups.
        gap_q = Q(pk=self.user.id) & (Q(archiveuserpermission__permission=OuterRef('permission__pk'), archiveuserpermission__archive__slug=OuterRef('archive__slug')) | Q(groups__archivegrouppermission__permission=OuterRef('permission__pk'), groups__archivegrouppermission__archive__slug=OuterRef("archive__slug")))

        from fortepan_us.kronofoto.models.archive import ArchiveGroupPermission
        invalid_gaps = ArchiveGroupPermission.objects.exclude(Exists(User.objects.filter(gap_q)))
        return groups.exclude(Exists(invalid_gaps.filter(group=OuterRef('pk'))))

class GroupAnalyst:
    def __init__(self, group: Group) -> None:
        self.group = group

    def get_archive_permissions(self) -> DefaultDict[int, Set[Any]]:
        sets = defaultdict(set)
        objects = (Permission.objects
            .filter(archivegrouppermission__group__id=self.group.id)
            .annotate(archive_id=F('archivegrouppermission__archive__id'))
        )
        for obj in objects:
            sets[obj.archive_id].add(obj)
        return sets

@dataclass
class UserData:
    user: User
    user_analyst: PermissionAnalyst

@dataclass
class GroupData:
    group: Group
    group_analyst: GroupAnalyst

@dataclass
class EscalationBlocker:
    editor: PermissionAnalyst
    target_data: Union[UserData, GroupData]

    def __enter__(self) -> None:
        if isinstance(self.target_data, UserData):
            archive_manager = self.target_data.user.archiveuserpermission_set
            analyst : Union[PermissionAnalyst, GroupAnalyst] = self.target_data.user_analyst
            perm_manager = self.target_data.user.user_permissions
            self.old_groups = set(self.target_data.user.groups.all())
            self.changeable_groups = set(self.editor.get_changeable_groups())
        elif isinstance(self.target_data, GroupData):
            archive_manager = self.target_data.group.archivegrouppermission_set # type: ignore
            analyst = self.target_data.group_analyst
            perm_manager = self.target_data.group.permissions # type: ignore

        self.old_archives = set(aup.archive for aup in archive_manager.all())
        self.old_archive_permissions = analyst.get_archive_permissions()
        self.old_perms = set(perm_manager.all())
        self.changeable_archive_permissions = self.editor.get_archive_permissions()
        self.changeable_perms = set(self.editor.get_changeable_permissions())

    def create_archive_relation(self, *, archive: Archive, target_data: Union[UserData, GroupData]) -> Union[ArchiveUserPermission, ArchiveGroupPermission]:
        if isinstance(target_data, UserData):
            return Archive.users.through.objects.create(archive=archive, user=target_data.user)
        return Archive.groups.through.objects.create(archive=archive, group=target_data.group)

    def get_archive_relation(self, *, archive: Archive, target_data: Union[UserData, GroupData]) -> Union[ArchiveUserPermission, ArchiveGroupPermission]:
        if isinstance(target_data, UserData):
            return target_data.user.archiveuserpermission_set.get(archive__id=archive.id)
        assert hasattr(target_data.group, "archivegrouppermission_set")
        return target_data.group.archivegrouppermission_set.get(archive__id=archive.id)

    def get_assigned_archive_permissions(self, *, target_data: Union[UserData, GroupData]) -> Dict[int, Set[Any]]:
        if isinstance(target_data, UserData):
            return target_data.user_analyst.get_archive_permissions()
        else:
            return target_data.group_analyst.get_archive_permissions()

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        if isinstance(self.target_data, UserData):
            new_perms = set(self.target_data.user.user_permissions.all())
            new_groups = set(self.target_data.user.groups.all())
            self.target_data.user.user_permissions.set((self.old_perms - self.changeable_perms) | (self.changeable_perms & new_perms))
            self.target_data.user.groups.set((self.old_groups - self.changeable_groups) | (self.changeable_groups & new_groups))

            new_archives = set(aup.archive for aup in self.target_data.user.archiveuserpermission_set.all())
            new_archive_permissions = self.get_assigned_archive_permissions(target_data=self.target_data)
            changed_archive_perms = self.old_archives | new_archives
            for related in changed_archive_perms:
                assign = (self.old_archive_permissions[related.id] - (self.changeable_archive_permissions[related.id] | self.changeable_perms)) | ((self.changeable_archive_permissions[related.id] | self.changeable_perms) & new_archive_permissions[related.id]) # type: ignore
                try:
                    obj : Union[ArchiveUserPermission, ArchiveGroupPermission] = self.get_archive_relation(archive=related, target_data=self.target_data)
                    if len(assign) == 0:
                        obj.delete()
                    else:
                        obj.permission.set(assign)
                except ObjectDoesNotExist:
                    if assign:
                        obj = self.create_archive_relation(archive=related, target_data=self.target_data)
                        obj.permission.set(assign)
        elif isinstance(self.target_data, GroupData):
            new_perms = set(self.target_data.group.permissions.all())
            self.target_data.group.permissions.set((self.old_perms - self.changeable_perms) | (self.changeable_perms & new_perms))
            new_archives = set(agp.archive for agp in self.target_data.group.archivegrouppermission_set.all()) # type: ignore

            new_archive_permissions = self.get_assigned_archive_permissions(target_data=self.target_data)
            changed_archive_perms = self.old_archives | new_archives
            for related in changed_archive_perms:
                assign = (self.old_archive_permissions[related.id] - (self.changeable_archive_permissions[related.id] | self.changeable_perms)) | ((self.changeable_archive_permissions[related.id] | self.changeable_perms) & new_archive_permissions[related.id]) # type: ignore
                try:
                    obj = self.get_archive_relation(archive=related, target_data=self.target_data)
                    if len(assign) == 0:
                        obj.delete()
                    else:
                        obj.permission.set(assign)
                except ObjectDoesNotExist:
                    if assign:
                        obj = self.create_archive_relation(archive=related, target_data=self.target_data)
                        obj.permission.set(assign)


def block_escalation(*, editor: User, user: User, PAClass: Type[PermissionAnalyst]=PermissionAnalyst) -> ContextManager:
    ua = PAClass(user)
    ud = UserData(user=user, user_analyst=ua)
    return EscalationBlocker(editor=PAClass(editor), target_data=ud)

def block_group_escalation(*, editor: User, group: Group, PAClass: Type[PermissionAnalyst]=PermissionAnalyst, GAClass: Type[GroupAnalyst]=GroupAnalyst) -> ContextManager:
    ga = GAClass(group)
    gd = GroupData(group=group, group_analyst=ga)
    return EscalationBlocker(editor=PAClass(editor), target_data=gd)

class KronofotoUserAdmin(UserAdmin):
    inlines = (UserArchivePermissionsInline,)
    readonly_fields = ['tagging_history']
    fieldsets = tuple(list(UserAdmin.fieldsets) + [("Other", {"fields": ('tagging_history',)})]) # type: ignore
    def thumbnail_url(self, photo: Photo) -> str:
        thumb = photo.thumbnail
        if thumb:
            return thumb.url
        else:
            return ""

    def tagging_history(self, obj: User) -> str:
        table = format_html_join(
            '',
            '<tr><td><a href="{}"><img src="{}" width="75" height="75"></a></td><td>{}</td><td>{}</td></tr>',
            (
                (
                    reverse('admin:kronofoto_photo_change',
                        args=(tag.photo.id,)),
                    self.thumbnail_url(tag.photo),
                    tag.tag, "Yes" if tag.accepted else "No",
                )
                for tag in PhotoTag.objects.filter(creator=obj).select_related('photo', 'tag')
            ),
        )
        return format_html("<table><thead><tr><td>Photo</td><td>Tag</td><td>Accepted?</td></tr><tbody>{}</tbody></table>", table)

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
    inlines = (GroupArchivePermissionsInline,)

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
        "description",
        "view",
    ]

    def view(self, object: LogEntry) -> Optional[str]:
        if object.action_flag != DELETION and ContentType.objects.get_for_model(Photo).id == object.content_type_id:
            return mark_safe('<a href="{}">View</a>'.format(
                reverse(
                    "admin:{}_{}_change".format(Photo._meta.app_label, Photo._meta.model_name),
                    kwargs={"object_id": object.object_id},
                )
            ))
        else:
            return None

    def description(self, object: LogEntry) -> str:
        if ContentType.objects.get_for_model(Submission).id == object.content_type_id:
            return mark_safe(object.change_message)
        else:
            return object.get_change_message()

    def has_add_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def has_change_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def has_delete_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def has_view_permission(self, request: HttpRequest, *args: Any, **kwargs: Any) -> bool:
        return request.user.is_superuser
