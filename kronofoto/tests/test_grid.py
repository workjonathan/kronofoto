from django.test import Client, RequestFactory, SimpleTestCase
from django.http import QueryDict
from hypothesis.extra.django import from_model, register_field_strategy, TestCase
from hypothesis import strategies as st, given, note, settings
from unittest.mock import Mock, sentinel, MagicMock
from archive.views.grid import GridView
from archive.models.archive import Archive
from archive.forms import SearchForm
from dataclasses import dataclass

@dataclass
class TestPhoto:
    year: int
    id: int

class Tests(TestCase):
    def test_grid_url(self):
        resp = GridView.as_view(
            get_no_objects_context=Mock(return_value={})
        )(RequestFactory().get('/photos'))
        assert resp.status_code == 200
        assert 'collection_name' in resp.context_data
        assert 'page_obj' in resp.context_data

    def test_no_objects_context_no_match_silly_available(self):
        view = GridView()
        view.request = RequestFactory().get('/')
        view.request.user = sentinel.user
        view.final_expr = "expr"
        photo = Mock()
        photo.get_accepted_tags = Mock(return_value=sentinel.tags)
        view.get_no_objects_queryset = Mock(return_value=[photo])
        objects = Mock()
        objects.exists = Mock(return_value=False)
        context = view.get_no_objects_context(objects)
        assert context['noresults']
        assert context['oops_photo'] == photo
        assert context['tags'] == sentinel.tags

    def test_no_objects_context_no_match_silly_unavailable(self):
        view = GridView()
        view.request = RequestFactory().get('/')
        view.request.user = sentinel.user
        view.final_expr = "expr"
        objects = Mock()
        objects.exists = Mock(return_value=False)
        context = view.get_no_objects_context(objects)
        assert context['noresults']
        assert context['tags'] == []

    def test_no_objects_context_match(self):
        view = GridView()
        view.request = RequestFactory().get('/')
        view.request.user = sentinel.user
        objects = Mock()
        objects.exists = Mock(return_value=True)
        context = view.get_no_objects_context(objects)
        assert not context['noresults']

    def test_pagination_base(self):
        view = GridView()
        view.request = RequestFactory().get('/')
        view.kwargs = {}
        view.final_expr = Mock()
        view.final_expr.is_collection = Mock(return_value=False)
        view.paginate_queryset([], 2)

    def test_pagination_page(self):
        view = GridView()
        view.kwargs = {'page': 2}
        view.final_expr = None
        view.params = QueryDict(mutable=True)
        paginator = Mock()
        paginator.get_page = Mock(return_value=sentinel.page)
        view.create_keyset_paginator = Mock(return_value=paginator)
        queryset = []
        for x in range(10):
            queryset.append(TestPhoto(year=x+1900, id=x))
        p2, page, qs, _ = view.paginate_queryset(queryset, 2)
        assert page == sentinel.page
        paginator.get_page.assert_called_with({'year': 1902, "id": 2, "reverse": False})

    def test_pagination_gte(self):
        view = GridView()
        view.kwargs = {}
        view.final_expr = None
        view.params = QueryDict(mutable=True)
        view.params['year:gte'] = 1902
        view.params['id:gt'] = 2
        paginator = Mock()
        paginator.get_page = Mock(return_value=sentinel.page)
        view.create_keyset_paginator = Mock(return_value=paginator)
        p2, page, qs, _ = view.paginate_queryset([], 2)
        assert page == sentinel.page
        paginator.get_page.assert_called_with({'year': 1902, "id": 2, "reverse": False})

    def test_pagination_lte(self):
        view = GridView()
        view.kwargs = {}
        view.final_expr = None
        view.params = QueryDict(mutable=True)
        view.params['year:lte'] = 1902
        view.params['id:lt'] = 2
        paginator = Mock()
        paginator.get_page = Mock(return_value=[TestPhoto(year=1900, id=1)])
        view.create_keyset_paginator = Mock(return_value=paginator)
        p2, page, qs, _ = view.paginate_queryset([], 2)
        paginator.get_page.assert_any_call({'year': 1902, "id": 2, "reverse": True})
        paginator.get_page.assert_called_with({'year': 1900, "id": 0, "reverse": False})

