from django.core.management.base import BaseCommand
from archive.models import Donor

class Command(BaseCommand):
    help = 'trim whitespace off names'

    def handle(self, *args, **options):
        for donor in Donor.objects.all():
            donor.first_name = donor.first_name.strip()
            donor.last_name = donor.last_name.strip()
            donor.save()
