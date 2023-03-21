from hypothesis.extra.django import TestCase, from_model
from hypothesis import given, strategies as st, note
from django.test import RequestFactory, SimpleTestCase, Client
from django.urls import reverse
from ..views.collection import ListMembers
from django.contrib.auth.models import User, AnonymousUser
from ..models.collection import Collection
import pytest
from .util import photos

class TestLists(TestCase):
    @given(from_model(Collection.photos.through, collection=from_model(Collection), photo=photos()), st.integers(min_value=1, max_value=100))
    def test_CollectionQuerySet(self, _, photo_id):
        note(f'{_.photo=} {_.collection=}')
        Collection.objects.count_photo_instances(photo=photo_id)

    @given(
        st.lists(from_model(User), min_size=1, max_size=3).flatmap(lambda users:
        st.lists(from_model(Collection, owner=st.sampled_from(users)), max_size=5).flatmap(lambda _:
        st.one_of(st.just(users[0]), st.just(AnonymousUser))
    )))
    def test_queryset(self, user):
        request = RequestFactory().get(reverse('kronofoto:popup-add-to-list', kwargs={'photo': 1}))
        request.user = user
        listview = ListMembers()
        listview.setup(request, photo=1)
        qs = listview.get_queryset()

    @pytest.mark.django_db
    def test_template(self):
        resp = Client().get(reverse('kronofoto:popup-add-to-list', kwargs={'photo': 1}))
        self.assertTemplateUsed(resp, 'archive/popup_collection_list.html')
