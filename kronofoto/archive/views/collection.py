from django.views.generic.edit import CreateView, FormView, DeleteView
from django.views.generic import ListView
from django.core.exceptions import PermissionDenied
from ..reverse import reverse
from django.http import QueryDict, HttpResponse, HttpResponseForbidden, HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.forms import formset_factory, Form
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .basetemplate import BaseTemplateMixin
from .base import ArchiveRequest
from django.db.models import QuerySet
from ..models.photo import Photo
from ..models.collection import Collection
from ..forms import AddToListForm, ListMemberForm, ListForm, CollectionForm
from django.views.generic.list import MultipleObjectTemplateResponseMixin, MultipleObjectMixin
from django.views.decorators.csrf import csrf_exempt
from typing import Any, Dict, List

def profile_view(request: HttpRequest, username: str) -> HttpResponse:
    context = ArchiveRequest(request=request).common_context
    context['profile_user'] = get_object_or_404(User.objects.all(), username=username)
    return TemplateResponse(request=request, context=context, template="archive/collection_list.html")

@login_required
def collections_view(request: HttpRequest) -> HttpResponse:
    assert not request.user.is_anonymous
    areq = ArchiveRequest(request=request)
    context = areq.common_context
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.owner = request.user
            instance.save()
        if areq.is_hx_request:
            context['form'] = CollectionForm()
            context['object_list'] = Collection.objects.filter(owner=request.user)
            context['profile_user'] = request.user
            return TemplateResponse(request=request, context=context, template="archive/components/collections.html")
        else:
            return HttpResponseRedirect(reverse("kronofoto:user-page", kwargs={"username": request.user.username}))
    else:
        context['form'] = CollectionForm()
        context['object_list'] = Collection.objects.filter(owner=request.user)
        context['profile_user'] = request.user
        return TemplateResponse(request=request, context=context, template="archive/collections.html")


class CollectionCreate(BaseTemplateMixin, LoginRequiredMixin, CreateView):
    model = Collection
    fields = ['name', ]

    def get_success_url(self) -> str:
        return reverse('kronofoto:user-page', args=[self.request.user.get_username()])

    def form_valid(self, form: Any) -> Any:
        form.instance.owner = self.request.user
        return super().form_valid(form)


class CollectionDelete(BaseTemplateMixin, LoginRequiredMixin, DeleteView): # type: ignore
    model = Collection

    def get_context_data(self, *args: Any, **kwargs: Any) -> Any:
        context = super().get_context_data(*args, **kwargs)
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

class NewList(FormView):
    form_class = ListForm

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
    template_name = 'archive/popup_collection_list.html'
    form_class = formset_factory(ListMemberForm, extra=0)

    def get_success_url(self) -> str:
        return reverse('kronofoto:popup-add-to-list', kwargs={'photo': self.kwargs['photo']})

    def get_queryset(self) -> QuerySet:
        return Collection.objects.filter(
            owner=self.request.user
        ).count_photo_instances(
            photo=self.kwargs['photo']
        ) if not self.request.user.is_anonymous else []

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

    def form_valid(self, form: Form) -> HttpResponse:
        if self.request.user.is_anonymous:
            return HttpResponseForbidden()
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
    template_name = 'archive/collection_create.html'
    form_class = AddToListForm

    def get_success_url(self) -> str:
        return self.photo.get_absolute_url(kwargs=self.url_kwargs, params=self.get_params)

    def get_form_kwargs(self) -> Dict[str, Any]:
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
        self.photo = get_object_or_404(Photo, id=self.kwargs['photo'])
        if self.request.user.is_anonymous:
            raise PermissionDenied
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
