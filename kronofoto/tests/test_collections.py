from fortepan_us.kronofoto.views.collection import UserPageRedirect, FormResponse, ListNullAction, ListSaver, CollectionPostBehaviorSelection, CollectionGetBehaviorSelection, CollectionBehaviorSelection
from fortepan_us.kronofoto.views.base import ArchiveRequest
from django.urls import reverse
from fortepan_us.kronofoto.forms import CollectionForm
from django.contrib.auth.models import User
from django.test import RequestFactory, Client
import pytest
from pytest_django.asserts import assertRedirects, assertTemplateUsed
from fortepan_us.kronofoto.models import Collection

@pytest.mark.django_db
def test_redirect():
    user = User.objects.create_user(username="username")
    response = UserPageRedirect(user=user).response
    assertRedirects(response, "//example.com/kf/users/username", fetch_redirect_response=False)

@pytest.mark.django_db
def test_formresponse():
    user = User.objects.create_user(username="username")
    factory = RequestFactory()
    request = factory.get("")
    response = FormResponse(request=request, user=user, template="template", context={}).response
    assert "form" in response.context_data
    assert "object_list" in response.context_data
    assert "profile_user" in response.context_data
    assert response.template_name == "template"

def test_nullaction():
    assert ListNullAction().save() is None

@pytest.mark.django_db
def test_saveaction():
    user = User.objects.create_user(username="username")
    form = CollectionForm({"name": "name"})
    assert form.is_valid()
    ListSaver(user=user, form=form).save()
    assert Collection.objects.count() == 1


@pytest.mark.django_db
def test_postbehavior():
    factory = RequestFactory()
    user = User.objects.create_user(username="username")
    request = factory.get("")
    behavior = CollectionPostBehaviorSelection(postdata={"name": "name"}, user=user, areq=ArchiveRequest(request))
    assert isinstance(behavior.saver(), ListSaver)
    assert isinstance(behavior.responder(request=request, user=user), UserPageRedirect)

@pytest.mark.django_db
def test_postinvalidhxbehavior():
    factory = RequestFactory()
    user = User.objects.create_user(username="username")
    request = factory.get("", headers={"Hx_request": "1"})
    behavior = CollectionPostBehaviorSelection(postdata={}, user=user, areq=ArchiveRequest(request))
    assert isinstance(behavior.saver(), ListNullAction)
    assert isinstance(behavior.responder(request=request, user=user), FormResponse)


@pytest.mark.django_db
def test_getbehavior():
    factory = RequestFactory()
    user = User.objects.create_user(username="username")
    request = factory.get("")
    behavior = CollectionGetBehaviorSelection(areq=ArchiveRequest(request))
    assert isinstance(behavior.saver(), ListNullAction)
    assert isinstance(behavior.responder(request=request, user=user), FormResponse)

@pytest.mark.django_db
def test_behavior():
    factory = RequestFactory()
    user = User.objects.create_user(username="username")
    request = factory.get("")
    behavior = CollectionBehaviorSelection()
    assert isinstance(behavior.behavior(request=request, user=user), CollectionGetBehaviorSelection)
    request = factory.post("")
    assert isinstance(behavior.behavior(request=request, user=user), CollectionPostBehaviorSelection)

@pytest.mark.django_db
def test_user_page():
    user = User.objects.create_user(username="username")
    client = Client()
    resp = client.get(reverse("kronofoto:user-page", kwargs={"username": "username"}))
    assert resp.status_code == 200

@pytest.mark.django_db
def test_collections_list():
    user = User.objects.create_user(username="username")
    client = Client()
    client.force_login(user)
    resp = client.get(reverse("kronofoto:collection-create"))
    assert resp.status_code == 200
