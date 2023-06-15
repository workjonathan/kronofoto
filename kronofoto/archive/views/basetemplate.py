from django.core.cache import cache
from django.http import QueryDict
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.templatetags.static import static
from django.template.loader import select_template
import random
import json
from ..reverse import set_request
from ..forms import SearchForm
from ..search.parser import Parser, NoExpression
from ..models import Photo
from functools import reduce
import operator
from dataclasses import dataclass, replace

class ThemeDict(dict):
    def __missing__(self, key):
        return self['us']

@dataclass
class Theme:
    color: str
    logo: str
    menuSvg: str
    infoSvg: str
    downloadSvg: str
    searchSvg: str
    carrotSvg: str
    timelineSvg: str

    @classmethod
    def generate_themes(cls):
        # This is a very annoying feature, and this is unpleasantly non-general.
        colors = (
            ('skyblue', "#6c84bd"),
            ('golden', "#c28800"),
            ('haybail', "#c2a55e"),
            ('lakeblue', "#445170"), # was navy?
        )
        colors = {
            name: Theme(
                color=color,
                logo='assets/images/{}/logo.svg'.format(name),
                menuSvg='assets/images/{}/menu.svg'.format(name),
                infoSvg='assets/images/{}/info.svg'.format(name),
                downloadSvg='assets/images/{}/download.svg'.format(name),
                searchSvg='assets/images/{}/search.svg'.format(name),
                carrotSvg='assets/images/{}/carrot.svg'.format(name),
                timelineSvg='assets/images/{}/toggle.svg'.format(name),
            )
            for name, color in colors
        }
        themes = {
            archive: [
                replace(theme, logo='assets/images/{}/{}/logo.svg'.format(name, archive))
                for name, theme in colors.items()
            ]
            for archive in ('ia', 'ct')
        }
        themes['us'] = list(colors.values())
        return ThemeDict(themes)

THEME = Theme.generate_themes()

class BaseTemplateMixin:
    def set_request(self, request):
        # By default, the request should not be globally available.
        set_request(None)

    def filter_params(self, params, removals=('id:lt', 'id:gt', 'page', 'year:gte', 'year:lte')):
        get_params = params.copy()
        for key in removals:
            try:
                get_params.pop(key)
            except KeyError:
                pass
        return get_params

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.params = self.request.GET.copy()
        self.form = SearchForm(self.request.GET)
        self.url_kwargs = {'short_name': self.kwargs['short_name']} if 'short_name' in self.kwargs else {}
        self.expr = None
        if self.form.is_valid():
            try:
                self.expr = self.form.as_expression()
            except NoExpression:
                pass
        self.constraint = self.request.headers.get('Constraint', None)
        constraint_expr = self.get_constraint_expr(self.constraint)
        self.final_expr = self.get_final_expr(self.expr, constraint_expr)
        self.get_params = self.filter_params(self.params) if not self.final_expr or self.final_expr.is_collection() else QueryDict()

    def get_constraint_expr(self, constraint):
        if constraint:
            try:
                constraint_expr = Parser.tokenize(constraint).parse().shakeout()
            except:
                raise SuspiciousOperation("invalid constraint")
        return None

    def get_final_expr(self, *exprs):
        exprs = [expr for expr in exprs if expr]
        if exprs:
            return reduce(operator.__and__, exprs)
        return None

    def get_collection_name(self, expr):
        context = {}
        if expr:
            if expr.is_collection():
                context['collection_name'] = str(expr.description())
            else:
                context['collection_name'] = "Search Results"
        else:
            context['collection_name'] = 'All Photos'
        return context

    def get_hx_context(self):
        context = {}
        if self.request.headers.get('Hx-Request', 'false') == 'true':
            context['base_template'] = 'archive/base_partial.html'
        elif self.request.headers.get('Embedded', 'false') != 'false':
            context['base_template'] = 'archive/embedded-base.html'
        else:
            templates = []
            if 'short_name' in self.kwargs:
                templates.append('archive/base/{}.html'.format(self.kwargs['short_name']))
            templates.append('archive/base.html')
            context['base_template'] = select_template(templates)
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        photo_count = cache.get('photo_count:')
        context['get_params'] = self.get_params
        context['search-form'] = self.form
        context['constraint'] = json.dumps({'Constraint': self.constraint})
        context['url_kwargs'] = self.url_kwargs
        context.update(self.get_collection_name(self.expr))
        context.update(self.get_hx_context())

        context['push-url'] = True

        if not photo_count:
            photo_count = Photo.objects.filter(is_published=True).count()
            cache.set('photo_count:', photo_count)
        context['KF_DJANGOCMS_NAVIGATION'] = settings.KF_DJANGOCMS_NAVIGATION
        context['KF_DJANGOCMS_ROOT'] = settings.KF_DJANGOCMS_ROOT
        context['photo_count'] = photo_count
        context['timeline_url'] = '#'
        context['theme'] = random.choice(THEME[self.kwargs['short_name'] if 'short_name' in self.kwargs else 'us'])
        hxheaders = dict()
        hxheaders['Constraint'] = self.request.headers.get('Constraint', None)
        hxheaders['Embedded'] = self.request.headers.get('Embedded', 'false')
        context['hxheaders'] = json.dumps(hxheaders)
        return context

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'constraint, embedded, hx-current-url, hx-request, hx-target, hx-trigger, us.fortepan.position'
        return response

class BasePhotoTemplateMixin(BaseTemplateMixin):
    def get_queryset(self):
        if self.form.is_valid():
            expr = self.final_expr
            qs = self.model.objects.filter(is_published=True, year__isnull=False)
            if 'short_name' in self.kwargs:
                qs = qs.filter(archive__slug=self.kwargs['short_name'])
            if expr is None:
                return qs.order_by('year', 'id')

            if expr.is_collection():
                qs = expr.as_collection(qs, self.request.user)
            else:
                qs = expr.as_search(self.model.objects.filter(is_published=True), self.request.user)
            return qs
        else:
            raise SuspiciousOperation('invalid search request')

