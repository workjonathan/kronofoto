from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Photo, Tag, Term, PhotoTag
from django.conf import settings

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    pass


class TagInline(admin.TabularInline):
    model = PhotoTag
    extra = 1


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    readonly_fields = ["h700_image"]
    inlines = (TagInline,)
    list_filter = ('phototag__accepted',)
    list_display = ('thumb_image',)
    list_display = ('thumb_image', 'accession_number', 'year', 'caption')

    def thumb_image(self, obj):
        return mark_safe('<img src="{}" width="{}" height={} />'.format(settings.STATIC_URL + obj.thumbnail.url, obj.thumbnail.width, obj.thumbnail.height))

    def h700_image(self, obj):
        return mark_safe('<img src="{}" width="{}" height={} />'.format(settings.STATIC_URL + obj.h700.url, obj.h700.width, obj.h700.height))

