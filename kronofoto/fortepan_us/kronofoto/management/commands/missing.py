from django.core.management.base import BaseCommand
from archive.models import CSVRecord, Photo, Collection, Donor



class Command(BaseCommand):
    help = 'dump out missing photos'

    def handle(self, *args, **options):
        records = CSVRecord.objects.filter(photo__isnull=True).order_by('added_to_archive', 'year', 'id')
        print(repr([record.filename[:-4] if record.filename.endswith('.jpg') else record.filename for record in records]))
