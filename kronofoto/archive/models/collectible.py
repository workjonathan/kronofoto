from django.http import QueryDict
from ..reverse import reverse

class Collectible:
    def get_absolute_url(self, kwargs=None, params=None):
        return self.format_url(viewname='kronofoto:gridview', kwargs=kwargs, params=params)

    def format_url(self, viewname, kwargs=None, params=None):
        if not params:
            params = QueryDict(mutable=True)
        return '{}?{}'.format(reverse(viewname, kwargs=kwargs), self.encode_params(params))
