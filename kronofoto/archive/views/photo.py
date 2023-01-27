from django.views.generic import DetailView
from django.http import Http404
from django.urls import reverse
from django.shortcuts import redirect
from django.core.cache import cache
from django.conf import settings
from django.views.generic.base import RedirectView, TemplateView
from django.template.loader import render_to_string
from .basetemplate import BaseTemplateMixin
from .timelinepaginator import TimelinePaginator
from ..models.photo import Photo
from ..models.collectionquery import CollectionQuery
from ..reverse import get_request, set_request, as_absolute
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.csrf import csrf_exempt

NO_URLS = dict(url='#', json_url='#')

class PhotoView(BaseTemplateMixin, DetailView):
    items = 10
    pk_url_kwarg = 'photo'
    _queryset = None
    model = Photo

    @property
    def queryset(self):
        if self._queryset is None:
            self._queryset = self.get_queryset()
        return self._queryset

    def get_queryset(self):
        self.collection = CollectionQuery(self.final_expr, self.request.user)
        return Photo.objects.filter_photos(self.collection)

    #def get_object(self, *args, **kwargs):
    #    print("test")
    #    return self.model.objects.get(pk=self.model.accession2id(self.kwargs[self.pk_url_kwarg]))

    def get_paginator(self):
        return TimelinePaginator(self.queryset.order_by('year', 'id').select_related('donor', 'scanner'), self.items)

    def get_context_data(self, **kwargs):
        context = super(PhotoView, self).get_context_data(**kwargs)
        if self.request.headers.get('Hx-Target', None) == 'fi-image':
            context['base_template'] = 'archive/photo_partial.html'
        photo = self.kwargs['photo']
        if 'page' in self.kwargs:
            page = self.kwargs['page']
        else:
            page = 1
        queryset = self.queryset
        cache_info = self.collection.cache_encoding()
        #index_key = 'year_links:' + cache_info
        #index = cache.get(index_key)
        #if not index:
        #    index = queryset.year_links(params=self.request.GET)
        #    cache.set(index_key, index)

        paginator = self.get_paginator()
        page_selection = paginator.get_pages(page)
        year_range = queryset.year_range()
        start = year_range['start']
        end = year_range['end']

        try:
            photo_rec = page_selection.find(self.object.id)

            params = self.request.GET.copy()
            if 'constraint' in params:
                params.pop('constraint')
            for p in page_selection.photos():
                p.save_params(params)

            context['prev_page'], context["page"], context['next_page'] = page_selection.pages
            context['grid_url'] = photo_rec.get_grid_url()
            context['timeline_url'] = photo_rec.get_absolute_url()
            context["photo"] = photo_rec
            context["alttext"] = ', '.join(photo_rec.describe(self.request.user))
            context["tags"] = photo_rec.get_accepted_tags(self.request.user)
            #context["years"] = index
            context['timeline_key'] = cache_info
            context['timelinesvg_url'] = "{}?{}".format(reverse('timelinesvg', kwargs=dict(start=start, end=end)), self.request.GET.urlencode())
            if self.request.user.is_staff and self.request.user.has_perm('archive.change_photo'):
                context['edit_url'] = photo_rec.get_edit_url()
        except KeyError:
            pass
        return context

    def render(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response

    def get_redirect_url(self, photo):
        return photo.get_absolute_url(queryset=self.queryset, params=self.request.GET)

    def render_to_response(self, context, **kwargs):
        if 'timeline_key' not in context:
            try:
                photo = Photo.objects.get(id=self.kwargs['photo'])
                return redirect(self.get_redirect_url(photo))
            except Photo.DoesNotExist:
                raise Http404("Photo either does not exist or is not in that set of photos")
        return self.render(context, **kwargs)


class TimelineSvg(TemplateView):
    template_name = "archive/timeline.svg"
    def get_context_data(self, start, end, width=400):
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
                'target': "{}?{}".format(reverse('year-redirect', kwargs=dict(year=year)), self.request.GET.urlencode()),
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
