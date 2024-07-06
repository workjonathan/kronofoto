from django.shortcuts import redirect
from django.views.generic import ListView
from django.http import HttpResponseBadRequest, QueryDict, HttpResponse, HttpRequest
from django.db.models import QuerySet
from django.core.cache import cache
from django.core.paginator import Paginator, Page
from .paginator import KeysetPaginator
from ..reverse import reverse
from django.template.loader import render_to_string
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from .basetemplate import BasePhotoTemplateMixin
from ..models import Photo
from ..models.photo import PhotoQuerySet
import json
from django import forms
from typing import Any, Tuple, Union, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from django.core.paginator import _SupportsPagination

class PageForwardForm(forms.Form):
    locals()["year:gte"] = forms.IntegerField(required=True)
    locals()["id:gt"] = forms.IntegerField(required=False)

class PageBackwardForm(forms.Form):
    locals()["year:lte"] = forms.IntegerField(required=True)
    locals()["id:lt"] = forms.IntegerField(required=False)


class Redirect(Exception):
    def __init__(self, msg: str, url: str):
        self.msg = msg,
        self.url = url

class GridView(BasePhotoTemplateMixin, ListView):
    model = Photo
    paginate_by = settings.GRID_DISPLAY_COUNT

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            return super().dispatch(request, *args, **kwargs)
        except Redirect as e:
            return redirect(e.url)

    def create_keyset_paginator(self, queryset: "_SupportsPagination[Any]", page_size: int) -> KeysetPaginator:
        return KeysetPaginator(queryset, page_size)

    def paginate_queryset(self, queryset: "_SupportsPagination[Any]", page_size: int) -> "Tuple[Paginator[Any], Page[Any], _SupportsPagination[Any], bool]":
        if self.final_expr and not self.final_expr.is_collection():
            return super().paginate_queryset(queryset, page_size)
        else:
            paginator = self.create_keyset_paginator(queryset, page_size)
            form: Union[PageForwardForm, PageBackwardForm] = PageForwardForm(self.params)
            if form.is_valid():
                page = paginator.get_page({
                    "year": form.cleaned_data['year:gte'],
                    "id": form.cleaned_data['id:gt'] or 0,
                    "reverse": False,
                })
                if len(page) == 0:
                    page = paginator.get_page(paginator.num_pages)

            else:
                form = PageBackwardForm(self.params)
                if form.is_valid():
                    page = paginator.get_page({
                        "year": form.cleaned_data['year:lte'],
                        "id": form.cleaned_data['id:lt'] or 9999999,
                        "reverse": True,
                    })
                    if len(page) == 0:
                        page = paginator.get_page({})
                    elif len(page) < page_size:
                        page = paginator.get_page({
                            "year": page[0].year,
                            "id": page[0].id-1,
                            "reverse": False,
                        })
                else:
                    page = paginator.get_page({})
            self.params.pop('year:gte', None)
            self.params.pop('id:gt', None)
            self.params.pop('year:lte', None)
            self.params.pop('id:lt', None)
            return paginator, page, queryset, True

    def get_no_objects_queryset(self) -> QuerySet[Any]:
        return Photo.objects.filter(phototag__tag__tag='silly', phototag__accepted=True).order_by('?')

    def get_no_objects_context(self, object_list: QuerySet) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
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

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        object_list = context['object_list']
        context['formatter'] = KeysetViewFormatter(self.url_kwargs, self.params)
        context.update(self.get_no_objects_context(object_list))
        return context

    def get_queryset(self) -> PhotoQuerySet:
        qs = super().get_queryset()
        try:
            raise Redirect("single object found", url=qs.order_by('year', 'id').get().get_absolute_url())
        except (MultipleObjectsReturned, self.model.DoesNotExist):
            pass

        return qs

    def attach_params(self, photos: Any) -> None:
        params = self.params.copy()
        if 'display' in params:
            params.pop('display')
        if not self.final_expr or self.final_expr.is_collection():
            for photo in photos:
                photo.save_params(params=params)


class KeysetViewFormatter:
    def __init__(self, kwargs: Dict[str, Any], parameters: QueryDict):
        if 'page' in parameters:
            parameters.pop('page')
        self.parameters = parameters
        self.kwargs = kwargs

    def page_url(self, num: int) -> str:
        params = self.parameters.copy()
        if isinstance(num, int):
            if num != 1:
                params['page'] = str(num)
        elif 'reverse' in num and num['reverse']:
            params['year:lte'] = num['year']
            params['id:lt'] = num['id']
        elif 'reverse' in num and not num['reverse']:
            params['year:gte'] = num['year']
            params['id:gt'] = num['id']

        return "{}?{}".format(reverse('kronofoto:gridview', kwargs=self.kwargs), params.urlencode())

