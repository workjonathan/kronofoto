from django.test import Client, RequestFactory, SimpleTestCase
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.core.exceptions import BadRequest
from django.contrib.auth.models import AnonymousUser
from fortepan_us.kronofoto.views.basetemplate import BaseTemplateMixin, BasePhotoTemplateMixin
from unittest.mock import Mock, sentinel
from .util import searchTerms, photos, donors
from fortepan_us.kronofoto.forms import SearchForm
from fortepan_us.kronofoto.models.photo import Photo
from fortepan_us.kronofoto.search.expression import YearEquals, Caption

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
