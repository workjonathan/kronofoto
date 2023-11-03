from django.http import HttpRequest, HttpResponse, Http404
from django.template.response import TemplateResponse
from ..models.category import Category
from ..models.archive import Archive
from typing import Optional
from django.views.generic import ListView
from .basetemplate import BaseTemplateMixin
from django.db.models import QuerySet
from .base import require_valid_archive, ArchiveRequest

@require_valid_archive
def category_list(request: HttpRequest, short_name: Optional[str]=None, category: Optional[str]=None) -> TemplateResponse:
    archive_request = ArchiveRequest(request=request, short_name=short_name, category=category)
    if short_name:
        queryset = Category.objects.filter(archive__slug=short_name)
    else:
        queryset = Category.objects.all()
    context = archive_request.common_context
    context['object_list'] = queryset
    return TemplateResponse(
        request=request,
        template='archive/category_list.html',
        context=context,
    )


