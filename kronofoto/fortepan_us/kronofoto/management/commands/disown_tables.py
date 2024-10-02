from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'transfer migration history and content types to fortepan_us.kronofoto'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("UPDATE django_migrations SET app='kronofoto' WHERE app='archive';")
            cursor.execute("UPDATE django_content_type SET app_label='kronofoto' WHERE app_label='archive';")

