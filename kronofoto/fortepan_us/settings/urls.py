from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from fortepan_us.kronofoto.sitemap import PhotoSiteMap, TagSiteMap, TermSiteMap, DonorSiteMap
from django.views.decorators.cache import cache_page


urlpatterns = [
    path(r'robots.txt', include('robots.urls')),
    path('admin/', admin.site.urls),
    path('sitemap.xml', cache_page(timeout=6*60*60)(sitemap), {"sitemaps": {"photos": PhotoSiteMap, "tags": TagSiteMap, "terms": TermSiteMap, "donors": DonorSiteMap}}, name="django.contrib.sitemaps.views.sitemap",),
    path('accounts/', include('fortepan_us.kronofoto.auth.urls')),
    path('docs/', include("cms.urls")),
    path('', include('fortepan_us.kronofoto.urls', namespace="kronofoto")),
]
