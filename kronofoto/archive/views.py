from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Min, Count, Q
from .models import Photo, Collection, PrePublishPhoto, ScannedPhoto, PhotoVote
from django.contrib.auth.models import User
from .forms import TagForm, AddToListForm
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
import operator
from functools import reduce
from math import floor
from itertools import islice,chain

from .search.parser import parse, UnexpectedParenthesis, ExpectedParenthesis
from .search import evaluate, sort


class AddTagView(LoginRequiredMixin, FormView):
    template_name = 'archive/add_tag.html'
    form_class = TagForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['photo'] = self.photo
        return context

    def dispatch(self, request, photo):
        self.photo = Photo.objects.get(id=Photo.accession2id(photo))
        self.success_url = reverse('photoview', kwargs={'page': 0, 'photo': photo})
        return super().dispatch(request)

    def form_valid(self, form):
        form.add_tag(self.photo)
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


def build_query(getparams, user):
    replacements = {
        "collection": "collection__id",
        "tag": 'phototag__tag__slug',
        'term': 'terms__slug',
        'donor': 'donor__id',
    }
    params = ("collection", "county", "city", "state", "country", 'tag', 'term', 'donor')
    merges = {
        'phototag__tag__slug': [Q(phototag__accepted=True)],
        'collection__id': [~Q(collection__visibility='PR')],
    }
    if user.is_authenticated:
        merges['collection__id'][0] |= Q(collection__owner=user)
    filtervals = (
        (replacements.get(param, param), getparams.get(param))
        for param in params
    )
    clauses = [reduce(operator.and_, [Q(**{k: v})] + merges.get(k, [])) for (k, v) in filtervals if v]

    andClauses = [Q(is_published=True), Q(year__isnull=False)]
    if clauses:
        andClauses.append(reduce(operator.or_, clauses))
    return reduce(operator.and_, andClauses)


class FrontPage(RedirectView):
    permanent = False
    pattern_name = 'photoview'

    def get_redirect_url(self, *args, **kwargs):
        q = build_query(self.request.GET, self.request.user)
        photo = Photo.objects.filter(q).order_by('?')[0]
        return super().get_redirect_url(
            *args, page=1, photo=photo.accession_number, **kwargs
        )


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


