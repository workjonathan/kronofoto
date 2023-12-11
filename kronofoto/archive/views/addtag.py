from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, BadRequest
from django.views.generic.edit import FormView
from django.shortcuts import get_object_or_404
from ..reverse import reverse
from ..forms import TagForm
from .basetemplate import BaseTemplateMixin
from ..models import Photo
from django.http import HttpRequest, HttpResponse, QueryDict
from django.template.response import TemplateResponse
from typing import Any


def tags_view(request: HttpRequest, photo: int, **kwargs: Any) -> HttpResponse:
    object = get_object_or_404(Photo.objects.all(), id=photo)
    if request.method and request.method.lower() == 'put':
        if request.user.is_anonymous:
            raise PermissionDenied
        put_data = QueryDict(request.body)
        form = TagForm(data=put_data)
        if form.is_valid():
            form.add_tag(object, user=request.user)
        else:
            raise BadRequest
    return TemplateResponse(
        request,
        "archive/snippets/tags.html",
        {"tags": object.get_all_tags(user=request.user)}
    )
