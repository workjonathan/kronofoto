from django.http import HttpRequest, HttpResponse, Http404
from django.template.response import TemplateResponse
from ..models.category import Category
from ..models.archive import Archive
from typing import Optional
from django.views.generic import ListView
from .basetemplate import BaseTemplateMixin
from django.db.models import QuerySet

class CategoryList(BaseTemplateMixin, ListView):
    def get_queryset(self) -> QuerySet[Category]:
        if 'short_name' in self.kwargs:
            if not Archive.objects.filter(slug=self.kwargs['short_name']).exists():
                raise Http404('archive not found')
            return Category.objects.filter(archive__slug=self.kwargs['short_name'])
        return Category.objects.all()
