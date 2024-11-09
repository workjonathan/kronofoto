from django.http import HttpRequest, HttpResponse
from typing import Callable, Union, Optional, Dict, Any
from django.urls import resolve
from django.utils.cache import patch_vary_headers
import json

# could be a decorator
class CorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        resolve_match = resolve(request.path_info)
        if 'kronofoto' in resolve_match.app_names:
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'constraint, embedded, hx-current-url, hx-request, hx-target, hx-trigger, us.fortepan.position'
            patch_vary_headers(response, ['embedded', 'constraint', 'hx-request', 'hx-trigger']) # type: ignore
            hxtriggers = response.headers.get('Hx-Trigger', None)
            if hxtriggers:
                hxtriggersdict = json.loads(hxtriggers)
            else:
                hxtriggersdict = {}
            response.headers['Hx-Trigger'] = json.dumps(hxtriggersdict)
        return response

class OverrideVaryMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if hasattr(response, "override_vary"):
            response.headers['Vary'] = ""
            response.cookies.clear()
        return response

