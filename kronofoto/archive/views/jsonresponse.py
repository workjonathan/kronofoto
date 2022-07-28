from django.http import JsonResponse
from ..reverse import set_request


class JSONResponseMixin:
    def set_request(self, request):
        set_request(request)
    def render_to_json_response(self, context, **response_kwargs):
        response = JsonResponse(self.get_data(context), **response_kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response
    def get_data(self, context):
        return context
