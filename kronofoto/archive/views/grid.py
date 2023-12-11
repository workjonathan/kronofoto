from django.shortcuts import redirect
from django.views.generic import ListView
from django.http import HttpResponseBadRequest, QueryDict
from django.core.cache import cache
from django.core.paginator import Paginator, Page
from .paginator import KeysetPaginator
from ..reverse import reverse
from django.template.loader import render_to_string
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from .basetemplate import BasePhotoTemplateMixin
from ..models import Photo, CollectionQuery
import json
from django import forms

class PageForwardForm(forms.Form):
    locals()["year:gte"] = forms.IntegerField(required=True)
    locals()["id:gt"] = forms.IntegerField(required=False)

class PageBackwardForm(forms.Form):
    locals()["year:lte"] = forms.IntegerField(required=True)
    locals()["id:lt"] = forms.IntegerField(required=False)


class Redirect(Exception):
    def __init__(self, msg, url):
        self.msg = msg,
        self.url = url

class GridView(BasePhotoTemplateMixin, ListView):
    model = Photo
    paginate_by = settings.GRID_DISPLAY_COUNT
    _queryset = None

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Redirect as e:
            return redirect(e.url)

    @property
    def queryset(self):
        if self._queryset is None:
            self._queryset = self.get_queryset()
        return self._queryset

    def create_keyset_paginator(self, queryset, page_size):
        return KeysetPaginator(queryset, page_size)

    def paginate_queryset(self, queryset, page_size):
        if self.final_expr and not self.final_expr.is_collection():
            return super().paginate_queryset(queryset, page_size)
        else:
            paginator = self.create_keyset_paginator(queryset, page_size)
            form = PageForwardForm(self.params)
            if form.is_valid():
                self.params.pop('year:gte', None)
                self.params.pop('year:gt', None)
                page = paginator.get_page({
                    "year": form.cleaned_data['year:gte'],
                    "id": form.cleaned_data['id:gt'] or 0,
                    "reverse": False,
                })
            else:
                form = PageBackwardForm(self.params)
                if form.is_valid():
                    self.params.pop('year:lte', None)
                    self.params.pop('year:lt', None)
                    page = paginator.get_page({
                        "year": form.cleaned_data['year:lte'],
                        "id": form.cleaned_data['id:lt'] or 9999999,
                        "reverse": True,
                    })
                    if len(page) == 0:
                        return paginator, page, queryset, True
                    elif len(page) < page_size:
                        page = paginator.get_page({
                            "year": page[0].year,
                            "id": page[0].id-1,
                            "reverse": False,
                        })
                else:
                    page = paginator.get_page({})
            return paginator, page, queryset, True

    def get_no_objects_queryset(self):
        return Photo.objects.filter(phototag__tag__tag='silly', phototag__accepted=True).order_by('?')

    def get_no_objects_context(self, object_list):
        context = {}
        if not object_list.exists():
            context['noresults'] = True
            context['query_expr'] = str(self.final_expr)
            try:
                photo_rec = self.get_no_objects_queryset()[0]
                context['oops_photo'] = photo_rec
                context["tags"] = photo_rec.get_accepted_tags(self.request.user)
            except IndexError:
                context["tags"] = []

        else:
            context['noresults'] = False
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        object_list = context['object_list']
        context['formatter'] = KeysetViewFormatter(self.url_kwargs, self.params)
        context.update(self.get_no_objects_context(object_list))
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        try:
            raise Redirect("single object found", url=qs.get().get_absolute_url())
        except (MultipleObjectsReturned, self.model.DoesNotExist):
            pass

        return qs

    def attach_params(self, photos):
        params = self.params.copy()
        if 'display' in params:
            params.pop('display')
        if not self.final_expr or self.final_expr.is_collection():
            for photo in photos:
                photo.save_params(params=params)


class KeysetViewFormatter:
    def __init__(self, kwargs, parameters):
        if 'page' in parameters:
            parameters.pop('page')
        self.parameters = parameters
        self.kwargs = kwargs

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

        return "{}?{}".format(reverse('kronofoto:gridview', kwargs=self.kwargs), params.urlencode())

