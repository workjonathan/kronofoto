from django.urls import reverse as django_reverse
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
    uri = django_reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
    return as_absolute(uri)
