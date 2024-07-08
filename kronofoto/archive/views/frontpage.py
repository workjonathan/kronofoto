from django.http import HttpResponse, QueryDict, HttpRequest, HttpResponseBase
from django.views.generic.base import RedirectView
from django.views.generic.list import MultipleObjectMixin
from .basetemplate import BasePhotoTemplateMixin
from ..models.photo import Photo
from ..forms import SearchForm, TimelineForm
from ..search.parser import NoExpression
from django.core.exceptions import BadRequest
from django.http import Http404
from typing import Any, Dict, List, Optional, Union


class PhotoRedirectView(BasePhotoTemplateMixin, MultipleObjectMixin, RedirectView):
    permanent = False
    pattern_name = 'photoview'
    model = Photo

    def _get_params(self) -> QueryDict:
        return self.request.GET

    def get_object(self) -> Photo:
        qs = self.get_queryset().order_by(self.get_ordering())
        if not qs.exists():
            raise Http404("no objects found")
        return qs[0]

    def options(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if 'embedded' in request.headers.get('Access-Control-Request-Headers', '').split(','):
            response = HttpResponse()
            return response
        else:
            return super().options(request, *args, **kwargs)

    def get_redirect_url(self, *args: Any, **kwargs: Any) -> str:
        return self.get_object().get_absolute_url(kwargs=self.url_kwargs, params=self._get_params())


class RandomRedirect(PhotoRedirectView):
    ordering = "?"


class YearRedirect(PhotoRedirectView):
    ordering = ('year', 'id')

    def _get_params(self) -> QueryDict:
        params = self.request.GET.copy()
        while 'year' in params:
            params.pop('year')
        for k, l in list(params.lists()):
            if not any(l):
                params.pop(k)
        return params

    def get_object(self) -> Photo:
        if 'year' in self.kwargs:
            year = self.kwargs['year']
        else:
            form = TimelineForm(self.request.GET)
            if form.is_valid():
                year = form.cleaned_data['year']
            else:
                raise BadRequest('Invalid request')
        qs = self.get_queryset().filter(year__gte=year).order_by(*self.ordering)
        if not qs.exists():
            raise Http404("no objects found")
        return qs[0]
