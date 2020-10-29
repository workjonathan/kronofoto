from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, Page
from django.core.cache import cache
from django.conf import settings
from django.db.models import Min, Count, Q
import urllib
import os
import urllib.request
from .models import Photo, Collection, PrePublishPhoto, ScannedPhoto, PhotoVote, Term, Tag, Donor, CSVRecord, CollectionQuery
from django.contrib.auth.models import User
from .forms import TagForm, AddToListForm, RegisterUserForm, SearchForm
from django.utils.http import urlencode
from django.http import Http404, HttpResponseForbidden, JsonResponse, HttpResponseBadRequest, HttpResponse, QueryDict
from django.template.loader import render_to_string
from django.contrib.staticfiles.storage import staticfiles_storage
import json
from django.views.generic import ListView, TemplateView, View
from django.views.generic.list import BaseListView
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login
from math import floor
from itertools import islice,chain

from .search.parser import Parser, UnexpectedParenthesis, ExpectedParenthesis, NoExpression
from .search import evaluate

from .token import UserEmailVerifier


EMPTY_PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='

FAKE_PHOTO = dict(thumbnail=dict(url=EMPTY_PNG, height=75, width=75))

NO_URLS = dict(url='#', json_url='#')


class BaseTemplateMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        photo_count = cache.get('photo_count')
        if not photo_count:
            photo_count = Photo.count()
            cache.set('photo_count', photo_count)
        context['photo_count'] = photo_count
        context['grid_url'] = reverse('gridview')
        context['timeline_url'] = '#'
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
        context['tags'] = self.photo.get_accepted_tags(self.request.user)
        return context

    def dispatch(self, request, photo):
        self.photo = Photo.objects.get(id=Photo.accession2id(photo))
        self.success_url = reverse('addtag', kwargs={'photo': self.photo.accession_number})
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
        photo = Photo.objects.filter_photos(
            CollectionQuery(self.request.GET, self.request.user)
        ).order_by('?')[0]
        return photo.get_absolute_url()


class Keyframes(TemplateView):
    template_name = "archive/keyframes.css"
    content_type = 'text/css'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        origin = self.kwargs['origin']
        difference = self.kwargs['difference']
        step = self.kwargs['step']
        unit = self.kwargs['unit']
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


class FakeTimelinePage:
    def __iter__(self):
        yield from []

    object_list = [FAKE_PHOTO] * 10

class TimelinePage(Page):
    def find_accession_number(self, accession_number):
        for i, p in enumerate(self):
            if p.accession_number == accession_number:
                p.active = True
                p.row_number = self.start_index() + i - 1
                return p
        raise KeyError(accession_number)


