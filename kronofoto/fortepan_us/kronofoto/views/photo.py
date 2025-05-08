from django.views.generic import DetailView, ListView, View
from django.views.generic.list import MultipleObjectMixin
from django.http import Http404, HttpResponse, HttpRequest, HttpResponseBase
from django.template.response import TemplateResponse
from fortepan_us.kronofoto.reverse import reverse
from django.shortcuts import redirect, get_object_or_404
from django.core.cache import cache
from django.conf import settings
from django.views.generic.base import RedirectView, TemplateView
from django.template.loader import render_to_string
from .basetemplate import BasePhotoTemplateMixin
from .paginator import Paginator, EMPTY_PNG
from django.db.models import QuerySet
from fortepan_us.kronofoto.models.photo import Photo, PhotoQuerySet, BackwardList, ForwardList
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.csrf import csrf_exempt
from .base import PhotoRequest
from typing import final, TypedDict
from .basetemplate import Theme
from fortepan_us.kronofoto.forms import CarouselForm
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

        context['timelineclass'] = 'current-view'

        return context

class CarouselListView(BasePhotoTemplateMixin, MultipleObjectMixin, TemplateView):
    item_count = 40
    pk_url_kwarg = 'photo'
    model = Photo
    template_name = "kronofoto/components/thumbnails.html"
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
    template_name = "kronofoto/pages/photoview.html"


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

def logo_icon_view(request: HttpRequest, *, theme: str, short_name: Optional[str]=None) -> HttpResponse:
    return svg_view(request, theme=theme, short_name=short_name, name="logo-icon")

def logo_view(request: HttpRequest, *, theme: str, short_name: Optional[str]=None) -> HttpResponse:
    return svg_view(request, theme=theme, short_name=short_name, name="logo")

def logo_small_view(request: HttpRequest, *, theme: str, short_name: Optional[str]=None) -> HttpResponse:
    return svg_view(request, theme=theme, short_name=short_name, name="logo-small")

@cache_control(max_age=60*60, public=True)
@vary_on_headers()
def svg_view(request: HttpRequest, *, theme: str, short_name: Optional[str]=None, name: str) -> HttpResponse:
    template = f"kronofoto/svg/{name}.svg"
    context = {
        'theme': Theme.select_named_theme(name=theme)
    }
    templates = []
    if short_name:
        templates.append(f'kronofoto/svg/{name}/{short_name}.svg')
    templates.append(template)
    response = TemplateResponse(
        request=request,
        context=context,
        template=templates,
        headers={
            "Content-Type": "image/svg+xml",
        },
    )
    setattr(response, "override_vary", "")
    return response
