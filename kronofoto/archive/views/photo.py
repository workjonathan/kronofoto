from django.views.generic import DetailView, ListView, View
from django.views.generic.list import MultipleObjectMixin
from django.http import Http404, HttpResponse, HttpRequest, HttpResponseBase
from ..reverse import reverse
from django.shortcuts import redirect, get_object_or_404
from django.core.cache import cache
from django.conf import settings
from django.views.generic.base import RedirectView, TemplateView
from django.template.loader import render_to_string
from .basetemplate import BasePhotoTemplateMixin
from .paginator import Paginator, EMPTY_PNG
from django.db.models import QuerySet
from ..models.photo import Photo, PhotoQuerySet, BackwardList, ForwardList
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.csrf import csrf_exempt
from .base import PhotoRequest
from typing import final, TypedDict
from .basetemplate import Theme
from ..forms import CarouselForm
import random
from itertools import cycle, chain, islice
from dataclasses import dataclass
import json
from django.utils.cache import patch_vary_headers
from django.utils.decorators import method_decorator
from typing import Any, Optional, Dict, List

class OrderedDetailBase(DetailView):
    pk_url_kwarg = 'photo'
    @property
    def item_count(self) -> int:
        raise NotImplementedError


    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset().only('id', 'year', 'original')
        if not isinstance(queryset, PhotoQuerySet):
            raise ValueError
        object = self.object
        object.active = True

        before_chained = BackwardList(queryset=queryset, year=object.year, id=object.id).carousel_list(item_count=self.item_count)
        context['prev_photo'] = before_chained[0]

        after_chained = ForwardList(queryset=queryset, year=object.year, id=object.id).carousel_list(item_count=self.item_count)
        context['next_photo'] = after_chained[0]

        before_chained.reverse()
        carousel = before_chained + [object] + after_chained
        context['object_list'] = carousel

        context['queryset'] = queryset

        return context

class CarouselListView(BasePhotoTemplateMixin, MultipleObjectMixin, TemplateView):
    item_count = 40
    pk_url_kwarg = 'photo'
    model = Photo
    template_name = "archive/thumbnails.html"
    form_class = CarouselForm

    def get_form(self) -> CarouselForm:
        return self.form_class(self.request.GET)

    def form_valid(self, form: CarouselForm) -> HttpResponse:
        queryset = self.object_list = self.get_queryset().only('id', 'year', 'original')
        object = get_object_or_404(self.model, pk=form.cleaned_data['id'])
        offset = form.cleaned_data['offset']
        assert object.year
        if form.cleaned_data['forward']:
            objects = ForwardList(queryset=queryset, year=object.year, id=object.id).carousel_list(item_count=self.item_count)
        else:
            objects = BackwardList(queryset=queryset, year=object.year, id=object.id).carousel_list(item_count=self.item_count)
            objects.reverse()
            offset -= form.cleaned_data['width'] * (1 + self.item_count)
        context = {
            'object_list': objects,
            'positioning': {
                'width': form.cleaned_data['width'],
                'offset': offset,
            },
        }
        return self.render_to_response(context)

    def form_invalid(self, form: CarouselForm) -> HttpResponse:
        return HttpResponse("", status=400)

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)



class PhotoView(BasePhotoTemplateMixin, OrderedDetailBase):
    item_count = 20
    pk_url_kwarg = 'photo'
    model = Photo
    archive_request_class = PhotoRequest


    def get_object(self, queryset: Optional[QuerySet]=None) -> Photo:
        if not queryset:
            queryset = self.get_queryset()
            assert queryset
        try:
            return queryset.get(id=self.kwargs['photo'])
        except queryset.model.DoesNotExist:
            raise Http404("No photo with this accession number is in this collection.")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super(PhotoView, self).get_context_data(**kwargs)
        object = self.object
        queryset = self.get_queryset()
        year_range = queryset.year_range()
        start = year_range['start']
        end = year_range['end']

        context['grid_url'] = object.get_grid_url()
        context['timeline_url'] = object.get_absolute_url()
        context["photo"] = object
        return context

    def render(self, context: Dict[str, Any], **kwargs: Any) -> HttpResponse:
        response = super().render_to_response(context, **kwargs)
        patch_vary_headers(response, ('hx-target',))
        return response

    def render_to_response(self, context: Dict[str, Any], **kwargs: Any) -> HttpResponse:
        return self.render(context, **kwargs)

