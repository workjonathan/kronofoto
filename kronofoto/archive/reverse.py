from django.urls import reverse as django_reverse
from django.contrib.sites.shortcuts import get_current_site
from threading import local

requests = local()

def get_request():
    return getattr(requests, 'current_request', None)

def set_request(req):
    requests.current_request = req

def as_absolute(uri):
    req = get_request()
    return req.build_absolute_uri(uri) if req else uri

def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None):
    from django.contrib.sites.models import Site
    uri = django_reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
    return "https://{domain}{uri}".format(domain=Site.objects.get_current().domain, uri=uri)
