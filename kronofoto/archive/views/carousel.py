from django.http import HttpResponse
from django.views.generic import View
from django.views.generic.list import MultipleObjectMixin
from ..forms import CarouselForm
from .paginator import KeysetPaginator
from .basetemplate import BasePhotoTemplateMixin
import json
from ..models.photo import Photo


class CarouselView(BasePhotoTemplateMixin, MultipleObjectMixin, View):
    form_class = CarouselForm
    model = Photo

    def get_form(self):
        return self.form_class(self.request.GET)

    def form_valid(self, form):
        response = HttpResponse("", status_code=204)
        qs = super().get_queryset()
        response['Hx-Trigger'] = form

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.form = self.get_form()

    def get_paginate_by(self, queryset):
        return self.form.cleaned_data['count']

    def paginate_queryset(self, queryset, page_size):
        paginator = KeysetPaginator(queryset, page_size)
        if self.form.cleaned_data['id_gt'] is not None:
            page = paginator.get_page(dict(year=self.form.cleaned_data['year_gte'], id=self.form.cleaned_data['id_gt'], reverse=False))
        else:
            page = paginator.get_page(dict(year=self.form.cleaned_data['year_lte'], id=self.form.cleaned_data['id_lt'], reverse=True))
        return paginator, page, queryset, True

    def get(self, request, *args, **kwargs):
        if self.form.is_valid():
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            data = {'object_list': [
                {
                    'id': object.id,
                    'year': object.year,
                    'thumbnail': object.thumbnail.url,
                }
                for object in context['page_obj']
            ]}
            response = HttpResponse("", status=204)
            response['Hx-Trigger'] = json.dumps({"kronofoto:onThumbnails": data})
            return response
        else:
            return HttpResponse(self.form.errors.as_json(escape_html=True), status=400)
