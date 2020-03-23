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
    photo_list = Photo.objects.filter(q).order_by("year", "id")
    paginator = Paginator(photo_list, 10)
    photos = paginator.get_page(page)
    prev_photos = paginator.get_page(page - 1)
    next_photos = paginator.get_page(page + 1)
    cur_index = None
    next_page_first_accession = None
    prev_page_first_accession = None
    prev_page_last_accession = None
    if photos.has_next(): next_page_first_accession = next_photos[0].accession_number
    if photos.has_previous():
        prev_page_first_accession = prev_photos[0].accession_number
        prev_page_last_accession = prev_photos[-1].accession_number
    for i, p in enumerate(photos):
        if p.accession_number == photo:
            cur_index = i
            p.active = True
    prev_accession = None
    next_accession = None
    prev_photo_page = None
    next_photo_page = None
    if cur_index is not None:
        if cur_index == 0:
            prev_photo_page = page - 1
            next_photo_page = page
            prev_accession = prev_page_last_accession
            next_accession = photos[cur_index + 1].accession_number
        elif cur_index < 9:
            prev_photo_page = page
            next_photo_page = page
            prev_accession = photos[cur_index - 1].accession_number
            next_accession = photos[cur_index + 1].accession_number
        else:
            prev_photo_page = page
            next_photo_page = page + 1
            prev_accession = photos[cur_index - 1].accession_number
            next_accession = next_page_first_accession

    photo_rec = Photo.objects.filter(id=Photo.accession2id(photo))

    return render(
        request,
        "archive/photo.html",
        {
            "photos": photos,
            "photo": photo_rec,
            "next_page_first": next_page_first_accession,
            "prev_page_first": prev_page_first_accession,
            "prev_page_last": prev_page_last_accession,
            "prev_accession": prev_accession,
            "next_accession": next_accession,
            "prev_photo_page": prev_photo_page,
            "next_photo_page": next_photo_page,
            "index": index,
            "collections": collections,
            "cities": cities,
            "states": states,
            "countries": countries,
            "counties": counties,
            "getparams": request.GET.urlencode(),
        },
    )
