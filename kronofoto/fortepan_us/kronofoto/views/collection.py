from django.views.generic.edit import CreateView, FormView, DeleteView
from django.views.generic import ListView
from django.core.exceptions import PermissionDenied
from django.utils.html import escape
from fortepan_us.kronofoto.reverse import reverse
from django.views.decorators.http import require_http_methods
from django.http import QueryDict, HttpResponse, HttpResponseForbidden, HttpRequest, HttpResponseRedirect
from fortepan_us.kronofoto.reverse import reverse
from django.template.response import TemplateResponse
from django.forms import formset_factory, ModelForm, Form, BaseFormSet
from django.shortcuts import get_object_or_404
from fortepan_us.kronofoto.templatetags import widgets
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .basetemplate import BaseTemplateMixin
from .base import ArchiveRequest
from django.db.models import QuerySet, Exists, OuterRef
from fortepan_us.kronofoto.forms import AddToListForm, ListMemberForm, ListForm, CollectionForm, ListVisibilityForm
from fortepan_us.kronofoto.models import Photo, Exhibit, Collection
from django.views.generic.list import MultipleObjectTemplateResponseMixin, MultipleObjectMixin
from django.views.decorators.csrf import csrf_exempt
from dataclasses import dataclass
from typing import Any, Dict, Collection as CollectionT, List, Protocol, Callable, Type, Union
from .exhibit import ExhibitCreateForm

@login_required
def embed(request: HttpRequest, pk: int) -> HttpResponse:
    collection = get_object_or_404(Collection.objects.all(), id=pk, owner=request.user)
    context = ArchiveRequest(request=request).common_context
    context["constraint"] = "collection:{}".format(collection.uuid)
    context['collection'] = collection
    return TemplateResponse(
        request=request,
        context=context,
        template="kronofoto/pages/collection-embed.html",
    )

def profile_view(request: HttpRequest, username: str) -> HttpResponse:
    context = ArchiveRequest(request=request).common_context
    profile_user = get_object_or_404(User.objects.all(), username=username)
    context['profile_user'] = profile_user
    if not request.user.is_anonymous and request.user.id == profile_user.id:
        context['form'] = CollectionForm()
        context['exhibit_form'] = ExhibitCreateForm()
        context['exhibit_form'].fields['collection'].queryset = Collection.objects.filter(owner=request.user).filter(Exists(Photo.objects.filter(collection__id=OuterRef("id"))))
    return TemplateResponse(request=request, context=context, template="kronofoto/pages/user-page.html")

def collection_view(request: HttpRequest, pk: int) -> HttpResponse:
    assert not request.user.is_anonymous
    collection = get_object_or_404(Collection.objects.all(), id=pk)
    if collection.owner != request.user:
        return HttpResponseForbidden()
    else:
        context = ArchiveRequest(request=request).common_context
        context['collection'] = collection
        context['visibility_form'] = ListVisibilityForm(initial={'is_private': collection.visibility != "PU"})
        return TemplateResponse(request=request, context=context, template="kronofoto/pages/collection-edit.html")

class Responder(Protocol):
    @property
    def response(self) -> HttpResponse: ...

@dataclass
class UserPageRedirect:
    user: User

    @property
    def response(self) -> HttpResponse:
        return HttpResponseRedirect(reverse("kronofoto:user-page", kwargs={"username": self.user.username}))

@dataclass
class FormResponse:
    request: HttpRequest
    user: User
    template: str
    context: Union[widgets.UserContentListContext, Dict[str, Any]]

    form_class: Callable[[], CollectionForm] = CollectionForm

    @property
    def response(self) -> HttpResponse:
        self.context['form'] = self.form_class()
        self.context['object_list'] = Collection.objects.by_user(user=self.user)
        self.context['profile_user'] = self.user
        return TemplateResponse(request=self.request, context={**self.context}, template=self.template)

class ListNullAction:
    def save(self) -> None:
        pass

@dataclass
class ListSaver(ListNullAction):
    form: CollectionForm
    user: User

    def save(self) -> None:
        instance = self.form.save(commit=False)
        instance.owner = self.user
        instance.visibility = "PU"
        instance.save()

class BehaviorSelection(Protocol):
    def saver(self) -> ListNullAction: ...
    def responder(self, *, request: HttpRequest, user: User) -> Responder: ...


