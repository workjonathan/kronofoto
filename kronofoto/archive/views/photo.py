from django.views.generic import DetailView
from django.http import Http404
from ..reverse import reverse
from django.shortcuts import redirect
from django.core.cache import cache
from django.conf import settings
from django.views.generic.base import RedirectView, TemplateView
from django.template.loader import render_to_string
from .basetemplate import BasePhotoTemplateMixin, BasePermissiveCORSMixin
from .paginator import TimelinePaginator, FAKE_PHOTO
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..reverse import get_request, set_request, as_absolute
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.csrf import csrf_exempt
from typing import final
from .basetemplate import THEME
import random

NO_URLS = dict(url='#', json_url='#')

class OrderedDetailBase(DetailView):
    pk_url_kwarg = 'photo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        object = self.object
        object.active = True

        before = list(queryset.photos_before(year=object.year, id=object.id)[:20])
        if before:
            context['prev_photo'] = before[0]
        while len(before) < 20:
            before.append(FAKE_PHOTO)

        after = list(queryset.photos_after(year=object.year, id=object.id)[:20])
        if len(after):
            context['next_photo'] = after[0]
        while len(after) < 20:
            after.append(FAKE_PHOTO)

        before.reverse()
        carousel = before + [object] + after
        context['object_list'] = carousel

        context['queryset'] = queryset

        return context


class PhotoView(BasePhotoTemplateMixin, OrderedDetailBase):
    items = 10
    pk_url_kwarg = 'photo'
    _queryset = None
    model = Photo

    @property
    def queryset(self):
        if self._queryset is None:
            self._queryset = self.get_queryset()
        return self._queryset

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.queryset
        try:
            return queryset.get(id=self.kwargs['photo'])
        except queryset.model.DoesNotExist:
            raise Http404("No photo with this accession number is in this collection.")

    def get_hx_context(self):
        if self.request.headers.get('Hx-Target', None) == 'fi-image-tag':
            return {'base_template': 'archive/photo_partial.html'}
        else:
            return super().get_hx_context()


    def get_context_data(self, **kwargs):
        context = super(PhotoView, self).get_context_data(**kwargs)
        self.params = self.request.GET.copy()
        object = self.object
        queryset = self.queryset
        year_range = queryset.year_range()
        start = year_range['start']
        end = year_range['end']

        context['grid_url'] = object.get_grid_url()
        context['timeline_url'] = object.get_absolute_url()
        context["photo"] = object
        return context

    def render(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response

    def render_to_response(self, context, **kwargs):
        return self.render(context, **kwargs)


class TimelineSvg(TemplateView):
    template_name = "archive/timeline.svg"
    def get_context_data(self, start, end, short_name=None, width=400):
        url_kwargs = {}
        if short_name:
            url_kwargs['short_name'] = short_name
        context = {
            'minornotches': [],
            'majornotches': [],
            'viewBox': [0, 0, width, 10],
            'view': self,
        }
        years = end-start+1
        for i, year in enumerate(range(start, end+1)):
            xpos = i*width/years
            boxwidth = width/years
            marker = {
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

    def options(self, *args, **kwargs):
        response = super().options(*args, **kwargs)
        response['Access-Control-Allow-Headers'] = 'constraint, embedded, hx-current-url, hx-request, hx-target, hx-trigger'
        return response

    @cache_control(max_age=60*60, public=True)
    def dispatch(self, *args, **kwargs):
        response = super().dispatch(*args, **kwargs)
        response['Vary'] = 'Constraint'
        response['Content-Type'] = 'image/svg+xml'
        response['Access-Control-Allow-Origin'] = '*'
        return response



class LogoSvg(BasePermissiveCORSMixin, TemplateView):
    template_name = "archive/svg/logo.svg"
    def get_template_names(self):
        templates = []
        if 'short_name' in self.kwargs:
            templates.append('archive/svg/logo/{}.svg'.format(self.kwargs['short_name']))
        templates.append(self.template_name)
        return templates

    def get_context_data(self, theme='skyblue', short_name='us'):
        context = {
            'theme': THEME[short_name][theme]
        }
        return context

    @cache_control(max_age=60*60, public=True)
    def dispatch(self, *args, **kwargs):
        response = super().dispatch(*args, **kwargs)
        response['Content-Type'] = 'image/svg+xml'
        return response

class LogoSvgSmall(BasePermissiveCORSMixin, TemplateView):
    template_name = "archive/svg/logo-small.svg"
    def get_template_names(self):
        templates = []
        if 'short_name' in self.kwargs:
            templates.append('archive/svg/logo/{}.svg'.format(self.kwargs['short_name']))
        templates.append(self.template_name)
        return templates

    def get_context_data(self, theme='skyblue', short_name='us'):
        context = {
            'theme': THEME[short_name][theme]
        }
        return context

    @cache_control(max_age=60*60, public=True)
    def dispatch(self, *args, **kwargs):
        response = super().dispatch(*args, **kwargs)
        response['Content-Type'] = 'image/svg+xml'
        return response
