from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from typing import Callable
from django.urls import resolve
from django.utils.cache import patch_vary_headers

# could be a decorator
class CorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if hasattr(request, "KF_RETURNING_WHEEL") and request.KF_RETURNING_WHEEL and not request.COOKIES.get("kronofoto:returning:wheel", "0") != "0":
            response.set_cookie("kronofoto:returning:wheel", value="1", max_age=10)
        if 'kronofoto' in resolve(request.path_info).app_names:
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'constraint, embedded, hx-current-url, hx-request, hx-target, hx-trigger, us.fortepan.position'
            patch_vary_headers(response, ['embedded', 'constraint', 'hx-request']) # type: ignore
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

