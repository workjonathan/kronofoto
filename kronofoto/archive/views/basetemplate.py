from django.core.cache import cache
from django.urls import reverse
from django.templatetags.static import static
import random
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
        self.set_request(request)
        self.form = SearchForm(self.request.GET)
        self.expr = None
        if self.form.is_valid():
            try:
                self.expr = self.form.as_expression()
            except NoExpression:
                pass
        self.constraint_expr = None
        if 'constraint' in self.request.GET:
            constraint = self.request.GET['constraint']
            self.constraint_expr = Parser.tokenize(constraint).parse().shakeout()
        self.final_expr = None
        if self.expr and self.constraint_expr:
            self.final_expr = self.expr & self.constraint_expr
        else:
            self.final_expr = self.expr or self.constraint_expr

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        photo_count = cache.get('photo_count:')
        if not photo_count:
            photo_count = Photo.count()
            cache.set('photo_count:', photo_count)
        context['photo_count'] = photo_count
        context['grid_url'] = reverse('gridview')
        context['timeline_url'] = '#'
        context['grid_json_url'] = '#'
        context['timeline_json_url'] = '#'
        context['theme'] = random.choice(THEME)
        context['embed'] = 'embed' in self.request.GET
        return context
