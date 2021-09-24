from django.core.management.base import BaseCommand
from archive.geocoder import CSVGeocoder

class Command(BaseCommand):
    help = 'geocode from google'

    def handle(self, *args, **options):
        geocoder = CSVGeocoder()
        geocoder.geocode_from_csv_data()
