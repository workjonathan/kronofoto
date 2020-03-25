from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Min, Count, Q
from .models import Photo, Collection, PrePublishPhoto, ScannedPhoto, PhotoVote
from django.utils.http import urlencode
from django.views.generic import ListView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
import operator
from functools import reduce
from math import floor
from itertools import islice,chain


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
        vote, created = PhotoVote.objects.update_or_create(photo=photo, voter=self.request.user, defaults={'infavor': self.infavor})
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


def photoview(request, page, photo):
    replacements = {"collection": "collection__name"}
    params = ("collection", "city", "state", "country")
    filtervals = (
        (replacements.get(param, param), request.GET.get(param))
        for param in params
    )
    clauses = [Q(**{k: v}) for (k, v) in filtervals if v]

    andClauses = [Q(is_published=True), Q(year__isnull=False)]
    if clauses:
        andClauses.append(reduce(operator.or_, clauses))
    q = reduce(operator.and_, andClauses)

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

    items = 10

    photo_list = Photo.objects.filter(q).order_by("year", "id")
    paginator = Paginator(photo_list, items)
    this_page = paginator.get_page(page)
    for i, p in enumerate(this_page):
        if p.accession_number == photo:
            p.active = True
            photo_rec = p
            break

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

    return render(
        request,
        "archive/photo.html",
        {
            "page": this_page,
            "next_page": next_page,
            "prev_page": prev_page,
            "photo": photo_rec,
            "index": index,
            "collections": collections,
            "cities": cities,
            "states": states,
            "countries": countries,
            "coenties": counties,
            "getparams": request.GET.urlencode(),
        },
    )
