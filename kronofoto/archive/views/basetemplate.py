from django.core.cache import cache
from django.http import QueryDict
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.templatetags.static import static
import random
import json
from ..reverse import set_request
from ..forms import SearchForm
from ..search.parser import Parser, NoExpression
from ..models import Photo
from functools import reduce
import operator


THEME = [
    {
        'color': "#6c84bd",
        'colorDarker': "",
        'colorLighter': "",
        "logo": static("assets/images/skyblue/logo.svg"),
        "menuSvg": static("assets/images/skyblue/menu.svg"),
        "infoSvg": static("assets/images/skyblue/info.svg"),
        "downloadSvg": static("assets/images/skyblue/download.svg"),
        "searchSvg": static("assets/images/skyblue/search.svg"),
        "carrotSvg": static("assets/images/skyblue/carrot.svg"),
        "timelineSvg": static("assets/images/skyblue/toggle.svg"),
    },
    {
        'color': "#c28800",
        'colorDarker': "",
        'colorLighter': "",
        'logo': static("assets/images/golden/logo.svg"),
        'menuSvg': static("assets/images/golden/menu.svg"),
        'infoSvg': static("assets/images/golden/info.svg"),
        'downloadSvg': static("assets/images/golden/download.svg"),
        'searchSvg': static("assets/images/golden/search.svg"),
        'carrotSvg': static("assets/images/golden/carrot.svg"),
        "timelineSvg": static("assets/images/golden/toggle.svg"),
    },
    {
        'color': "#c2a55e",
        'colorDarker': "",
        'colorLighter': "",
        'logo': static("assets/images/haybail/logo.svg"),
        'menuSvg': static("assets/images/haybail/menu.svg"),
        'infoSvg': static("assets/images/haybail/info.svg"),
        'downloadSvg': static("assets/images/haybail/download.svg"),
        'searchSvg': static("assets/images/haybail/search.svg"),
        'carrotSvg': static("assets/images/haybail/carrot.svg"),
        "timelineSvg": static("assets/images/haybail/toggle.svg"),
    }
]

class BasePermissiveCORSMixin:
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'constraint, embedded, hx-current-url, hx-request, hx-target, hx-trigger, us.fortepan.position'
        return response

class BaseTemplateMixin(BasePermissiveCORSMixin):
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
            context['base_template'] = 'archive/base.html'
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
        context['theme'] = random.choice(THEME)
        hxheaders = dict()
        hxheaders['Constraint'] = self.request.headers.get('Constraint', None)
        hxheaders['Embedded'] = self.request.headers.get('Embedded', 'false')
        context['hxheaders'] = json.dumps(hxheaders)
        return context


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
