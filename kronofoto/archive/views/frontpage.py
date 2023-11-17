from django.http import HttpResponse
from django.views.generic.base import RedirectView
from django.views.generic.list import MultipleObjectMixin
from .basetemplate import BasePhotoTemplateMixin
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..forms import SearchForm, TimelineForm
from ..search.parser import NoExpression
from django.core.exceptions import SuspiciousOperation
from django.http import Http404


class PhotoRedirectView(BasePhotoTemplateMixin, MultipleObjectMixin, RedirectView):
    permanent = False
    pattern_name = 'photoview'
    model = Photo

    def _get_params(self):
        return self.request.GET

    def get_object(self):
        qs = self.get_queryset().order_by(self.get_ordering())
        if not qs.exists():
            raise Http404("no objects found")
        return qs[0]

    def options(self, request, *args, **kwargs):
        if 'embedded' in request.headers.get('Access-Control-Request-Headers', '').split(','):
            response = HttpResponse()
            return response
        else:
            return super().options(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        return self.get_object().get_absolute_url(kwargs=self.url_kwargs, params=self._get_params())


class RandomRedirect(PhotoRedirectView):
    ordering = "?"


class YearRedirect(PhotoRedirectView):
    ordering = ('year', 'id')

    def _get_params(self):
        params = self.request.GET.copy()
        while 'year' in params:
            params.pop('year')
        for k, l in list(params.lists()):
            if not any(l):
                params.pop(k)
        return params

    def get_object(self):
        if 'year' in self.kwargs:
            year = self.kwargs['year']
        else:
            form = TimelineForm(self.request.GET)
            if form.is_valid():
                year = form.cleaned_data['year']
            else:
                raise SuspiciousOperation('Invalid request')
        qs = self.get_queryset().filter(year__gte=year).order_by(*self.ordering)
        if not qs.exists():
            raise Http404("no objects found")
        return qs[0]
