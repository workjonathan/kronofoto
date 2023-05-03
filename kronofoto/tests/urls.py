from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('archive.auth.urls')),
    path('', include('archive.urls', namespace="kronofoto")),
]

