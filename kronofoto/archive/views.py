from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, Page
from django.core.cache import cache
from django.conf import settings
from django.db.models import Min, Count, Q
import os
import random
from .models import Photo, Collection, PrePublishPhoto, ScannedPhoto, PhotoVote, Term, Tag, Donor, CSVRecord, CollectionQuery
from django.contrib.auth.models import User
from .forms import TagForm, AddToListForm, SearchForm
from django.utils.http import urlencode
from django.http import Http404, HttpResponseForbidden, JsonResponse, HttpResponseBadRequest, HttpResponse, QueryDict
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.views.generic import ListView, TemplateView, View
from django.views.generic.list import BaseListView
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from math import floor
from itertools import islice,chain
from .reverse import get_request, set_request, as_absolute

from .search.parser import Parser, UnexpectedParenthesis, ExpectedParenthesis, NoExpression
from .search import evaluate



EMPTY_PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='

FAKE_PHOTO = dict(thumbnail=dict(url=EMPTY_PNG, height=75, width=75))

NO_URLS = dict(url='#', json_url='#')

THEME = [
    {
        'color': "#6c84bd",
        "logo": static("assets/images/skyblue/logo.svg"),
        "menuSvg": static("assets/images/skyblue/menu.svg"),
        "infoSvg": static("assets/images/skyblue/info.svg"),
        "downloadSvg": static("assets/images/skyblue/download.svg"),
        "searchSvg": static("assets/images/skyblue/search.svg"),
        "carrotSvg": static("assets/images/skyblue/carrot.svg"),
        "timelineSvg": static("assets/images/skyblue/toggle.svg"),
    },
    {
        'color': "#c28800",
        'logo': static("assets/images/golden/logo.svg"),
        'menuSvg': static("assets/images/golden/menu.svg"),
        'infoSvg': static("assets/images/golden/info.svg"),
        'downloadSvg': static("assets/images/golden/download.svg"),
        'searchSvg': static("assets/images/golden/search.svg"),
        'carrotSvg': static("assets/images/golden/carrot.svg"),
        "timelineSvg": static("assets/images/golden/toggle.svg"),
    },
    {
        'color': "#c2a55e",
        'logo': static("assets/images/haybail/logo.svg"),
        'menuSvg': static("assets/images/haybail/menu.svg"),
        'infoSvg': static("assets/images/haybail/info.svg"),
        'downloadSvg': static("assets/images/haybail/download.svg"),
        'searchSvg': static("assets/images/haybail/search.svg"),
        'carrotSvg': static("assets/images/haybail/carrot.svg"),
        "timelineSvg": static("assets/images/haybail/toggle.svg"),
    },
    {
        'color': "#445170",
        'logo': static("assets/images/navy/logo.svg"),
        'menuSvg': static("assets/images/navy/menu.svg"),
        'infoSvg': static("assets/images/navy/info.svg"),
        'downloadSvg': static("assets/images/navy/download.svg"),
        'searchSvg': static("assets/images/navy/search.svg"),
        'carrotSvg': static("assets/images/navy/carrot.svg"),
        "timelineSvg": static("assets/images/navy/toggle.svg"),
    }
]

