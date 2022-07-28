from django.views.generic.detail import DetailView
from django.conf import settings
from .basetemplate import BaseTemplateMixin
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery


class DownloadPageView(BaseTemplateMixin, DetailView):
    model = Photo
    template_name = "archive/download-page.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['host_uri'] = settings.HOST_URI
        photo = context['object']
        collection = CollectionQuery(self.final_expr, self.request.user)
        context['citation_url'] = photo.get_absolute_url(params=None)
        photo.save_params(self.request.GET)
        photo.row_number = self.model.objects.filter_photos(collection).photo_position(photo)
        context['grid_url'] = photo.get_grid_url()
        return context
