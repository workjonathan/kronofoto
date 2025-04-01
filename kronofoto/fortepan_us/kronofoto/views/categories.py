from django.http import HttpRequest, HttpResponse, Http404
from django.template.response import TemplateResponse
from fortepan_us.kronofoto.models.category import Category
from fortepan_us.kronofoto.models.archive import Archive
from typing import Optional
from django.views.generic import ListView
from .basetemplate import BaseTemplateMixin
from django.db.models import QuerySet
from .base import require_valid_archive, ArchiveRequest, ArchiveReference

@require_valid_archive
def category_list(request: HttpRequest, short_name: Optional[str]=None, domain: Optional[str]=None, category: Optional[str]=None) -> TemplateResponse:
    archive_ref = None
    if short_name:
        archive_ref = ArchiveReference(short_name, domain)
    archive_request = ArchiveRequest(request=request, archive_ref=archive_ref, category=category)
    if short_name:
        queryset = Category.objects.filter(archive__slug=short_name)
    else:
        queryset = Category.objects.all()
    context = archive_request.common_context
    context['object_list'] = queryset
    return TemplateResponse(
        request=request,
        template='kronofoto/pages/materials-list.html',
        context=context,
    )


