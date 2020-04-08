from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Photo, Tag, Term, PhotoTag
from django.conf import settings

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    pass

@admin.register(PhotoTag)
class PhotoTagAdmin(admin.ModelAdmin):
    pass

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    readonly_fields = ["h700_image"]

    def h700_image(self, obj):
        return mark_safe('<img src="{}" width="{}" height={} />'.format(settings.STATIC_URL + obj.h700.url, obj.h700.width, obj.h700.height))

