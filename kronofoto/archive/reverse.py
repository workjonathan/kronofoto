from django.urls import reverse as django_reverse, resolve as django_resolve, ResolverMatch
from django.contrib.sites.shortcuts import get_current_site
from threading import local
from django.http import HttpRequest
from dataclasses import dataclass
from django.contrib.sites.models import Site
from urllib.parse import urlparse
from django.conf import settings
from django.utils.functional import lazy
from typing import Any, Optional, Union, Dict, List, Protocol, Tuple, Sequence

requests = local()

@dataclass
class ResolveResults:
    domain: str
    match: ResolverMatch

def get_request() -> Optional[HttpRequest]:
    return getattr(requests, 'current_request', None)

def set_request(req: HttpRequest) -> None:
    requests.current_request = req

def as_absolute(uri: str) -> str:
    req = get_request()
    return req.build_absolute_uri(uri) if req else uri

def reverse(viewname: str, urlconf: Optional[str]=None, args: Optional[Sequence[Any]]=None, kwargs: Optional[Dict[str, Any]]=None, current_app: Optional[str]=None, domain: Optional[str]=None) -> str:
    domain = domain or Site.objects.get_current().domain
    uri = django_reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
    return "{scheme}//{domain}{uri}".format(scheme=settings.KF_URL_SCHEME, domain=domain, uri=uri)

reverse_lazy = lazy(reverse, str)

def resolve(path: str, urlconf: Optional[str]=None) -> ResolveResults:
    parseResults = urlparse(path)
    match = django_resolve(parseResults.path)
    return ResolveResults(parseResults.netloc, match)
