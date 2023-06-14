from django.test import Client, RequestFactory, SimpleTestCase
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.core.exceptions import SuspiciousOperation
from django.contrib.auth.models import AnonymousUser
from archive.views.basetemplate import BaseTemplateMixin, BasePhotoTemplateMixin
from unittest.mock import Mock, sentinel
from .util import searchTerms, photos, donors
from archive.forms import SearchForm
from archive.models.photo import Photo
from archive.search.expression import YearEquals, Caption

class Base:
    def setup(self, request, *args, **kwargs):
        self.request = request
        self.kwargs = kwargs

    def get_context_data(self, **kwargs):
        return {}

    def dispatch(self, *args, **kwargs):
        return {}

class Template(BasePhotoTemplateMixin, Base):
    pass

class DbTests(TestCase):


    def test_setup(self):
        request = RequestFactory().get('/')
        template = Template()
        template.filter_params = Mock(return_value={})
        template.get_final_expr = Mock(return_value=None)

        template.setup(request, photo=1)
        assert hasattr(template, 'get_params')
        assert hasattr(template, 'form')
        assert hasattr(template, 'url_kwargs')

    def test_setup_search(self):
        request = RequestFactory().get('/')
        template = Template()
        template.filter_params = Mock(return_value={})

        expr = Mock()
        expr.is_collection = Mock(return_value=False)

        template.get_final_expr = Mock(return_value=expr)

        template.setup(request, photo=1)
        assert len(template.get_params) == 0
        assert hasattr(template, 'form')
        assert hasattr(template, 'url_kwargs')

    def test_get_context_data(self):
        request = RequestFactory().get('/')
        template = Template()
        template.get_collection_name = Mock(return_value={})
        template.get_hx_context = Mock(return_value={})
        template.request = request
        template.get_params = sentinel.get_params
        template.form = sentinel.form
        template.constraint = None
        template.url_kwargs = sentinel.url_kwargs
        template.expr = None
        context = template.get_context_data()
        assert context['get_params'] == sentinel.get_params
        assert context['search-form'] == sentinel.form
        assert context['url_kwargs'] == sentinel.url_kwargs


    def test_invalid_form(self):
        template = Template()
        template.form = SearchForm(data={'term': 'invalid'})
        with self.assertRaises(SuspiciousOperation):
            template.get_queryset()

    @given(expr1=st.none() | searchTerms, expr2=st.none() | searchTerms)
    def test_final_expr(self, expr1, expr2):
        # would be nice to generate two and verify get_final_expr(a, b) == get_final_expr(b, a)
        # need to generate a photo with it
        template = Template()
        expr3 = template.get_final_expr(expr1, expr2)
        if expr1 and expr2:
            assert expr3 == expr1 & expr2
        elif expr1:
            assert expr3 == expr1
        else:
            assert expr3 == expr2

class Tests(SimpleTestCase):
    def test_collection_name(self):
        template = Template()
        assert template.get_collection_name(None) == {'collection_name': "All Photos"}
        assert template.get_collection_name(YearEquals(1950)) == {'collection_name': "from 1950"}
        assert template.get_collection_name(Caption('1950')) == {'collection_name': "Search Results"}

    @given(params=st.dictionaries(st.text(), st.text()), removals=st.lists(st.text()))
    def test_filter_params(self, params, removals):
        template = Template()
        params = template.filter_params(params, removals)
        for k in removals:
            assert k not in params

    @given(s=st.text())
    def test_constraint_parse(self, s):
        template = Template()
        try:
            expr = template.get_constraint_expr(s)
        except SuspiciousOperation:
            pass

    def test_hx_context(self):
        template = Template()
        request = RequestFactory().get('/')
        template.request = request
        assert template.get_hx_context() == {'base_template': 'archive/base.html'}
        request = RequestFactory().get('/', HTTP_HX_REQUEST="true")
        template.request = request
        assert template.get_hx_context() == {'base_template': 'archive/base_partial.html'}
        request = RequestFactory().get('/', HTTP_EMBEDDED="true")
        template.request = request
        assert template.get_hx_context() == {'base_template': 'archive/embedded-base.html'}

    def test_dispatch(self):
        template = Template()
        request = RequestFactory().get('/')
        assert template.dispatch(None)['Access-Control-Allow-Origin'] == '*'

    def test_get_queryset(self):
        template = Template()
        template.form = Mock()
        template.form.is_valid = Mock(return_value=True)
        template.model = Photo
        template.final_expr = None
        template.kwargs = {}
        template.get_queryset()

    def test_get_queryset_search(self):
        template = Template()
        request = RequestFactory().get('/')
        request.user = sentinel.user
        template.request = request
        template.form = Mock()
        template.form.is_valid = Mock(return_value=True)
        template.kwargs = {}
        template.model = Photo
        template.final_expr = Mock()
        template.final_expr.is_collection = Mock(return_value=False)
        template.final_expr.as_search = Mock(return_value=sentinel.results)

        qs = template.get_queryset()
        assert qs == sentinel.results

    def test_get_queryset_collection(self):
        template = Template()
        request = RequestFactory().get('/')
        request.user = sentinel.user
        template.request = request
        template.form = Mock()
        template.form.is_valid = Mock(return_value=True)
        template.kwargs = {}
        template.model = Photo
        template.final_expr = Mock()
        template.final_expr.is_collection = Mock(return_value=True)
        template.final_expr.as_collection = Mock(return_value=sentinel.collection)

        qs = template.get_queryset()
        assert qs == sentinel.collection

    def test_get_queryset_subarchive(self):
        template = Template()
        template.form = Mock()
        template.form.is_valid = Mock(return_value=True)
        template.model = Photo
        template.final_expr = None
        template.kwargs = {'short_name': 'state'}
        qs = template.get_queryset()
        assert qs is not None

