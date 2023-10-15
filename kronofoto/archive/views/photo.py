from django.views.generic import DetailView
from django.http import Http404
from ..reverse import reverse
from django.shortcuts import redirect
from django.core.cache import cache
from django.conf import settings
from django.views.generic.base import RedirectView, TemplateView
from django.template.loader import render_to_string
from .basetemplate import BasePhotoTemplateMixin
from .paginator import TimelinePaginator, FAKE_PHOTO
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..reverse import get_request, set_request, as_absolute
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.csrf import csrf_exempt
from typing import final

NO_URLS = dict(url='#', json_url='#')

class OrderedDetailBase(DetailView):
    pk_url_kwarg = 'photo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        object = self.object
        position = int(self.request.headers.get('us.fortepan.position', 3))
        object.position = position
        object.active = True
        before = list(reversed(queryset.photos_before(year=object.year, id=object.id)[:position+10]))
        if before:
            context['prev_photo'] = before[-1]
        for (i, photo) in enumerate(reversed(before)):
            photo.position = (position - i - 1) % 10
        position = len(before) % 10
        has_next = has_prev = True
        if len(before) < 10:
            has_prev = False
            before = [FAKE_PHOTO for _ in range(10)] + before
        after = list(queryset.photos_after(year=object.year, id=object.id)[:20-position-1])
        if after:
            context['next_photo'] = after[0]
        for (i, photo) in enumerate(after):
            photo.position = (position + i + 1) % 10
        if len(after) < 10 - position:
            has_next = False

        carousel = before + [object] + after
        while len(carousel) < 30:
            carousel.append(FAKE_PHOTO)
        context['object_list'] = carousel

        context['carousel_has_next'] = has_next
        context['carousel_has_prev'] = has_prev

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
        context["tags"] = object.get_accepted_tags(self.request.user)
        return context

    def render(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
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
