from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, AnonymousUser
from django.test import RequestFactory, Client
from archive.views import PhotoView
from kronofoto import settings
settings.ALLOWED_HOSTS.append('testserver')

class Command(BaseCommand):
    def handle(self, *args, **options):
        resp = Client().get('/photo/10/FI0000007/')
        print(resp)
