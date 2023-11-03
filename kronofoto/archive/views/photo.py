from django.views.generic import DetailView, ListView, View
from django.views.generic.list import MultipleObjectMixin
from django.http import Http404, HttpResponse
from ..reverse import reverse
from django.shortcuts import redirect, get_object_or_404
from django.core.cache import cache
from django.conf import settings
from django.views.generic.base import RedirectView, TemplateView
from django.template.loader import render_to_string
from .basetemplate import BasePhotoTemplateMixin
from .paginator import TimelinePaginator, EMPTY_PNG
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..reverse import get_request, set_request, as_absolute
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.csrf import csrf_exempt
from .base import PhotoRequest
from typing import final, TypedDict
from .basetemplate import THEME
from ..forms import CarouselForm
import random
from itertools import cycle, chain, islice
from dataclasses import dataclass
import json

class Thumbnail(TypedDict):
    url: str
    height: int
    width: int

@dataclass
class PhotoPlaceholder:
    thumbnail: Thumbnail
    is_spacer: bool
    photo: Photo

    def get_absolute_url(self, *args, **kwargs):
        return self.photo.get_absolute_url(*args, **kwargs)

    @property
    def id(self):
        return self.photo.id

    @property
    def year(self):
        return self.photo.year

EMPTY_THUMBNAIL = Thumbnail(url=EMPTY_PNG, height=75, width=75)

NO_URLS = dict(url='#', json_url='#')


class OrderedDetailBase(DetailView):
    pk_url_kwarg = 'photo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        object = self.object
        object.active = True

        before = queryset.photos_before(year=object.year, id=object.id).iterator(chunk_size=self.item_count)
        before_cycling = cycle(
            PhotoPlaceholder(
                thumbnail=EMPTY_THUMBNAIL,
                is_spacer=True,
                photo=photo
            ) for photo in queryset.order_by('-year', '-id').iterator(chunk_size=self.item_count)
        )
        before_looping = chain(before, before_cycling)
        before = list(islice(before_looping, self.item_count))
        context['prev_photo'] = before[0]

        after = queryset.photos_after(year=object.year, id=object.id).iterator(chunk_size=self.item_count)
        after_cycling = cycle(
            PhotoPlaceholder(
                thumbnail=EMPTY_THUMBNAIL,
                is_spacer=True,
                photo=photo,
            ) for photo in queryset.iterator(chunk_size=self.item_count)
        )
        after_looping = chain(after, after_cycling)
        after = list(islice(after_looping, self.item_count))
        context['next_photo'] = after[0]

        before.reverse()
        carousel = before + [object] + after
        context['object_list'] = carousel

        context['queryset'] = queryset

        return context

class CarouselListView(BasePhotoTemplateMixin, MultipleObjectMixin, TemplateView):
    item_count = 40
    pk_url_kwarg = 'photo'
    model = Photo
    template_name = "archive/thumbnails.html"
    form_class = CarouselForm

    def get_form(self):
        return self.form_class(self.request.GET)

    def form_valid(self, form):
        queryset = self.object_list = self.get_queryset()
        object = get_object_or_404(self.model, pk=form.cleaned_data['id'])
        offset = form.cleaned_data['offset']
        if form.cleaned_data['forward']:
            objects = queryset.photos_after(year=object.year, id=object.id).iterator(chunk_size=self.item_count)
            objects_cycling = cycle(
                PhotoPlaceholder(
                    thumbnail=EMPTY_THUMBNAIL,
                    is_spacer=True,
                    photo=photo
                ) for photo in queryset.iterator(chunk_size=self.item_count)
            )
            objects_looping = chain(objects, objects_cycling)
            objects = list(islice(objects_looping, self.item_count))

        else:
            objects = queryset.photos_before(year=object.year, id=object.id).iterator(chunk_size=self.item_count)
            objects_cycling = cycle(
                PhotoPlaceholder(
                    thumbnail=EMPTY_THUMBNAIL,
                    is_spacer=True,
                    photo=photo
                ) for photo in queryset.order_by('-year', '-id').iterator(chunk_size=self.item_count)
            )
            objects_looping = chain(objects, objects_cycling)
            objects = list(islice(objects_looping, self.item_count))
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

    def form_invalid(self, form):
        return HttpResponse("", status=400)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)



class PhotoView(BasePhotoTemplateMixin, OrderedDetailBase):
    item_count = 20
    pk_url_kwarg = 'photo'
    _queryset = None
    model = Photo
    archive_request_class = PhotoRequest

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

    def get_context_data(self, **kwargs):
        context = super(PhotoView, self).get_context_data(**kwargs)
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
        return response

    def render_to_response(self, context, **kwargs):
        return self.render(context, **kwargs)

class TimelineSvg(TemplateView):
    template_name = "archive/timeline.svg"
    def get_context_data(self, start, end, short_name=None, width=400, category=None):
        url_kwargs = {}
        if category:
            url_kwargs['category'] = category
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



class LogoSvg(TemplateView):
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

class LogoSvgSmall(TemplateView):
    template_name = "archive/svg/logo-small.svg"
    def get_template_names(self):
        templates = []
        if 'short_name' in self.kwargs:
            templates.append('archive/svg/logo-small/{}.svg'.format(self.kwargs['short_name']))
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
