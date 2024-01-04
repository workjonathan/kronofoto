from django.core.management.base import BaseCommand
from ...models import Place, PlaceType

class Command(BaseCommand):
    help = "update place full names"

    def handle(self, *args, **options):
        for placetype in PlaceType.objects.all():
            print(placetype.name)
            placetype.name_places()
