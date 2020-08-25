from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from django.db import transaction
from archive.models import CSVRecord
import csv
import sys

class Command(BaseCommand):
    help = 'import csv in arbitrary standard format'

    def add_arguments(self, parser):
        parser.add_argument('csvfile', nargs=1)


    def handle(self, *args, **options):
        with open(options['csvfile'][0], newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            #with transaction.atomic():
            for row in reader:
                try:
                    CSVRecord(
                        filename=row['FILE NAME'],
                        donorFirstName=row['DONOR FIRST NAME'],
                        donorLastName=row['DONOR LAST NAME'],
                        year=row['Year'][:4],
                        circa=row['Circa'],
                        scanner=row['Scanner'],
                        photographer=row['Photographer'],
                        address=row['Address'],
                        city=row['City/Town'],
                        county=row['County'],
                        state=row["State"],
                        country=row['Country'],
                        comments=row['Comments'],
                        added_to_archive=row['ADDED TO ARCHIVE']
                    ).save()
                except IntegrityError as err:
                    print(row)
