from django.apps import AppConfig


class ArchiveConfig(AppConfig):
    name = "archive"

    def ready(self):
        from . import signals
