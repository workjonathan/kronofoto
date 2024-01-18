from django.core.management.base import BaseCommand
from archive.geocoder import CSVGeocoder
from archive.models.photo import Photo

class Command(BaseCommand):
    help = 'reorganize media files'

    def handle(self, *args, **options):
        for p in Photo.objects.all().order_by('id'):
            oldname = p.original.name
            oldsize = p.original.size
            if sum(1 for c in oldname if c == '/') == 1:
                print(p.id)
                p.original.save("", p.original)
                p = Photo.objects.get(id=p.id)
                newname = p.original.name
                newsize = p.original.size
                if oldname != newname and oldsize == newsize:
                    p.original.storage.delete(oldname)

