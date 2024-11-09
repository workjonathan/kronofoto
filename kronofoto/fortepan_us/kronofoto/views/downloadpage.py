from django.views.generic.detail import DetailView
from django.conf import settings
from .basetemplate import BaseTemplateMixin
from fortepan_us.kronofoto.models.photo import Photo
from .base import require_valid_archive, ArchiveRequest
from typing import Any, List, Dict, Union, Optional


class BaseDownloadView(DetailView):
    model = Photo
    pk_url_kwarg = 'photo'

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)

        archive_request = ArchiveRequest(request=self.request, short_name=self.kwargs.get('short_name'), category=self.kwargs.get('category'))
        context.update(archive_request.common_context)
        photo = context['object']
        context['grid_url'] = photo.get_grid_url()
        return context


class DownloadPageView(BaseDownloadView):
    template_name = "kronofoto/pages/download.html"


class DownloadPopupView(BaseDownloadView):
    template_name = "kronofoto/components/popups/download.html"
