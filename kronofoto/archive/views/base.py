from ..models import Photo, Category, Archive
from django.core.exceptions import BadRequest
from django.template.loader import select_template
from functools import cached_property, wraps
from ..search.expression import Expression
from ..search.parser import Parser
from django.db.models import QuerySet
from django.contrib.auth.models import User, AnonymousUser
from typing import Union, Optional, Dict, Any, Sequence, Callable, TypeVar
from dataclasses import dataclass, field
from ..forms import SearchForm
from django.shortcuts import get_object_or_404
from django.http import HttpRequest, QueryDict
import json

T = TypeVar('T')
def require_valid_archive(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def validate_archive(*args: Any, short_name: Optional[int]=None, **kwargs: Any) -> T:
        if short_name:
            get_object_or_404(Archive.objects.all(), slug=short_name)
        return func(*args, short_name=short_name, **kwargs)
    return validate_archive


@dataclass
class ArchiveRequest:
    request: HttpRequest
    category: Optional[str] = None
    short_name: Optional[str] = None

    @cached_property
    def form(self) -> SearchForm:
        return SearchForm(self.request.GET)

    @property
    def user(self) -> Union[User, AnonymousUser]:
        return self.request.user

    @property
    def base_template(self) -> str:
        if self.is_hx_request:
            print("reasera")
            return 'archive/base_partial.html'
        elif self.is_embedded:
            return 'archive/embedded-base.html'
        else:
            templates = []
            if self.short_name:
                templates.append('archive/base/{}.html'.format(self.short_name))
            templates.append('archive/base.html')
            return select_template(templates)

    @property
    def common_context(self) -> Dict[str, Any]:
        context : Dict[str, Any] = {}
        context['get_params'] = self.get_params
        context['search-form'] = self.form
        context['constraint'] = json.dumps({'Constraint': self.constraint})
        context['url_kwargs'] = self.url_kwargs
        context['base_template'] = self.base_template
        context['collection_name'] = self.collection_name
        context['timeline_url'] = '#'
        return context

    @property
    def collection_name(self) -> str:
        expr = self.expr
        if expr:
            if expr.is_collection():
                return str(expr.description())
            else:
                return "Search Results"
        else:
            return 'All Photos'

    @cached_property
    def url_kwargs(self) -> Dict[str, str]:
        args = {}
        if self.category:
            args['category'] = self.category
        if self.short_name:
            args['short_name'] = self.short_name
        return args

    @property
    def constraint(self) -> Optional[str]:
        return self.request.headers.get('Constraint', None)

    @property
    def hx_target(self) -> Optional[str]:
        return self.request.headers.get('Hx-Target', None)

    @property
    def is_hx_request(self) -> bool:
        return self.request.headers.get('Hx-Request', "false") not in ("false", "0", "")

    @property
    def is_embedded(self) -> bool:
        return self.request.headers.get('Embedded', "false") not in ("false", "0", "")

    @cached_property
    def expr(self) -> Optional[Expression]:
        form = self.form
        expr = None
        if form.is_valid():
            expr = form.cleaned_data['expr']
        return expr

    @cached_property
    def final_expr(self) -> Optional[Expression]:
        expr = self.expr
        constraint = self.get_constraint_expr(self.constraint)
        return (expr & constraint) if (expr and constraint) else expr or constraint

    @cached_property
    def params(self) -> Dict[str, Any]:
        return self.request.GET.copy()

    @cached_property
    def get_params(self) -> Dict[str, Any]:
        return self.filter_params(self.params) if not self.final_expr or self.final_expr.is_collection() else QueryDict()

    def get_constraint_expr(self, constraint: Optional[str]) -> Optional[Expression]:
        if constraint:
            try:
                return Parser.tokenize(constraint).parse().shakeout()
            except:
                raise BadRequest("invalid constraint")
        return None

    def filter_params(
        self,
        params: Dict[str, Any],
        removals: Sequence[str]=('id:lt', 'id:gt', 'page', 'year:gte', 'year:lte')
    ) -> Dict[str, Any]:
        get_params = params.copy()
        for key in removals:
            try:
                get_params.pop(key)
            except KeyError:
                pass
        return get_params

    def get_photo_queryset(self) -> QuerySet[Photo]:
        if self.form.is_valid():
            qs = Photo.objects.filter(is_published=True, year__isnull=False)
            short_name = self.url_kwargs.get('short_name')
            if short_name:
                qs = qs.filter(archive__slug=short_name)
            if 'category' in self.url_kwargs:
                category = get_object_or_404(Category.objects.all(), slug=self.url_kwargs['category'])
                qs = qs.filter(category=category)

            expr = self.final_expr
            if expr is None:
                return qs.order_by('year', 'id')

            if expr.is_collection():
                qs = expr.as_collection(qs, self.request.user)
            else:
                qs = expr.as_search(Photo.objects.filter(is_published=True), self.request.user)
            return qs
        else:
            raise BadRequest('invalid search request')

class PhotoRequest(ArchiveRequest):
    @property
    def base_template(self) -> str:
        if self.hx_target == 'fi-image':
            return 'archive/photo_partial.html'
        else:
            return super().base_template
