from django.views.generic.base import View, ContextMixin
from .jsonresponse import JSONResponseMixin
from ..models.tag import Tag


class AutocompleteSearchView(JSONResponseMixin, ContextMixin, View):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

    def get_data(self, context):
        return [
            dict(value=expr, label=expr)
            for expr in ['tag:', 'contributor:', 'term:', 'year:', 'city:', 'county:', 'state:', 'country:', 'is_new:']
        ]

    def get(self, request, **kwargs):
        self.request = request
        return self.render_to_json_response(self.get_context_data(**kwargs), safe=False, **kwargs)

    def render_to_response(self, context, **kwargs):
        return self.render_to_json_response(context, safe=False, **kwargs)
