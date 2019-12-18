from django.shortcuts import render
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Min, Count
from .models import Photo
from math import floor

def photoview(request, page, photo):
    # yikes
    year_vals = Photo.objects.values('year').filter(is_published=True, year__isnull=False).annotate(min_id=Min('id'), count=Count('id')).order_by('year')
    year_index = (p['min_id'] for p in year_vals)
    year_pages = {}
    running_total = 0
    for y in year_vals:
        year_pages[y['year']] = floor(running_total/10) + 1
        running_total += y['count']
    year_photos = Photo.objects \
        .filter(id__in=year_index, year__isnull=False) \
        .order_by('year')

    index = []
    for p in year_photos:
        while index and index[-1][0] != p.year - 1:
            index.append((index[-1][0] + 1, p, year_pages[p.year]))
        index.append((p.year, p, year_pages[p.year]))
    photo_list = Photo.objects.filter(is_published=True, year__isnull=False).order_by('year', 'id')
    paginator = Paginator(photo_list, 10)
    photos = paginator.get_page(page)
    prev_photos = paginator.get_page(page-1)
    next_photos = paginator.get_page(page+1)
    cur_index = None
    next_page_first_accession = None
    prev_page_first_accession = None
    prev_page_last_accession = None
    if photos.has_next():
        next_page_first_accession = next_photos[0].accession_number
    if photos.has_previous():
        prev_page_first_accession = prev_photos[0].accession_number
        prev_page_last_accession = prev_photos[-1].accession_number
    for i, p in enumerate(photos):
        if p.accession_number == photo:
            cur_index = i
    prev_accession = None
    next_accession = None
    prev_photo_page = None
    next_photo_page = None
    if cur_index is not None:
        if cur_index == 0:
            prev_photo_page = page-1
            next_photo_page = page
            prev_accession = prev_page_last_accession
            next_accession = photos[cur_index+1].accession_number
        elif cur_index < 9:
            prev_photo_page = page
            next_photo_page = page
            prev_accession = photos[cur_index-1].accession_number
            next_accession = photos[cur_index+1].accession_number
        else:
            prev_photo_page = page
            next_photo_page = page+1
            prev_accession = photos[cur_index-1].accession_number
            next_accession = next_page_first_accession

    photo_rec = Photo.objects.filter(accession_number=photo)

    return render(request, 'archive/photo.html',
        {
            'photos': photos,
            'photo': photo_rec,
            'next_page_first': next_page_first_accession,
            'prev_page_first': prev_page_first_accession,
            'prev_page_last': prev_page_last_accession,
            'prev_accession': prev_accession,
            'next_accession': next_accession,
            'prev_photo_page': prev_photo_page,
            'next_photo_page': next_photo_page,
            'index': index,
            'year_pages': year_pages
        })

