from django.conf import settings

def feature_flags(request):
    return dict(
        KF_DJANGOCMS_NAVIGATION=settings.KF_DJANGOCMS_NAVIGATION,
        KF_DJANGOCMS_SUPPORT=settings.KF_DJANGOCMS_SUPPORT,
    )
