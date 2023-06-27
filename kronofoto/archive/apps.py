from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ArchiveConfig(AppConfig):
    name = "archive"

    def ready(self):
        from . import settings as app_defaults
        from . import signals
        from django.conf import settings
        for name in dir(app_defaults):
            if name.isupper() and not hasattr(settings, name):
                setattr(settings, name, getattr(app_defaults, name))
