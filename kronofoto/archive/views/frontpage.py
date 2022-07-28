from django.views.generic.base import RedirectView
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..forms import SearchForm
from ..search.parser import NoExpression


class FrontPage(RedirectView):
    permanent = False
    pattern_name = 'photoview'

    def get_redirect_url(self, *args, **kwargs):
        form = SearchForm(self.request.GET)
        expr = None
        if form.is_valid():
            try:
                expr = form.as_expression()
            except NoExpression:
                pass
        photo = Photo.objects.filter_photos(
            CollectionQuery(expr, self.request.user)
        ).order_by('?')[0]
        return photo.get_absolute_url()


