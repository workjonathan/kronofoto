from django.core.management.base import BaseCommand
from ...models import Photo
from ...views.images import ImageSigner, ImageCacher

class Command(BaseCommand):
    help = "precache photos"

    def handle(self, *args, **options):
        for photo in Photo.objects.all().order_by('id'):
            ImageSigner(id=photo.id, path=photo.original.name, width=75, height=75).cacher.precache()
            ImageSigner(id=photo.id, path=photo.original.name, width=500, height=500).cacher.precache()
