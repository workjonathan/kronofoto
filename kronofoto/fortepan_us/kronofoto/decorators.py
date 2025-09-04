from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from dataclasses import dataclass
from django.views.decorators.cache import cache_page

import typing

class RequestHandler(typing.Protocol):
    def __call__(self, request: HttpRequest, *args: typing.Any, **kwargs: typing.Any) -> HttpResponse:
        ...

class CacheFunction(typing.Protocol):
    def __call__(self, request: HttpRequest, *args: typing.Any, **kwargs: typing.Any) -> int:
        ...

def dynamic_cache_page(cacheF: CacheFunction) -> typing.Callable[[RequestHandler], RequestHandler]:
    def wrapper(handler: RequestHandler) -> RequestHandler:
        def _(request: HttpRequest, *args: typing.Any, **kwargs: typing.Any) -> HttpResponse:
            return cache_page(timeout=cacheF(request, *args, **kwargs))(handler)(request, *args, **kwargs)
        return _
    return wrapper

def strip_cookies(func: RequestHandler) -> RequestHandler:
    def _(request: HttpRequest, *args: typing.Any, **kwargs: typing.Any) -> HttpResponse:
        for cookie in list(request.COOKIES):
            if cookie != 'django_language':
                request.COOKIES.pop(cookie)
        request.user = AnonymousUser()
        return func(request, *args, **kwargs)
    return _
