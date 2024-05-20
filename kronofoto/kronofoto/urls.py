from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('archive.auth.urls')),
    path('', include('archive.urls', namespace="kronofoto")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))


if settings.KF_DJANGOCMS_SUPPORT:
    urlpatterns += [
        path('docs/', include("cms.urls")),
    ]
