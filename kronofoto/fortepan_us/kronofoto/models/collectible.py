from django.http import QueryDict
from fortepan_us.kronofoto.reverse import reverse
from typing import Optional, Any, Dict, Protocol
from typing_extensions import Self

class Collectible:
    def encode_params(self, params: QueryDict) -> str:
        raise NotImplementedError

    def get_absolute_url(self, kwargs: Optional[Dict[str, Any]]=None, params: Optional[QueryDict]=None) -> str:
        return self.format_url(viewname='kronofoto:gridview', kwargs=kwargs, params=params)

    def format_url(self, viewname: str, kwargs: Optional[Dict[str, Any]]=None, params: Optional[QueryDict]=None) -> str:
        if not params:
            params = QueryDict(mutable=True)
        return '{}?{}'.format(reverse(viewname, kwargs=kwargs), self.encode_params(params))
