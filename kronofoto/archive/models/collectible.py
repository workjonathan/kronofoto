from django.http import QueryDict
from django.urls import reverse

class Collectible:
    def get_absolute_url(self, params=None):
        return self.format_url(viewname='search-results', params=params)

    def get_json_url(self, params=None):
        return self.format_url(viewname='search-results-json', params=params)

    def format_url(self, viewname, params=None):
        if not params:
            params = QueryDict(mutable=True)
        return '{}?{}'.format(reverse(viewname), self.encode_params(params))


