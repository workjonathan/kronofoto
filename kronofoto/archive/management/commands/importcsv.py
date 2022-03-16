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
        with open(options['csvfile'][0], newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            #with transaction.atomic():
            for row in reader:
                try:
                    year = row['Year'][:4].strip()
                    circa = row['Circa'].strip()
                    if not year:
                        year = None
                    if not circa:
                        circa = None
                    CSVRecord(
                        filename=row['FILE NAME'].strip(),
                        donorFirstName=row['DONOR FIRST NAME'].strip(),
                        donorLastName=row['DONOR LAST NAME'].strip(),
                        year=year,
                        circa=circa,
                        scanner=row['Scanner'].strip(),
                        photographer=row['Photographer'].strip(),
                        address=row['Address'].strip(),
                        city=row['City/Town'].strip(),
                        county=row['County'].strip(),
                        state=row["State"].strip(),
                        country=row['Country'].strip(),
                        comments=row['Comments'].strip(),
                        added_to_archive=row['ADDED TO ARCHIVE']
                    ).save()
                except IntegrityError as err:
                    print(row)
