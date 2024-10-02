from django.views.generic import TemplateView
from .basetemplate import BaseTemplateMixin
from fortepan_us.kronofoto.models.photo import Photo
from fortepan_us.kronofoto.models.term import Term
from fortepan_us.kronofoto.models.tag import Tag
from fortepan_us.kronofoto.models.donor import Donor
from typing import Any, Dict


class DirectoryView(BaseTemplateMixin, TemplateView):
    template_name = 'kronofoto/pages/directory.html'
    subdirectories = [
        {'name': 'Terms', 'indexer': Term},
        {'name': 'Tags', 'indexer': Tag},
        {'name': 'Donors', 'indexer': Donor},
        {'name': 'Cities', 'indexer': Photo.CityIndexer()},
        {'name': 'Counties', 'indexer': Photo.CountyIndexer()},
    ]

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        context['subdirectories'] = self.subdirectories
        return context