class PhotoView(JSONResponseMixin, TemplateView):
    template_name = "archive/photo.html"
    def get_context_data(self, page, photo):
        context = super().get_context_data()
        q = build_query(self.request.GET, self.request.user)

        # yikes
        year_vals = (
            Photo.objects.values("year")
            .filter(q)
            .annotate(min_id=Min("id"), count=Count("id"))
            .order_by("year")
        )
        year_index = (p["min_id"] for p in year_vals)
        year_pages = {}
        running_total = 0
        for y in year_vals:
            year_pages[y["year"]] = floor(running_total / 10) + 1
            running_total += y["count"]
        year_photos = Photo.objects.filter(
            id__in=year_index, year__isnull=False
        ).order_by("year")

        collections = Collection.objects.values("name")
        cities = (
            Photo.objects.exclude(city="")
            .values("city")
            .annotate(count=Count("city"))
        )
        counties = (
            Photo.objects.exclude(county="")
            .values("county")
            .annotate(count=Count("county"))
        )
        states = (
            Photo.objects.exclude(state="")
            .values("state")
            .annotate(count=Count("state"))
        )
        countries = (
            Photo.objects.exclude(country="")
            .values("country")
            .annotate(count=Count("country"))
        )

        index = []
        for p in year_photos:
            while index and index[-1][0] != p.year - 1:
                index.append((index[-1][0] + 1, p, year_pages[p.year]))
            index.append((p.year, p, year_pages[p.year]))
        index = [(year, reverse('photoview', kwargs={'photo':photo.accession_number, 'page': page}), reverse('photoview-json', kwargs={'photo': photo.accession_number, 'page': page})) for (year, photo, page) in index]
        items = 10

        photo_list = Photo.objects.filter(q).order_by("year", "id")
        paginator = Paginator(photo_list, items)
        this_page = paginator.get_page(page)
        photo_rec = None
        for i, p in enumerate(this_page):
            if p.accession_number == photo:
                p.active = True
                photo_rec = p
                break

        if photo_rec is None:
            id = Photo.accession2id(photo)
            try:
                photo = photo_list.get(id=id)
                idx = len(photo_list.filter(Q(year__lt=photo.year) | (Q(year=photo.year) & Q(id__lt=photo.id))))
                url = reverse('photoview', kwargs={'page': (idx//items + 1), 'photo': photo.accession_number})
                self.redirect = redirect("{}?{}".format(url, self.request.GET.urlencode()))
            except Photo.DoesNotExist:
                raise Http404("Photo either does not exist or is not in that set of photos")
        prev_page = []
        next_page = []
        if this_page.has_previous():
            prev_page = paginator.get_page(page-1)
            for p in prev_page:
                p.page = prev_page
        if this_page.has_next():
            next_page = paginator.get_page(page+1)
            for p in next_page:
                p.page = next_page
        for p in this_page:
            p.page = this_page
        last = None
        for p in chain(prev_page, this_page, next_page):
            if last:
                p.last = last
                last.next = p
            last = p

        context["page"] = this_page
        context["next_page"] = next_page
        context["prev_page"] = prev_page
        context["photo"] = photo_rec
        context["years"] = index
        context["collections"] = collections
        context["cities"] = cities
        context["states"] = states
        context["countries"] = countries
        context["counties"] = counties
        context["getparams"] = self.request.GET.urlencode()
        context['initialstate'] = self.get_data(context)
        return context

    def get_data(self, context):
        if 'photo' not in context or not context['photo']:
            return {

            }
        return {
            'url': "{}?{}".format(reverse('photoview', kwargs={'page': context['page'].number, 'photo': context['photo'].accession_number}), self.request.GET.urlencode()),
            'h700': staticfiles_storage.url(context['photo'].h700.url),
            'metadata': render_to_string('archive/photometadata.html', context),
            'thumbnails': render_to_string('archive/thumbnails.html', context),
            'backward': {
                "url": "{}?{}".format(reverse('photoview', kwargs={'page': context['page'].previous_page_number(), 'photo': context['prev_page'][0].accession_number}), self.request.GET.urlencode()),
                'json_url': "{}?{}".format(reverse('photoview-json', kwargs={'page': context['page'].previous_page_number(), 'photo': context['prev_page'][0].accession_number}), self.request.GET.urlencode()),
            } if context['page'].has_previous() else {},
            'forward': {
                "url": "{}?{}".format(reverse('photoview', kwargs={'page': context['page'].next_page_number(), 'photo': context['next_page'][0].accession_number}), self.request.GET.urlencode()),
                'json_url': "{}?{}".format(reverse('photoview-json', kwargs={'page': context['page'].next_page_number(), 'photo': context['next_page'][0].accession_number}), self.request.GET.urlencode()),
            } if context['page'].has_next() else {},
            'next': {
                'url': "{}?{}".format(reverse('photoview', kwargs={'page': context['photo'].next.page.number, 'photo': context['photo'].next.accession_number}), self.request.GET.urlencode()),
                'json_url': "{}?{}".format(reverse('photoview-json', kwargs={'page': context['photo'].next.page.number, 'photo': context['photo'].next.accession_number}), self.request.GET.urlencode()),
            } if 'photo' in context and context['photo'] and hasattr(context['photo'], 'next') else {},
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


class GridView(ListView):
    model = Photo
    paginate_by = 50
    template_name = 'archive/photo_grid.html'

    def get_queryset(self):
        return Photo.objects.filter(
            build_query(self.request.GET, self.request.user)
        ).order_by('year', 'id')

    def get_paginate_by(self, qs):
        return self.request.GET.get('display', self.paginate_by)

    def format_page_url(self, num):
        return "{}?{}".format(reverse('gridview', args=(num,)), self.request.GET.urlencode())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
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


class SearchResultsView(GridView):
    def format_page_url(self, num):
        return "{}?{}".format(reverse('search-results'), urlencode({'q': self.query, 'page': num}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.query
        return context

    def get_queryset(self):
        self.query = self.request.GET.get('q')
        expr = None
        while expr is None:
            try:
                expr = parse(self.query)
            except UnexpectedParenthesis as err:
                self.query = self.query[:err.index] + self.query[err.index+1:]
            except ExpectedParenthesis:
                self.query = self.query + ')'
        print(expr)
        return sort(expr, evaluate(expr, Photo.objects))


class Profile(ListView):
    model = Collection
    template_name = 'archive/user_page.html'

    def get_queryset(self):
        if self.request.user.get_username() == self.kwargs['username']:
            return Collection.objects.filter(owner=self.request.user)
        else:
            user = get_object_or_404(User, username=self.kwargs['username'])
            return Collection.objects.filter(owner=user, visibility='PU')


class CollectionCreate(LoginRequiredMixin, CreateView):
    model = Collection
    fields = ['name', 'visibility']
    template_name = 'archive/collection_create.html'

    def get_success_url(self):
        return reverse('user-page', args=[self.request.user.get_username()])

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class CollectionDelete(LoginRequiredMixin, DeleteView):
    model = Collection
    template_name = 'archive/collection_delete.html'

    def get_success_url(self):
        return reverse('user-page', args=[self.request.user.get_username()])

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.owner != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)


class AddToList(LoginRequiredMixin, FormView):
    template_name = 'archive/collection_create.html'
    form_class = AddToListForm

    def get_success_url(self):
        return reverse('photoview', args=[1, self.kwargs['photo']])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['collections'] = [(collection.id, collection.name) for collection in Collection.objects.filter(owner=self.request.user)]
        kwargs['collections'].append((None, 'New List'))
        return kwargs

    def form_valid(self, form):
        if form.cleaned_data['collection']:
            collection = get_object_or_404(
                Collection, id=form.cleaned_data['collection']
            )
            if collection.owner == self.request.user:
                photo = get_object_or_404(
                    Photo, id=Photo.accession2id(self.kwargs['photo'])
                )
                collection.photos.add(photo)
        elif form.cleaned_data['name']:
            collection = Collection.objects.create(
                name=form.cleaned_data['name'],
                owner=self.request.user,
                visibility=form.cleaned_data['visibility'],
            )
        return super().form_valid(form)
