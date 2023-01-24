from django.apps import AppConfig
from django.conf import settings


class ArchiveConfig(AppConfig):
    name = "archive"

    def ready(self):
        from . import settings as app_defaults
        for name in dir(app_defaults):
            if name.isupper() and not hasattr(settings, name):
                setattr(settings, name, getattr(app_defaults, name))
