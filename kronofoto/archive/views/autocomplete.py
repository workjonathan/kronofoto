from django.views.generic.base import View, ContextMixin
from .jsonresponse import JSONResponseMixin
from django.http import QueryDict, HttpResponse, HttpRequest
from ..models.tag import Tag
from typing import Any, Dict, List, Union, Optional


class AutocompleteSearchView(JSONResponseMixin, ContextMixin, View):
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        return ctx

    def get_data(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            dict(value=expr, label=expr)
            for expr in ['tag:', 'contributor:', 'term:', 'year:', 'city:', 'county:', 'state:', 'country:', 'is_new:']
        ]

    def get(self, request: HttpRequest, **kwargs: Any) -> HttpResponse:
        self.request = request
        return self.render_to_json_response(self.get_context_data(**kwargs), safe=False, **kwargs)

    def render_to_response(self, context: Dict[str, Any], **kwargs: Any) -> HttpResponse:
        return self.render_to_json_response(context, safe=False, **kwargs)