class TimelineSvg(TemplateView):
    template_name = "archive/timeline.svg"
    def get_context_data(self, start: Any, end: Any, short_name: Optional[str]=None, width: int=400, category: Optional[str]=None) -> Dict[str, Any]: # type: ignore
        url_kwargs = {}
        if category:
            url_kwargs['category'] = category
        if short_name:
            url_kwargs['short_name'] = short_name
        context : Dict[str, Any] = {
            'minornotches': [],
            'majornotches': [],
            'viewBox': [0, 0, width, 10],
            'view': self,
        }
        years = end-start+1
        for i, year in enumerate(range(start, end+1)):
            xpos = i*width/years
            boxwidth = width/years
            marker : Dict[str, Any] = {
                'target': "{}?{}".format(reverse('kronofoto:year-redirect', kwargs=dict(**url_kwargs, **dict(year=year))), self.request.GET.urlencode()),
                'data_year': str(year),
                'box': {
                    'x': xpos,
                    'width': boxwidth,
                    'y': 5,
                    'height': 5,
                },
                'notch': {
                    'x': xpos,
                    'width': boxwidth/5,
                    'y': 7,
                    'height': 3,
                }
            }
            if year % 5 == 0:
                marker['notch']['height'] = 5
                marker['notch']['y'] = 5
            if year % 10 == 0:
                marker['notch']['height'] = 5
                marker['notch']['y'] = 5
                marker['label'] = {
                    'text': str(year),
                    'y': 3,
                    'x': xpos + boxwidth/2,
                }
                context['majornotches'].append(marker)
            else:
                context['minornotches'].append(marker)
        return context

    def options(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        response = super().options(*args, **kwargs)
        response['Access-Control-Allow-Headers'] = 'constraint, embedded, hx-current-url, hx-request, hx-target, hx-trigger'
        return response

    @method_decorator(cache_control(max_age=60*60, public=True))
    def dispatch(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        response = super().dispatch(*args, **kwargs)
        response['Vary'] = 'Constraint'
        response['Content-Type'] = 'image/svg+xml'
        response['Access-Control-Allow-Origin'] = '*'
        return response



class LogoSvg(TemplateView):
    template_name = "archive/svg/logo.svg"
    def get_template_names(self) -> List[str]:
        templates = []
        if 'short_name' in self.kwargs:
            templates.append('archive/svg/logo/{}.svg'.format(self.kwargs['short_name']))
        templates.append(self.template_name)
        print(templates)
        return templates

    def get_context_data(self, theme: str='skyblue', short_name: str='us') -> Dict[str, Any]: # type: ignore
        context = {
            'theme': Theme.select_named_theme(archive=short_name, name=theme),
        }
        return context

    @method_decorator(cache_control(max_age=60*60, public=True))
    @vary_on_headers()
    def dispatch(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        response = super().dispatch(*args, **kwargs)
        response['Content-Type'] = 'image/svg+xml'
        response.override_vary = "" # type: ignore
        return response

class LogoSvgSmall(TemplateView):
    template_name = "archive/svg/logo-small.svg"
    def get_template_names(self) -> List[str]:
        templates = []
        if 'short_name' in self.kwargs:
            templates.append('archive/svg/logo-small/{}.svg'.format(self.kwargs['short_name']))
        templates.append(self.template_name)
        return templates

    def get_context_data(self, theme: str='skyblue', short_name: str='us') -> Dict[str, Any]: # type: ignore
        context = {
            'theme': Theme.select_named_theme(archive=short_name, name=theme),
        }
        return context

    @method_decorator(cache_control(max_age=60*60, public=True))
    def dispatch(self, *args: Any, **kwargs: Any) -> HttpResponseBase:
        response = super().dispatch(*args, **kwargs)
        response['Content-Type'] = 'image/svg+xml'
        return response