@dataclass
class CollectionPostBehaviorSelection:
    postdata: QueryDict
    user: User
    areq: ArchiveRequest
    def saver(self) -> ListNullAction:
        form = CollectionForm(self.postdata)
        if form.is_valid():
            return ListSaver(user=self.user, form=form)
        else:
            return ListNullAction()

    def responder(self, *, request: HttpRequest, user: User) -> Responder:
        if self.areq.is_hx_request:
            template = "kronofoto/components/user-content-section.html"
            return FormResponse(request=request, user=user, template=template, context=widgets.collections(user=user, profile_user=user, form=CollectionForm()))
        else:
            return UserPageRedirect(user=user)

@dataclass
class CollectionGetBehaviorSelection:
    areq: ArchiveRequest
    def saver(self) -> ListNullAction:
        return ListNullAction()

    def responder(self, *, request: HttpRequest, user: User) -> Responder:
        template = "kronofoto/pages/collection-create.html"
        responder = FormResponse(request=request, user=user, template=template, context=self.areq.common_context)
        return responder

class CollectionBehaviorSelection:
    def behavior(self, *, request: HttpRequest, user: User) -> BehaviorSelection:
        areq = ArchiveRequest(request=request)
        if request.method == "POST":
            return CollectionPostBehaviorSelection(postdata=request.POST, user=user, areq=areq)
        else:
            return CollectionGetBehaviorSelection(areq=areq)


@require_http_methods(["POST"])
@login_required
def change_name(request: HttpRequest, pk: int) -> HttpResponse:
    assert not request.user.is_anonymous
    collections = Collection.objects.filter(owner__id=request.user.id, pk=pk)
    if 'collection-name' in request.POST and len(request.POST['collection-name'].strip()) > 0:
        name = request.POST['collection-name']
        collections.update(name=name)
    for c in collections:
        return HttpResponse(escape(c.name))
    return HttpResponse("forbidden", status=403)

@require_http_methods(["POST"])
@login_required
def change_visibility(request: HttpRequest, pk: int) -> HttpResponse:
    assert not request.user.is_anonymous
    areq = ArchiveRequest(request)
    collection = get_object_or_404(Collection.objects.all(), owner=request.user, id=pk)
    form = ListVisibilityForm(request.POST)
    if form.is_valid():
        collection.visibility = "PR" if form.cleaned_data['is_private'] else "PU"
        collection.save()
    context = areq.common_context
    context['collection'] = collection
    context['visibility_form'] = form
    if areq.is_hx_request:
        return TemplateResponse(request=request, template="kronofoto/pages/collection-edit.html", context=context)
    else:
        return HttpResponseRedirect(reverse("kronofoto:collection-edit", kwargs={'pk':pk}))


@require_http_methods(["POST"])
@login_required
def remove(request: HttpRequest, pk: int, photo: int) -> HttpResponse:
    areq = ArchiveRequest(request)
    assert not request.user.is_anonymous
    collection = get_object_or_404(Collection.objects.all(), owner=request.user, id=pk)
    relations = Collection.photos.through.objects.filter(collection__owner=request.user, collection__id=pk, photo__id=photo)
    if 'choice' in request.POST and request.POST['choice'] == 'Yes':
        relations.delete()
    context = areq.common_context
    context['collection'] = collection
    context['visibility_form'] = ListVisibilityForm(initial={'is_private': collection.visibility != "PU"})
    if areq.is_hx_request:
        return TemplateResponse(request=request, template="kronofoto/pages/collection-edit.html", context=context)
    else:
        return HttpResponseRedirect(reverse("kronofoto:collection-edit", kwargs={'pk':pk}))

@login_required
def collections_view(
    request: HttpRequest,
    behavior_class: Type[CollectionBehaviorSelection]=CollectionBehaviorSelection,
) -> HttpResponse:
    assert not request.user.is_anonymous
    behavior = behavior_class().behavior(request=request, user=request.user)
    saver = behavior.saver()
    responder = behavior.responder(request=request, user=request.user)
    saver.save()
    return responder.response


class CollectionDelete(BaseTemplateMixin, LoginRequiredMixin, DeleteView): # type: ignore
    model = Collection
    template_name = 'kronofoto/pages/collection-delete.html'

    def get_context_data(self, *args: Any, **kwargs: Any) -> Any:
        context = super().get_context_data(*args, **kwargs)
        assert not self.request.user.is_anonymous
        context['profile_user'] = self.request.user
        context['exhibit_form'] = ExhibitCreateForm()
        context['exhibit_form'].fields['collection'].queryset = Collection.objects.filter(owner=self.request.user).filter(Exists(Photo.objects.filter(collection__id=OuterRef("id"))))
        context['exhibits'] = Exhibit.objects.filter(owner=self.request.user)
        if 'view' not in context:
            context['view'] = self
        return context

    def get_success_url(self) -> Any:
        return reverse('kronofoto:user-page', args=[self.request.user.get_username()])

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        obj = self.get_object()
        if obj.owner != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

