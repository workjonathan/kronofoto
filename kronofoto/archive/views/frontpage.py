from django.http import HttpResponse
from django.views.generic.base import RedirectView
from .basetemplate import BaseTemplateMixin
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..forms import SearchForm
from ..search.parser import NoExpression


class FrontPage(BaseTemplateMixin, RedirectView):
    permanent = False
    pattern_name = 'photoview'

    def options(self, request, *args, **kwargs):
        if 'embedded' in request.headers.get('Access-Control-Request-Headers', '').split(','):
            response = HttpResponse()
            return response
        else:
            return super().options(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        photos = Photo.objects.filter_photos(
            CollectionQuery(self.final_expr, self.request.user)
        )
        return photos.order_by('?')[0].get_absolute_url(queryset=photos)


