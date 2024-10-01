from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('fortepan_us.kronofoto.auth.urls')),
    path('docs/', include("cms.urls")),
    path('', include('fortepan_us.kronofoto.urls', namespace="kronofoto")),
]
