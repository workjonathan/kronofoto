from django.http import JsonResponse


class JSONResponseMixin:
    def render_to_json_response(self, context, **response_kwargs):
        response = JsonResponse(self.get_data(context), **response_kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response
    def get_data(self, context):
        return context
