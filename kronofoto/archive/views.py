from django.shortcuts import render
from django.core.paginator import Paginator
from django.conf import settings
from .models import Photo

def photoview(request, page, photo):
    photo_list = Photo.objects.filter(is_published=True, year__isnull=False).order_by('year', 'id')
    paginator = Paginator(photo_list, 13)
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
        elif cur_index < 12:
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
        })

