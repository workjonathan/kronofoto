from django.shortcuts import redirect
from django.views.generic import ListView
from django.core.cache import cache
from django.core.paginator import Paginator, Page
from .paginator import KeysetPaginator
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from .basetemplate import BaseTemplateMixin
from ..models import Photo, CollectionQuery
import json


class GridView(BaseTemplateMixin, ListView):
    model = Photo
    paginate_by = settings.GRID_DISPLAY_COUNT
    _queryset = None

    def dispatch(self, request, *args, **kwargs):
        if self.form.is_valid():
            return super().dispatch(request, *args, **kwargs)
        else:
            return HttpResponseBadRequest('Invalid search parameters')

    @property
    def queryset(self):
        if self._queryset is None:
            self._queryset = self.get_queryset()
        return self._queryset

    def render(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        return response

    def paginate_queryset(self, queryset, page_size):
        self.params = self.request.GET.copy()
        if self.final_expr and not self.final_expr.is_collection():
            return super().paginate_queryset(queryset, page_size)
        else:
            try:
                page = self.kwargs['page']
            except KeyError:
                try:
                    page = int(self.params.pop('page')[0])
                except KeyError:
                    page = None
            if page:
                first_photo = queryset[page_size*(page-1)]
                self.params['year:gte'] = first_photo.year
                self.params['id:gt'] = first_photo.id

            paginator = KeysetPaginator(queryset, page_size)
            try:
                # probably should handle no id
                page = paginator.get_page(dict(year=self.params.pop('year:gte')[0], id=self.params.pop('id:gt')[0], reverse=False))
            except KeyError:
                try:
                    page = paginator.get_page(dict(year=self.params.pop('year:lte')[0], id=self.params.pop('id:lt')[0], reverse=True))
                    if len(page) < page_size:
                        page = paginator.get_page(dict(year=page[0].year, id=page[0].id-1, reverse=False))
                except KeyError:
                    page = paginator.get_page({})
            return paginator, page, queryset, True

    def render_to_response(self, context, **kwargs):
        if hasattr(self, 'redirect'):
            return self.redirect
        return self.render(context, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        context['search-form'] = self.form
        context['constraint'] = json.dumps({"Constraint": self.request.headers.get('Constraint', None)})
        context['formatter'] = KeysetViewFormatter(self.params)
        if not self.object_list.exists():
            context['noresults'] = True
            photo_rec = Photo.objects.filter(phototag__tag__tag='silly', phototag__accepted=True).order_by('?')[0]
            context['oops_photo'] = photo_rec
            context['query_expr'] = str(self.final_expr)
            context["tags"] = photo_rec.get_accepted_tags(self.request.user)
        else:
            context['noresults'] = False
            if not self.final_expr or self.final_expr.is_collection():
                context['timeline_url'] = page_obj[0].get_absolute_url()
        self.attach_params(page_obj)
        return context

    def get_queryset(self):
        expr = self.final_expr

        if expr is None or expr.is_collection():
            self.collection = CollectionQuery(expr, self.request.user)
            qs = self.model.objects.filter_photos(self.collection).order_by('year', 'id')
        else:
            qs = expr.as_search(self.model.objects, self.request.user)
        try:
            self.redirect = redirect(qs.get().get_absolute_url())
        except (MultipleObjectsReturned, self.model.DoesNotExist):
            pass
        return qs

    def attach_params(self, photos):
        params = self.params.copy()
        if 'display' in params:
            params.pop('display')
        for photo in photos:
            photo.save_params(params=params)


class KeysetViewFormatter:
    def __init__(self, parameters):
        if 'page' in parameters:
            parameters.pop('page')
        self.parameters = parameters

    def page_url(self, num):
        params = self.parameters.copy()
        if isinstance(num, int):
            if num != 1:
                params['page'] = num
        elif 'reverse' in num and num['reverse']:
            params['year:lte'] = num['year']
            params['id:lt'] = num['id']
        elif 'reverse' in num and not num['reverse']:
            params['year:gte'] = num['year']
            params['id:gt'] = num['id']

        return "{}?{}".format(reverse('kronofoto:gridview'), params.urlencode())

