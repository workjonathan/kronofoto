from django.core.management.base import BaseCommand
from archive.models import CSVRecord

class Command(BaseCommand):
    help = 'trim whitespace from csv records'

    def handle(self, *args, **options):
        CSVRecord.objects.bulk_clean()
