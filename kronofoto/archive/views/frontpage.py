from django.http import HttpResponse
from django.views.generic.base import RedirectView
from django.views.generic.list import MultipleObjectMixin
from .basetemplate import BaseTemplateMixin
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..forms import SearchForm
from ..search.parser import NoExpression


class PhotoRedirectView(BaseTemplateMixin, MultipleObjectMixin, RedirectView):
    permanent = False
    pattern_name = 'photoview'
    model = Photo

    def get_object(self):
        qs = self.get_queryset().order_by(self.get_ordering())
        return qs[0]

    def get_queryset(self):
        qs = self.model.objects.filter_photos(
            CollectionQuery(self.final_expr, self.request.user)
        )
        if 'short_name' in self.kwargs:
            qs = qs.filter(archive__slug=self.kwargs['short_name'])
        return qs

    def options(self, request, *args, **kwargs):
        if 'embedded' in request.headers.get('Access-Control-Request-Headers', '').split(','):
            response = HttpResponse()
            return response
        else:
            return super().options(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        return self.get_object().get_absolute_url(kwargs=self.url_kwargs, params=self.request.GET)


class RandomRedirect(PhotoRedirectView):
    ordering = "?"


class YearRedirect(PhotoRedirectView):
    ordering = ('year', 'id')
    def get_object(self):
        qs = self.get_queryset().filter(year__gte=self.kwargs['year']).order_by(*self.ordering)
        return qs[0]
