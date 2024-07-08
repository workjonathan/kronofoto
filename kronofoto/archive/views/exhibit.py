from django.contrib.auth.decorators import user_passes_test
from ..models import Photo
from django.db.models.functions import Length
from django.template.response import TemplateResponse
from .base import ArchiveRequest
from django.http import HttpResponse, HttpRequest

@user_passes_test(lambda user: hasattr(user, "is_superuser") and user.is_superuser)
def exhibit(request: HttpRequest) -> HttpResponse:
    context = ArchiveRequest(request).common_context
    photos = Photo.objects.annotate(len=Length('caption')).filter(len__gte=200).order_by("?")[:10]
    context.update({"photos": photos})
    return TemplateResponse(request, "archive/exhibit.html", context=context)