class PageSelection:
    def __init__(self, pages):
        self.pages = pages

    def find_accession_number(self, accession_number):
        return self.main_page().find_accession_number(accession_number)

    def main_page(self):
        return self.pages[len(self.pages)//2]

    def photos(self):
        last = None
        for p in chain(*self.pages):
            yield p
            if last:
                p.previous = last
                last.next = p
            last = p


class TimelinePaginator(Paginator):
    def get_pageselection(self, pages):
        return PageSelection(pages)

    def get_pages(self, number, buffer=1):
        return PageSelection([self.get_page(n) for n in range(number-buffer, number+buffer+1)])

    def get_page(self, number):
        try:
            page = super().page(number)
            for item in page:
                item.page = page
            return page
        except EmptyPage:
            return FakeTimelinePage()

    def _get_page(self, *args, **kwargs):
        return TimelinePage(*args, **kwargs)


class PhotoView(JSONResponseMixin, BaseTemplateMixin, TemplateView):
    template_name = "archive/photo.html"
    items = 10
    _queryset = None

    @property
    def queryset(self):
        if self._queryset is None:
            self._queryset = self.get_queryset()
        return self._queryset

    def get_queryset(self):
        self.collection = CollectionQuery(self.request.GET, self.request.user)
        return Photo.objects.filter_photos(self.collection)

    def get_paginator(self):
        return TimelinePaginator(self.queryset.order_by('year', 'id'), self.items)

    def get_context_data(self, **kwargs):
        context = super(PhotoView, self).get_context_data(**kwargs)
        photo = self.kwargs['photo']
        if 'page' in self.kwargs:
            page = self.kwargs['page']
        else:
            page = 1
        queryset = self.queryset
        index_key = 'year_links:' + self.collection.cache_encoding()
        index = cache.get(index_key)
        if not index:
            index = queryset.year_links(params=self.request.GET)
            cache.set(index_key, index)

        paginator = self.get_paginator()
        page_selection = paginator.get_pages(page)

        try:
            photo_rec = page_selection.find_accession_number(photo)

            for p in page_selection.photos():
                p.save_params(self.request.GET)

            context['prev_page'], context["page"], context['next_page'] = page_selection.pages
            context['grid_url'] = photo_rec.get_grid_url()
            context["photo"] = photo_rec
            context["tags"] = photo_rec.get_accepted_tags(self.request.user)
            context["years"] = index
            context['initialstate'] = self.get_data(context)
            context['collection_name'] = str(self.collection)
            if self.request.user.is_staff and self.request.user.has_perm('archive.change_photo'):
                context['edit_url'] = photo_rec.get_edit_url()
        except KeyError:
            pass
        return context

    def get_data(self, context):
        if 'photo' not in context or not context['photo']:
            return {}
        photo = context['photo']
        return {
            'url': photo.get_absolute_url(),
            'h700': photo.h700.url,
            'original': photo.original.url,
            'grid_url': photo.get_grid_url(),
            'metadata': render_to_string('archive/photometadata.html', context, self.request),
            'thumbnails': render_to_string('archive/thumbnails.html', context, self.request),
            'backward': context['prev_page'][0].get_urls() if context['page'].has_previous() else NO_URLS,
            'forward': context['next_page'][0].get_urls() if context['page'].has_next() else NO_URLS,
            'previous': photo.previous.get_urls() if hasattr(photo, 'previous') else NO_URLS,
            'next': photo.next.get_urls() if hasattr(photo, 'next') else NO_URLS,
        }

    def render(self, context, **kwargs):
        return super().render_to_response(context, **kwargs)

    def render_to_response(self, context, **kwargs):
        if 'years' not in context:
            try:
                photo = Photo.objects.get(id=Photo.accession2id(self.kwargs['photo']))
                return redirect(photo.get_absolute_url(queryset=self.queryset, params=self.request.GET))
            except Photo.DoesNotExist:
                raise Http404("Photo either does not exist or is not in that set of photos")
        return self.render(context, **kwargs)


class XSendFile(View):
    def get_path(self):
        raise NotImplemented()

    def get_content_type(self, path):
        return NotImplemented()

    def get_file_size(self, path):
        return os.stat(path).st_size

    def dispatch(self, request, photo):
        response = HttpResponse()
        path = self.get_path()
        response['X-SendFile'] = path
        response['Content-Type'] = self.get_content_type(path)
        response['Content-Length'] = self.get_file_size(path)
        return response


class XSendImage(XSendFile):
    def get_path(self):
        obj = Photo.objects.get(id=Photo.accession2id(self.kwargs['photo']))
        return obj.original.path

    def get_content_type(self, path):
        return "image/jpeg"


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
        for i, photo in enumerate(page_obj):
            photo.row_number = page_obj.start_index() + i - 1
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
        self.collection = CollectionQuery(self.request.GET, self.request.user)
        qs = self.model.objects.filter_photos(self.collection).order_by('year', 'id')
        if qs.count() == 1:
            self.redirect = redirect(qs[0].get_absolute_url())
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collection_name'] = str(self.collection)
        try:
            context['timeline_url'] = context['page_obj'][0].get_absolute_url()
        except IndexError:
            pass
        return context

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
        context['collection_name'] = 'Search Results'
        return context

    def attach_params(self, photos):
        pass

    def dispatch(self, request, *args, **kwargs):
        self.form = SearchForm(self.request.GET)
        if self.form.is_valid():
            return super().dispatch(request, *args, **kwargs)
        else:
            return HttpResponseBadRequest('Invalid search parameters')

    def get_queryset(self):
        try:
            expr = self.form.as_expression()
            try:
                params = expr.as_collection()
                qd = QueryDict('', mutable=True)
                qd.update(params)
                self.redirect = redirect('{}?{}'.format(reverse('gridview'), qd.urlencode()))
                return []
            except ValueError:
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
    template_name = 'archive/collection_create.html'

    def get_success_url(self):
        return reverse('user-page', args=[self.request.user.get_username()])

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class CollectionDelete(BaseTemplateMixin, LoginRequiredMixin, DeleteView):
    model = Collection
    template_name = 'archive/collection_delete.html'

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


class DirectoryView(BaseTemplateMixin, TemplateView):
    template_name = 'archive/directory.html'
    subdirectories = [
        {'name': 'Terms', 'indexer': Term},
        {'name': 'Tags', 'indexer': Tag},
        {'name': 'Donors', 'indexer': Donor},
        {'name': 'Cities', 'indexer': Photo.CityIndexer()},
        {'name': 'Counties', 'indexer': Photo.CountyIndexer()},
    ]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['subdirectories'] = self.subdirectories
        return context


class MissingPhotosView(UserPassesTestMixin, ListView):
    template_name = 'archive/missingphotos.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        return CSVRecord.objects.filter(photo__isnull=True).order_by('added_to_archive', 'year', 'id')


class TagSearchView(JSONResponseMixin, BaseListView):
    def get_queryset(self):
        return Tag.objects.filter(tag__icontains=self.request.GET['term'], phototag__accepted=True).values('tag', 'id').distinct()[:10]

    def get_data(self, context):
        return [dict(id=tag['id'], value=tag['tag'], label=tag['tag']) for tag in context['object_list']]

    def render_to_response(self, context, **kwargs):
        return self.render_to_json_response(context, safe=False, **kwargs)


