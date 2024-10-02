from django.test import Client, RequestFactory, SimpleTestCase
from django.http import QueryDict
from hypothesis.extra.django import from_model, register_field_strategy, TestCase
from hypothesis import strategies as st, given, note, settings
from unittest.mock import Mock, sentinel, MagicMock
from fortepan_us.kronofoto.views.grid import GridView
from fortepan_us.kronofoto.models.archive import Archive
from fortepan_us.kronofoto.forms import SearchForm
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

    def test_no_objects_context_match(self):
        view = GridView()
        view.request = RequestFactory().get('/')
        view.request.user = sentinel.user
        objects = Mock()
        objects.exists = Mock(return_value=True)
        context = view.get_no_objects_context(objects)
        assert not context['noresults']

