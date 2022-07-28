from django.views.generic import TemplateView
from .basetemplate import BaseTemplateMixin
from ..models.photo import Photo
from ..models.term import Term
from ..models.tag import Tag
from ..models.donor import Donor


class DirectoryView(BaseTemplateMixin, TemplateView):
    template_name = 'archive/directory.html'
    subdirectories = [
        {'name': 'Terms', 'indexer': Term},
        {'name': 'Tags', 'indexer': Tag},
        {'name': 'Donors', 'indexer': Donor},
        {'name': 'Cities', 'indexer': Photo.CityIndexer()},
        {'name': 'Counties', 'indexer': Photo.CountyIndexer()},
    ]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['subdirectories'] = self.subdirectories
        return context