class BaseTemplateMixin:
    def set_request(self, request):
        # By default, the request should not be globally available.
        set_request(None)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.set_request(request)
        self.form = SearchForm(self.request.GET)
        self.expr = None
        if self.form.is_valid():
            try:
                self.expr = self.form.as_expression()
            except NoExpression:
                pass
        self.constraint_expr = None
        if 'constraint' in self.request.GET:
            constraint = self.request.GET['constraint']
            self.constraint_expr = Parser.tokenize(constraint).parse().shakeout()
        self.final_expr = None
        if self.expr and self.constraint_expr:
            self.final_expr = self.expr & self.constraint_expr
        else:
            self.final_expr = self.expr or self.constraint_expr

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        photo_count = cache.get('photo_count:')
        if not photo_count:
            photo_count = Photo.count()
            cache.set('photo_count:', photo_count)
        context['photo_count'] = photo_count
        context['grid_url'] = reverse('gridview')
        context['timeline_url'] = '#'
        context['grid_json_url'] = '#'
        context['timeline_json_url'] = '#'
        context['theme'] = random.choice(THEME)
        context['embed'] = 'embed' in self.request.GET
        return context


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
        form = SearchForm(self.request.GET)
        expr = None
        if form.is_valid():
            try:
                expr = form.as_expression()
            except NoExpression:
                pass
        photo = Photo.objects.filter_photos(
            CollectionQuery(expr, self.request.user)
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
    def set_request(self, request):
        set_request(request)
    def render_to_json_response(self, context, **response_kwargs):
        response = JsonResponse(self.get_data(context), **response_kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response
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
        self.collection = CollectionQuery(self.final_expr, self.request.user)
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
        cache_info = self.collection.cache_encoding()
        index_key = 'year_links:' + cache_info
        index = cache.get(index_key)
        if not index:
            index = queryset.year_links(params=self.request.GET)
            cache.set(index_key, index)

        paginator = self.get_paginator()
        page_selection = paginator.get_pages(page)

        try:
            photo_rec = page_selection.find_accession_number(photo)

            params = self.request.GET.copy()
            if 'constraint' in params:
                params.pop('constraint')
            if 'embed' in params:
                params.pop('embed')
            for p in page_selection.photos():
                p.save_params(params)

            context['prev_page'], context["page"], context['next_page'] = page_selection.pages
            context['grid_url'] = photo_rec.get_grid_url()
            context['grid_json_url'] = photo_rec.get_grid_json_url()
            context["photo"] = photo_rec
            context["alttext"] = ', '.join(photo_rec.describe(self.request.user))
            context["tags"] = photo_rec.get_accepted_tags(self.request.user)
            context["years"] = index
            if self.final_expr and self.final_expr.is_collection() and self.expr:
                context['collection_name'] = str(self.expr.description())
            else:
                context['collection_name'] = 'All Photos'
            context['timeline_key'] = cache_info
            if self.request.user.is_staff and self.request.user.has_perm('archive.change_photo'):
                context['edit_url'] = photo_rec.get_edit_url()
            context['initialstate'] = self.get_data(context)
        except KeyError:
            pass
        return context

    def get_data(self, context):
        if 'photo' not in context or not context['photo']:
            return {}
        photo = context['photo']
        return {
            'type': 'TIMELINE',
            'static_url': settings.STATIC_URL,
            'url': as_absolute(photo.get_absolute_url()),
            'h700': as_absolute(photo.h700.url),
            'alttext': str(context['alttext']),
            'tags': str(context['tags']),
            'original': as_absolute(photo.original.url),
            'grid_json_url': photo.get_grid_json_url(),
            'timeline_json_url': context['timeline_json_url'],
            'grid_url': photo.get_grid_url(),
            'timeline_url': context['timeline_url'],
            'frame': render_to_string('archive/photo-details.html', context, self.request),
            'metadata': render_to_string('archive/photometadata.html', context, self.request),
            'thumbnails': render_to_string('archive/thumbnails.html', context, self.request),
            'backward': context['prev_page'][0].get_urls() if context['page'].has_previous() else NO_URLS,
            'forward': context['next_page'][0].get_urls() if context['page'].has_next() else NO_URLS,
            'previous': photo.previous.get_urls() if hasattr(photo, 'previous') else NO_URLS,
            'next': photo.next.get_urls() if hasattr(photo, 'next') else NO_URLS,
            'year': photo.year,
        }

    def render(self, context, **kwargs):
        return super().render_to_response(context, **kwargs)

    def get_redirect_url(self, photo):
        return photo.get_absolute_url(queryset=self.queryset, params=self.request.GET)

    def render_to_response(self, context, **kwargs):
        if 'years' not in context:
            try:
                photo = Photo.objects.get(id=Photo.accession2id(self.kwargs['photo']))
                return redirect(self.get_redirect_url(photo))
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
    def get_data(self, context):
        return super().get_data(context)
    def render(self, context, **kwargs):
        return self.render_to_json_response(context, **kwargs)
    def get_redirect_url(self, photo):
        return photo.get_json_url(queryset=self.queryset, params=self.request.GET)


class GridBase(BaseTemplateMixin, ListView):
    model = Photo
    paginate_by = settings.GRID_DISPLAY_COUNT
    template_name = 'archive/photo_grid.html'
    _queryset = None

    @property
    def queryset(self):
        if self._queryset is None:
            self._queryset = self.get_queryset()
        return self._queryset

    def get_paginate_by(self, qs):
        return self.request.GET.get('display', self.paginate_by)

    def render(self, context, **kwargs):
        return super().render_to_response(context, **kwargs)

    def render_to_response(self, context, **kwargs):
        if hasattr(self, 'redirect'):
            return self.redirect
        return self.render(context, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        for i, photo in enumerate(page_obj):
            photo.row_number = page_obj.start_index() + i - 1
        self.attach_params(page_obj)
        return context

class GridViewFormatter:
    def __init__(self, parameters):
        self.parameters = parameters
    def page_url(self, num, json=False):
        view = 'gridview-json' if json else 'gridview'
        return "{}?{}".format(reverse(view, args=(num,)), self.parameters.urlencode())

class SearchResultsViewFormatter:
    def __init__(self, parameters):
        self.parameters = parameters
    def page_url(self, num, json=False):
        params = self.parameters.copy()
        params['page'] = num
        view = 'search-results-json' if json else 'search-results'
        return "{}?{}".format(reverse(view), params.urlencode())
    def render(self, context, **kwargs):
        return super().render_to_response(context, **kwargs)

class GridView(JSONResponseMixin, GridBase):

    def get_queryset(self):
        expr = self.final_expr
        self.collection = CollectionQuery(expr, self.request.user)
        qs = self.model.objects.filter_photos(self.collection).order_by('year', 'id')
        cache_info = 'photo_count:' + self.collection.cache_encoding()
        photo_count = cache.get(cache_info)
        if not photo_count:
            photo_count = qs.count()
            cache.set(cache_info, photo_count)
        if photo_count == 1:
            self.redirect = redirect(qs[0].get_absolute_url())
        return qs

    def get_data(self, context):
        return dict(
            type="GRID",
            static_url=settings.STATIC_URL,
            frame=render_to_string('archive/grid-content.html', context, self.request),
            url=context['page_obj'][0].get_grid_url(params=self.request.GET) if self.queryset.count() else "#",
            grid_json_url=context['grid_json_url'],
            timeline_json_url=context['timeline_json_url'],
            grid_url=context['grid_url'],
            timeline_url=context['timeline_url'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formatter'] = GridViewFormatter(self.request.GET)
        if self.final_expr and self.final_expr.is_collection() and self.expr:
            context['collection_name'] = str(self.expr.description())
        else:
            context['collection_name'] = 'All Photos'
        try:
            context['timeline_url'] = context['page_obj'][0].get_absolute_url()
            context['timeline_json_url'] = context['page_obj'][0].get_json_url()
        except IndexError:
            pass
        context['initialstate'] = self.get_data(context)
        return context

    def attach_params(self, photos):
        params = self.request.GET.copy()
        if 'display' in params:
            params.pop('display')
        for photo in photos:
            photo.save_params(params=params)


class SearchResultsView(JSONResponseMixin, GridBase):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search-form'] = self.form
        context['formatter'] = SearchResultsViewFormatter(self.request.GET)
        context['collection_name'] = 'Search Results' if self.final_expr else "All Photos"
        if self.queryset.count() == 0:
            context['noresults'] = True
            photo_rec = Photo.objects.filter(phototag__tag__tag='silly', phototag__accepted=True).order_by('?')[0]
            context['oops_photo'] = photo_rec
            context['query_expr'] = str(self.final_expr)
            context["tags"] = photo_rec.get_accepted_tags(self.request.user)
        else:
            context['noresults'] = False
            if self.final_expr and self.final_expr.is_collection():
                context['collection_name'] = str(self.expr.description()) if self.expr else "All Photos"
                context['timeline_url'] = context['page_obj'][0].get_absolute_url() if self.queryset.count() else "#"
                context['timeline_json_url'] = context['page_obj'][0].get_json_url() if self.queryset.count() else "#"
        context['initialstate'] = self.get_data(context)
        return context

    def attach_params(self, photos):
        params = self.request.GET.copy()
        if 'display' in params:
            params.pop('display')
        for photo in photos:
            photo.save_params(params=params)

    def get_data(self, context):
        return dict(
            type="GRID",
            static_url=settings.STATIC_URL,
            frame=render_to_string('archive/grid-content.html', context, self.request),
            url=context['page_obj'][0].get_grid_url(params=self.request.GET) if self.queryset.count() else "#",
            grid_url=context['grid_url'],
            grid_json_url=context['grid_json_url'],
            timeline_url=context['timeline_url'],
            timeline_json_url=context['timeline_json_url'],
        )

    def dispatch(self, request, *args, **kwargs):
        if self.form.is_valid():
            return super().dispatch(request, *args, **kwargs)
        else:
            return HttpResponseBadRequest('Invalid search parameters')

    def get_queryset(self):
        expr = self.final_expr

        if expr is None or expr.is_collection():
            self.collection = CollectionQuery(expr, self.request.user)
            qs = self.model.objects.filter_photos(self.collection).order_by('year', 'id')
        else:
            qs = expr.as_search(self.model.objects, self.request.user)
        if qs.count() == 1:
            self.redirect = redirect(qs[0].get_absolute_url())
        return qs

class JSONGridView(GridView):
    def render(self, context, **kwargs):
        return self.render_to_json_response(context, **kwargs)

class JSONSearchResultsView(SearchResultsView):
    def render(self, context, **kwargs):
        return self.render_to_json_response(context, **kwargs)

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


class MissingPhotosView(RedirectView):
    permanent = True
    pattern_name = 'admin:archive_csvrecord_changelist'


class TagSearchView(JSONResponseMixin, BaseListView):
    def get_queryset(self):
        return Tag.objects.filter(tag__icontains=self.request.GET['term'], phototag__accepted=True).values('tag', 'id').distinct()[:10]

    def get_data(self, context):
        return [dict(id=tag['id'], value=tag['tag'], label=tag['tag']) for tag in context['object_list']]

    def render_to_response(self, context, **kwargs):
        return self.render_to_json_response(context, safe=False, **kwargs)


class EmbedStyleSheet(TemplateView):
    template_name = 'archive/id.css'
    content_type = 'text/css'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['id'] = self.kwargs['id']
        return context
