from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage
from django.conf import settings
from django.db.models import Min, Count, Q
from bisect import bisect_left as bisect
import urllib
from .models import Photo, Collection, PrePublishPhoto, ScannedPhoto, PhotoVote
from django.contrib.auth.models import User
from .forms import TagForm, AddToListForm, RegisterUserForm, SearchForm
from django.utils.http import urlencode
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.template.loader import render_to_string
from django.contrib.staticfiles.storage import staticfiles_storage
import json

from django.views.generic import ListView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import login
from math import floor
from itertools import islice,chain

from .search.parser import Parser, UnexpectedParenthesis, ExpectedParenthesis, NoExpression
from .search import evaluate

from .token import UserEmailVerifier


class BaseTemplateMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['photo_count'] = Photo.count()
        return context


class VerifyToken(RedirectView):
    permanent = False
    pattern_name = 'random-image'
    verifier = UserEmailVerifier()

    def get_redirect_url(self, *args, **kwargs):
        user = self.verifier.verify_token(uid=kwargs['uid'], token=kwargs['token'])
        if user:
            login(self.request, user)
        return super().get_redirect_url()


class RegisterAccount(BaseTemplateMixin, FormView):
    form_class = RegisterUserForm
    template_name = 'archive/register.html'
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['RECAPTCHA_SITE_KEY'] = settings.GOOGLE_RECAPTCHA_SITE_KEY
        return context

    def user_is_human(self):
        recaptcha_response = self.request.POST.get('g-recaptcha-response')
        data = {
            'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response,
        }
        args = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request('https://www.google.com/recaptcha/api/siteverify', data=args)
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode())
        return result['success']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def form_valid(self, form):
        if self.user_is_human():
            form.create_user()
            self.success_url = reverse('email-sent')
        else:
            self.success_url = reverse('register-account')
        return super().form_valid(form)


class AddTagView(BaseTemplateMixin, LoginRequiredMixin, FormView):
    template_name = 'archive/add_tag.html'
    form_class = TagForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['photo'] = self.photo
        return context

    def dispatch(self, request, photo):
        self.photo = Photo.objects.get(id=Photo.accession2id(photo))
        self.success_url = self.photo.get_absolute_url()
        return super().dispatch(request)

    def form_valid(self, form):
        form.add_tag(self.photo, user=self.request.user)
        return super().form_valid(form)



class PrePublishPhotoList(PermissionRequiredMixin, ListView):
    model = PrePublishPhoto
    template_name = 'archive/publish_list.html'
    permission_required = ('archive.delete_prepublishphoto', 'archive.change_photo')


class PrePublishPhotoView(PermissionRequiredMixin, DetailView):
    template_name = 'archive/publish.html'
    model = PrePublishPhoto
    permission_required = ('archive.delete_prepublishphoto', 'archive.change_photo')


class PublishPhotoRedirect(PermissionRequiredMixin, RedirectView):
    permanent = False
    pattern_name = 'prepublishlist'
    publish = None
    permission_required = ('archive.delete_prepublishphoto', 'archive.change_photo')

    def get_redirect_url(self, *args, **kwargs):
        photo = get_object_or_404(PrePublishPhoto, id=kwargs['pk'])
        del kwargs['pk']
        photo.photo.is_published = self.publish
        photo.photo.save()
        photo.delete()
        return super().get_redirect_url(*args, **kwargs)


class UploadScannedImage(PermissionRequiredMixin, CreateView):
    model = ScannedPhoto
    fields = ['image', 'collection']
    template_name = 'archive/upload_photo.html'
    success_url = reverse_lazy('upload')
    permission_required = 'archive.add_scannedphoto'


class ReviewPhotos(PermissionRequiredMixin, ListView):
    model = ScannedPhoto
    template_name = 'archive/review_photos.html'
    permission_required = 'archive.add_photovote'

    def get_queryset(self):
        return ScannedPhoto.objects.filter(accepted=None)


class VoteOnPhoto(PermissionRequiredMixin, RedirectView):
    permanent = False
    pattern_name = 'review'
    infavor = None
    permission_required = 'archive.add_photovote'

    def get_redirect_url(self, *args, **kwargs):
        photo = get_object_or_404(ScannedPhoto, id=kwargs['pk'])
        del kwargs['pk']
        vote, created = PhotoVote.objects.update_or_create(
            photo=photo, voter=self.request.user, defaults={'infavor': self.infavor}
        )
        return super().get_redirect_url(*args, **kwargs)


class ApprovePhoto(PermissionRequiredMixin, RedirectView):
    permanent = False
    pattern_name = 'review'
    approve = None
    permission_required = 'archive.change_scannedphoto'

    def get_redirect_url(self, *args, **kwargs):
        photo = get_object_or_404(ScannedPhoto, id=kwargs['pk'])
        del kwargs['pk']
        photo.accepted = self.approve
        photo.save()
        PhotoVote.objects.filter(photo=photo).delete()
        return super().get_redirect_url(*args, **kwargs)


class FrontPage(RedirectView):
    permanent = False
    pattern_name = 'photoview'

    def get_redirect_url(self, *args, **kwargs):
        photo = Photo.objects.filter_photos(self.request.GET, self.request.user).order_by('?')[0]
        return photo.get_absolute_url()


class Keyframes(TemplateView):
    template_name = "archive/keyframes.css"
    content_type = 'text/css'
    def get_context_data(self, origin, difference, step, unit):
        context = super().get_context_data()
        animations = []
        for i in range(0, difference, step):
            animations.append({'from': origin-i, 'to': origin-difference})
            animations.append({'from': origin+i, 'to': origin+difference})
        context['keyframes'] = animations
        context['unit'] = unit
        return context


