from fortepan_us.settings.urls import *

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))
