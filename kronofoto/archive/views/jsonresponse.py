from django.http import JsonResponse, HttpRequest, HttpResponse
from typing import Dict, Any, List, Union, Optional, TypeVar

T = TypeVar("T")

class JSONResponseMixin:
    def render_to_json_response(self, context: Dict[str, Any], **response_kwargs: Any) -> HttpResponse:
        response = JsonResponse(self.get_data(context), **response_kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response
    def get_data(self, context: Dict[str, Any]) -> Union[List [Dict[str, Any]], Dict[str, Any]]:
        return context
