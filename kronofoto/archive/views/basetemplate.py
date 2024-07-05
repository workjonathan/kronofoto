from django.core.cache import cache
from django.http import QueryDict, Http404, HttpRequest, HttpResponse, HttpResponseBase
from django.conf import settings
from django.core.exceptions import BadRequest
from django.templatetags.static import static
from django.template.loader import select_template
from django.db.models import QuerySet
from ..search.expression import Expression
from django.shortcuts import get_object_or_404
import random
import json
from ..reverse import set_request, reverse
from ..forms import SearchForm
from ..search.parser import Parser, NoExpression
from ..models import Photo
from ..models.photo import PhotoQuerySet
from ..models.archive import Archive
from ..models import Category
from functools import reduce
import operator
from dataclasses import dataclass, replace
from .base import ArchiveRequest, require_valid_archive
from django.utils.decorators import method_decorator
import random
from typing import Optional, Type, TypeVar, Any, Protocol, Dict

T = TypeVar("T", bound="Theme")

class ThemeDict(dict):
    def __missing__(self, key: str) -> str:
        return self['us']

@dataclass
class Theme:
    color: str
    colorDarker: str
    colorLighter: str
    menuSvg: str
    infoSvg: str
    downloadSvg: str
    searchSvg: str
    carrotSvg: str
    timelineSvg: str

    name: str
    archive: Optional[str]

    colors = {
        'skyblue': ("#6E86BC", "#A8B6D7", "#53658D"),
        'golden': ("#C2891C", "#D6BC89", "#987024"),
        'haybail': ("#C2A562", "#CEB57C", "#A28B54"),
    }

    def logo(self) -> str:
        kwargs = {'theme': self.name}
        if self.archive:
            kwargs['short_name'] = self.archive
        return reverse('kronofoto:logosvg', kwargs=kwargs)

    def logosmall(self) -> str:
        kwargs = {'theme': self.name}
        if self.archive:
            kwargs['short_name'] = self.archive
        return reverse('kronofoto:logosvgsmall', kwargs=kwargs)

    @classmethod
    def select_named_theme(cls: Type[T], name: str, archive: Optional[str]=None) -> T:
        try:
            colors = cls.colors[name]
        except KeyError:
            colors = cls.colors['skyblue']
        return cls(
            color=colors[0],
            colorLighter=colors[1],
            colorDarker=colors[2],
            menuSvg='assets/images/{}/menu.svg'.format(name),
            infoSvg='assets/images/{}/info.svg'.format(name),
            downloadSvg='assets/images/{}/download.svg'.format(name),
            searchSvg='assets/images/{}/search.svg'.format(name),
            carrotSvg='assets/images/{}/carrot.svg'.format(name),
            timelineSvg='assets/images/{}/toggle.svg'.format(name),
            name=name,
            archive=archive,
        )


    @classmethod
    def select_random_theme(cls: Type[T], archive: Optional[str]=None) -> T:
        name, color = random.choice(list(cls.colors.items()))

        return cls(
            color=color[0],
            colorLighter=color[1],
            colorDarker=color[2],
            menuSvg='assets/images/{}/menu.svg'.format(name),
            infoSvg='assets/images/{}/info.svg'.format(name),
            downloadSvg='assets/images/{}/download.svg'.format(name),
            searchSvg='assets/images/{}/search.svg'.format(name),
            carrotSvg='assets/images/{}/carrot.svg'.format(name),
            timelineSvg='assets/images/{}/toggle.svg'.format(name),
            name=name,
            archive=archive,
        )

class BaseTemplateMixin:
    category: Optional[str] = None
    archive_request_class = ArchiveRequest

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs) # type: ignore
        if self.category:
            kwargs['category'] = self.category
        self.archive_request = self.archive_request_class(request=request, category=kwargs.get("category"), short_name=kwargs.get('short_name'))

    @property
    def params(self) -> QueryDict:
        return self.archive_request.params
    @property
    def final_expr(self) -> Optional[Expression]:
        return self.archive_request.final_expr
    @property
    def expr(self) -> Optional[Expression]:
        return self.archive_request.expr
    @property
    def constraint(self) -> Optional[str]:
        return self.archive_request.constraint
    @property
    def form(self) -> SearchForm:
        return self.archive_request.form
    @property
    def get_params(self) -> QueryDict:
        return self.archive_request.get_params
    @property
    def url_kwargs(self) -> Dict[str, Any]:
        return self.archive_request.url_kwargs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs) # type: ignore
        context.update(self.archive_request.common_context)
        return context

    @method_decorator(require_valid_archive)
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().dispatch(request, *args, **kwargs) # type: ignore

class BasePhotoTemplateMixin(BaseTemplateMixin):
    def get_queryset(self) -> PhotoQuerySet:
        return self.archive_request.get_photo_queryset()
