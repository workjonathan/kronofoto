from django.views.generic.detail import DetailView
from django.conf import settings
from .basetemplate import BaseTemplateMixin
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery


class BaseDownloadView(DetailView):
    model = Photo
    pk_url_kwarg = 'photo'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        photo = context['object']
        context['citation_url'] = photo.get_absolute_url(params=None)
        context['grid_url'] = photo.get_grid_url()
        return context


class DownloadPageView(BaseDownloadView):
    template_name = "archive/download-page.html"


class DownloadPopupView(BaseDownloadView):
    template_name = "archive/popup-download.html"
