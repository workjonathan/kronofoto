from django.core.management.base import BaseCommand
from ...models.csvrecord import ConnecticutRecord
import csv
import re

ids = re.compile(r'.*/([0-9]+?):([0-9]+?)/.*')

class Command(BaseCommand):
    help = 'load records from ctda csv file'

    def add_arguments(self, parser):
        parser.add_argument('csv_inputs', nargs='+')

    def handle(self, *args, csv_inputs, **options):
        no_ids = 0
        processed = 0
        objs = []
        for csv_input in csv_inputs:
            with open(csv_input, 'r', newline='', encoding='utf-8') as inf:
                for row in csv.DictReader(inf):
                    m = re.search(ids, row['File Name'])
                    if not m:
                        no_ids += 1
                    else:
                        id1 = int(m.group(1))
                        id2 = int(m.group(2))
                        title = row['Title'].strip()
                        year = row['Year'].strip()
                        contributor = row['Contributor Last Name'].strip()
                        description = row['dc.description'].strip()
                        location = row['City/Town'].strip()

                        obj = ConnecticutRecord(
                            file_id1=id1,
                            file_id2=id2,
                            title= title,
                            year= year,
                            contributor= contributor,
                            description= description,
                            location= location,
                        )
                        objs.append(obj)
                    processed += 1
                    if processed % 100 == 0:
                        print(processed)
        ConnecticutRecord.objects.bulk_create(objs)
        print(no_ids, processed)
