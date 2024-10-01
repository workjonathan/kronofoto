from django.apps import AppConfig


class KronofotoConfig(AppConfig):
    #default_auto_field = "django.db.models.BigAutoField"
    name = "fortepan_us.kronofoto"

    def ready(self) -> None:
        from fortepan_us.kronofoto import settings as app_defaults
        from fortepan_us.kronofoto import signals
        from django.conf import settings
        for name in dir(app_defaults):
            if name.isupper() and not hasattr(settings, name):
                setattr(settings, name, getattr(app_defaults, name))
