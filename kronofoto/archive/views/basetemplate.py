from django.core.cache import cache
from django.urls import reverse
from django.conf import settings
from django.templatetags.static import static
import random
import json
from ..reverse import set_request
from ..forms import SearchForm
from ..search.parser import Parser, NoExpression
from ..models import Photo


THEME = [
    {
        'color': "#6c84bd",
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
        'logo': static("assets/images/haybail/logo.svg"),
        'menuSvg': static("assets/images/haybail/menu.svg"),
        'infoSvg': static("assets/images/haybail/info.svg"),
        'downloadSvg': static("assets/images/haybail/download.svg"),
        'searchSvg': static("assets/images/haybail/search.svg"),
        'carrotSvg': static("assets/images/haybail/carrot.svg"),
        "timelineSvg": static("assets/images/haybail/toggle.svg"),
    },
    {
        'color': "#445170",
        'logo': static("assets/images/navy/logo.svg"),
        'menuSvg': static("assets/images/navy/menu.svg"),
        'infoSvg': static("assets/images/navy/info.svg"),
        'downloadSvg': static("assets/images/navy/download.svg"),
        'searchSvg': static("assets/images/navy/search.svg"),
        'carrotSvg': static("assets/images/navy/carrot.svg"),
        "timelineSvg": static("assets/images/navy/toggle.svg"),
    }
]


class BaseTemplateMixin:
    def set_request(self, request):
        # By default, the request should not be globally available.
        set_request(None)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.params = self.request.GET.copy()
        get_params = self.params.copy()
        for key in ('id:lt', 'id:gt', 'page', 'year:gte', 'year:lte'):
            try:
                get_params.pop(key)
            except KeyError:
                pass
        self.get_params = get_params
        self.form = SearchForm(self.request.GET)
        self.url_kwargs = {'short_name': self.kwargs['short_name']} if 'short_name' in self.kwargs else {}
        self.expr = None
        if self.form.is_valid():
            try:
                self.expr = self.form.as_expression()
            except NoExpression:
                pass
        self.constraint = self.request.headers.get('Constraint', None)
        self.constraint_expr = None
        if self.constraint:
            self.constraint_expr = Parser.tokenize(self.constraint).parse().shakeout()
        self.final_expr = None
        if self.expr and self.constraint_expr:
            self.final_expr = self.expr & self.constraint_expr
        else:
            self.final_expr = self.expr or self.constraint_expr

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        photo_count = cache.get('photo_count:')
        context['get_params'] = self.get_params
        context['search-form'] = self.form
        context['constraint'] = json.dumps({'Constraint': self.constraint})
        context['url_kwargs'] = self.url_kwargs
        if self.expr:
            if self.expr.is_collection():
                context['collection_name'] = str(self.expr.description())
            else:
                context['collection_name'] = "Search Results"
        else:
            context['collection_name'] = 'All Photos'

        context['push-url'] = True
        if self.request.headers.get('Hx-Request', 'false') == 'true':
            context['base_template'] = 'archive/base_partial.html'
        elif self.request.headers.get('Embedded', 'false') != 'false':
            context['base_template'] = 'archive/embedded-base.html'
        else:
            context['base_template'] = 'archive/base.html'

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

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'constraint, embedded, hx-current-url, hx-request, hx-target, hx-trigger, us.fortepan.position'
        return response

class BasePhotoTemplateMixin(BaseTemplateMixin):
    def get_queryset(self):
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
