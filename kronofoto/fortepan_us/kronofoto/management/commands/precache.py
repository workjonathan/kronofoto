from django.core.management.base import BaseCommand
from fortepan_us.kronofoto.models import Photo
from fortepan_us.kronofoto.imageutil import ImageSigner, ImageCacher

class Command(BaseCommand):
    help = "precache photos"

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=0)
        parser.add_argument('--id', type=int, default=0)

    def handle(self, *args, id, year, **options):
        for photo in (Photo.objects.filter(year__gt=year)|Photo.objects.filter(year=year, id__gte=id)).order_by('year', 'id'):
            print(photo.year, photo.id)
            ImageSigner(id=photo.id, path=photo.original.name, width=75, height=75).cacher.precache()
            ImageSigner(id=photo.id, path=photo.original.name, width=500, height=500).cacher.precache()