class JSONResponseMixin:
    def render_to_json_response(self, context, **response_kwargs):
        return JsonResponse(self.get_data(context), **response_kwargs)

    def get_data(self, context):
        return context


class TimelinePaginator(Paginator):
    def get_page(self, number):
        try:
            page = super().page(number)
            for item in page:
                item.page = page
            return page
        except EmptyPage:
            return []


class PhotoView(JSONResponseMixin, BaseTemplateMixin, TemplateView):
    template_name = "archive/photo.html"

    def get_queryset(self):
        return Photo.objects.filter_photos(self.request.GET, self.request.user)

    def get_context_data(self, page, photo):
        context = super(PhotoView, self).get_context_data()
        queryset = self.get_queryset()
        year_index = queryset.year_index()
        years = [p.year for p in year_index]
        allyears = [(year, year_index[bisect(years, year)]) for year in range(years[0], years[-1]+1)]
        index = [(year, photo.get_absolute_url(params=self.request.GET), photo.get_json_url(params=self.request.GET)) for (year, photo) in allyears]

        items = 10
        paginator = TimelinePaginator(queryset.order_by('year', 'id'), items)
        this_page = paginator.get_page(page)
        prev_page = paginator.get_page(page-1)
        next_page = paginator.get_page(page+1)
        photo_rec = None
        for p in this_page:
            if p.accession_number == photo:
                p.active = True
                photo_rec = p
                break

        if photo_rec is None:
            try:
                photo = Photo.objects.get(id=Photo.accession2id(photo))
                self.redirect = redirect(photo.get_absolute_url(queryset=queryset, params=self.request.GET))
            except Photo.DoesNotExist:
                raise Http404("Photo either does not exist or is not in that set of photos")

        last = None
        for p in chain(prev_page, this_page, next_page):
            p.save_params(self.request.GET)
            if last:
                p.previous = last
                last.next = p
            last = p

        context["page"] = this_page
        context["next_page"] = next_page
        context["prev_page"] = prev_page
        context["photo"] = photo_rec
        context["years"] = index
        context["getparams"] = self.request.GET.urlencode()
        context['initialstate'] = self.get_data(context)
        return context

    def get_data(self, context):
        if 'photo' not in context or not context['photo']:
            return {}
        photo = context['photo']
        return {
            'url': photo.get_absolute_url(),
            'h700': photo.h700.url,
            'metadata': render_to_string('archive/photometadata.html', context),
            'thumbnails': render_to_string('archive/thumbnails.html', context),
            'backward': context['prev_page'][0].get_urls() if context['page'].has_previous() else {},
            'forward': context['next_page'][0].get_urls() if context['page'].has_next() else {},
            'previous': photo.previous.get_urls() if hasattr(photo, 'previous') else {},
            'next': photo.next.get_urls() if hasattr(photo, 'next') else {},
        }

    def render(self, context, **kwargs):
        return super().render_to_response(context, **kwargs)

    def render_to_response(self, context, **kwargs):
        if hasattr(self, "redirect"):
            return self.redirect
        return self.render(context, **kwargs)


class JSONPhotoView(PhotoView):
    def render(self, context, **kwargs):
        return self.render_to_json_response(context, **kwargs)


class GridBase(BaseTemplateMixin, ListView):
    model = Photo
    paginate_by = 50
    template_name = 'archive/photo_grid.html'

    def get_paginate_by(self, qs):
        return self.request.GET.get('display', self.paginate_by)

    def render_to_response(self, context, **kwargs):
        if hasattr(self, 'redirect'):
            return self.redirect
        return super().render_to_response(context, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        self.attach_params(page_obj)
        paginator = context['paginator']
        links = [{'label': label} for label in ['First', 'Previous', 'Next', 'Last']]
        if page_obj.number != 1:
            links[0]['url'] = self.format_page_url(1)
            links[1]['url'] = self.format_page_url(page_obj.previous_page_number())
        if page_obj.has_next():
            links[2]['url'] = self.format_page_url(page_obj.next_page_number())
        if page_obj.number != paginator.num_pages:
            links[3]['url'] = self.format_page_url(paginator.num_pages)
        context['links'] = links
        return context


class GridView(GridBase):
    def get_queryset(self):
        qs = self.model.objects.filter_photos(
            self.request.GET, self.request.user
        ).order_by('year', 'id')
        if qs.count() == 1:
            self.redirect = redirect(qs[0].get_absolute_url())
        return qs

    def format_page_url(self, num):
        return "{}?{}".format(reverse('gridview', args=(num,)), self.request.GET.urlencode())

    def attach_params(self, photos):
        params = self.request.GET.copy()
        if 'display' in params:
            params.pop('display')
        for photo in photos:
            photo.save_params(params=params)


class SearchResultsView(GridBase):
    def format_page_url(self, num):
        params = self.request.GET.copy()
        params['page'] = num
        return "{}?{}".format(reverse('search-results'), params.urlencode())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search-form'] = self.form
        return context

    def attach_params(self, photos):
        pass

    def get_queryset(self):
        self.form = SearchForm(self.request.GET)
        form = self.form

        if form.is_valid():
            try:
                expr = form.as_expression()
                qs = evaluate(expr, self.model.objects)
                if qs.count() == 1:
                    self.redirect = redirect(qs[0].get_absolute_url())
                return qs
            except NoExpression:
                return []


class Profile(BaseTemplateMixin, ListView):
    model = Collection
    template_name = 'archive/user_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
    template_name = 'archive/collection_create.html'

    def get_success_url(self):
        return reverse('user-page', args=[self.request.user.get_username()])

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class CollectionDelete(BaseTemplateMixin, LoginRequiredMixin, DeleteView):
    model = Collection
    template_name = 'archive/collection_delete.html'

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
