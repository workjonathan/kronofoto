from django.views.generic.base import RedirectView
from .basetemplate import BaseTemplateMixin
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..forms import SearchForm
from ..search.parser import NoExpression


class FrontPage(BaseTemplateMixin, RedirectView):
    permanent = False
    pattern_name = 'photoview'

    def get_redirect_url(self, *args, **kwargs):
        photo = Photo.objects.filter_photos(
            CollectionQuery(self.final_expr, self.request.user)
        ).order_by('?')[0]
        return photo.get_absolute_url()