class NewList(LoginRequiredMixin, FormView):
    form_class = ListForm
    template_name = 'kronofoto/components/popups/collections.html' # any template is needed to prevent a 500 error

    def get_success_url(self) -> str:
        return reverse('kronofoto:popup-add-to-list', kwargs={'photo': self.kwargs['photo']})

    def form_valid(self, form: Form) -> HttpResponse:
        if self.request.user.is_anonymous:
            return HttpResponseForbidden()
        collection = Collection.objects.create(
            name=form.cleaned_data['name'],
            owner=self.request.user,
            visibility='PR' if form.cleaned_data['is_private'] else 'PU',
        )
        collection.photos.add(self.kwargs['photo'])
        return super().form_valid(form)

class ListMembers(MultipleObjectTemplateResponseMixin, MultipleObjectMixin, FormView):
    template_name = 'kronofoto/components/popups/collections.html'
    form_class = formset_factory(ListMemberForm, extra=0)

    def get_success_url(self) -> str:
        return reverse('kronofoto:popup-add-to-list', kwargs={'photo': self.kwargs['photo']})

    def post(self, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            return super().post(*args, **kwargs)
        except TypeError:
            return HttpResponse("", status=400)

    def get_queryset(self) -> Any:
        return Collection.objects.filter(
            owner=self.request.user
        ).count_photo_instances(
            photo=self.kwargs['photo']
        ) if not self.request.user.is_anonymous else Collection.objects.filter(id__in=[])

    def get_initial(self) -> Any:
        return [
            {
                'membership': bool(o.membership),
                'collection': o.id,
                'name': o.name,
                'photo': self.kwargs['photo'],
            }
            for o in self.get_queryset()
        ]

    def form_valid(self, form: BaseFormSet) -> HttpResponse:
        if self.request.user.is_anonymous:
            return HttpResponse(400)
        for data in form.cleaned_data:
            try:
                collection = Collection.objects.get(id=data['collection'], owner=self.request.user) # type: ignore
                if data['membership']: # type: ignore
                    collection.photos.add(self.kwargs['photo'])
                else:
                    collection.photos.remove(self.kwargs['photo'])
            except Collection.DoesNotExist:
                pass
        return super().form_valid(form)

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        context['new_list_form'] = ListForm()
        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.object_list = self.get_queryset()
        return super().get(request, *args, **kwargs)


class AddToList(BaseTemplateMixin, LoginRequiredMixin, FormView):
    template_name = 'kronofoto/pages/collection-create.html'
    form_class = AddToListForm

    def get_success_url(self) -> str:
        return self.photo.get_absolute_url(kwargs=self.url_kwargs, params=self.get_params)

    def get_form_kwargs(self) -> Dict[str, Any]:
        assert not self.request.user.is_anonymous
        kwargs = super().get_form_kwargs()
        if self.request.user.is_anonymous:
            raise PermissionDenied
        kwargs['collections'] = [
            (collection.id, collection.name)
            for collection in Collection.objects.filter(owner=self.request.user)
        ]
        kwargs['collections'].append((None, 'New List'))
        return kwargs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['photo'] = get_object_or_404(Photo, id=self.kwargs['photo'])
        return context

    def form_valid(self, form: Form) -> HttpResponse:
        assert not self.request.user.is_anonymous
        if isinstance(self.kwargs['photo'], int):
            self.photo = get_object_or_404(Photo, id=self.kwargs['photo'])
        else:
            self.photo = get_object_or_404(
                Photo, id=Photo.accession2id(self.kwargs['photo'])
            )
        if form.cleaned_data['collection']:
            collection = get_object_or_404(
                Collection, id=form.cleaned_data['collection']
            )
            if collection.owner == self.request.user:
                collection.photos.add(self.photo)
        elif form.cleaned_data['name']:
            collection = Collection.objects.create(
                name=form.cleaned_data['name'],
                owner=self.request.user,
                visibility=form.cleaned_data['visibility'],
            )
            collection.photos.add(self.photo)
        return super().form_valid(form)
