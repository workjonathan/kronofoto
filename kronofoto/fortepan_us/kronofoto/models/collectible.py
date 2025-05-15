from django.http import QueryDict
from fortepan_us.kronofoto.reverse import reverse
from typing import Optional, Any, Dict, Protocol
from typing_extensions import Self


class Collectible:
    def encode_params(self, params: QueryDict) -> str:
        """Build query string that filters to this collection.

        Args:
            params (QueryDict): query parameters to also include.

        Returns:
            str: A query string for a GET request that filters to this object's collection.
        """
        raise NotImplementedError

    def get_absolute_url(
        self,
        kwargs: Optional[Dict[str, Any]] = None,
        params: Optional[QueryDict] = None,
    ) -> str:
        """Get the canonical user facing URL for this object's collection.

        Adds optional parameters to allow category and archive based
        collections, as well as constraints for web components.

        Args:
            kwargs (dict[str, Any], optional): Defaults to None. Allows filtering by archive and category.
            params (QueryDict, optional): Defaults to None. Allows GET query parameters.

        Return:
            str: The URL for the requested collection.
        """


        return self.format_url(
            viewname="kronofoto:gridview", kwargs=kwargs, params=params
        )

    def format_url(
        self,
        viewname: str,
        kwargs: Optional[Dict[str, Any]] = None,
        params: Optional[QueryDict] = None,
    ) -> str:
        """A wrapper for reverse that handles the query parameter part of the
        URL.

        Args:
            viewname (str): Django's name for the url.
            kwargs (dict[str, Any], optional): Defaults to None. URL kwargs.
            params (QueryDict, optional): Defaults to None. URL query parameters

        Returns:
            str: The URL constructed from the arguments.
        """
        if not params:
            params = QueryDict(mutable=True)
        return "{}?{}".format(
            reverse(viewname, kwargs=kwargs), self.encode_params(params)
        )
