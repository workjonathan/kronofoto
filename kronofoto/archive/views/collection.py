from django.views.generic.edit import CreateView, FormView, DeleteView
from django.views.generic import ListView
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from .basetemplate import BaseTemplateMixin
from ..models.photo import Photo
from ..models.collection import Collection
from ..forms import AddToListForm


class Profile(BaseTemplateMixin, ListView):
    model = Collection

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile_user'] = User.objects.get(username=self.kwargs['username'])
        return context

    def get_queryset(self):
        if self.request.user.get_username() == self.kwargs['username']:
            return Collection.objects.filter(owner=self.request.user)
        else:
            user = get_object_or_404(User, username=self.kwargs['username'])
            return Collection.objects.filter(owner=user, visibility='PU')


class CollectionCreate(BaseTemplateMixin, LoginRequiredMixin, CreateView):
    model = Collection
    fields = ['name', 'visibility']

    def get_success_url(self):
        return reverse('user-page', args=[self.request.user.get_username()])

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class CollectionDelete(BaseTemplateMixin, LoginRequiredMixin, DeleteView):
    model = Collection

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if 'view' not in context:
            context['view'] = self
        return context

    def get_success_url(self):
        return reverse('user-page', args=[self.request.user.get_username()])

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.owner != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)


class AddToList(BaseTemplateMixin, LoginRequiredMixin, FormView):
    template_name = 'archive/collection_create.html'
    form_class = AddToListForm

    def get_success_url(self):
        return self.photo.get_absolute_url()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['collections'] = [
            (collection.id, collection.name)
            for collection in Collection.objects.filter(owner=self.request.user)
        ]
        kwargs['collections'].append((None, 'New List'))
        return kwargs

    def form_valid(self, form):
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
