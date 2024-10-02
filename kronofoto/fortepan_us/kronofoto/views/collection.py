from django.views.generic.edit import CreateView, FormView, DeleteView
from django.views.generic import ListView
from fortepan_us.kronofoto.reverse import reverse
from django.http import QueryDict, HttpResponse, HttpRequest, HttpResponseForbidden
from django.forms import formset_factory, ModelForm, Form, BaseFormSet
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from .basetemplate import BaseTemplateMixin
from fortepan_us.kronofoto.models.photo import Photo
from django.db.models import QuerySet
from fortepan_us.kronofoto.models.collection import Collection
from fortepan_us.kronofoto.forms import AddToListForm, ListMemberForm, ListForm
from django.views.generic.list import MultipleObjectTemplateResponseMixin, MultipleObjectMixin
from django.views.decorators.csrf import csrf_exempt
from typing import Any, Dict, Collection as CollectionT, List


class Profile(BaseTemplateMixin, ListView):
    model = Collection
    template_name = 'kronofoto/pages/user-page.html' # any template is needed to prevent a 500 error

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['profile_user'] = User.objects.get(username=self.kwargs['username'])
        return context

    def get_queryset(self) -> QuerySet:
        if not self.request.user.is_anonymous and self.request.user.get_username() == self.kwargs['username']:
            return Collection.objects.filter(owner=self.request.user)
        else:
            user = get_object_or_404(User, username=self.kwargs['username'])
            return Collection.objects.filter(owner=user, visibility='PU')


class CollectionCreate(BaseTemplateMixin, LoginRequiredMixin, CreateView):
    model = Collection
    fields = ['name', 'visibility']
    template_name = 'kronofoto/pages/collection-create.html'

    def get_success_url(self) -> str:
        return reverse('kronofoto:user-page', args=[self.request.user.get_username()])

    def form_valid(self, form: ModelForm) -> HttpResponse:
        form.instance.owner = self.request.user
        return super().form_valid(form)


class CollectionDelete(BaseTemplateMixin, LoginRequiredMixin, DeleteView): # type: ignore
    model = Collection
    template_name = 'kronofoto/pages/collection-delete.html'

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        if 'view' not in context:
            context['view'] = self
        return context

    def get_success_url(self) -> str:
        return reverse('kronofoto:user-page', args=[self.request.user.get_username()])

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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
        assert not self.request.user.is_anonymous
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
                collection = Collection.objects.get(id=data['collection'], owner=self.request.user)
                if data['membership']:
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
