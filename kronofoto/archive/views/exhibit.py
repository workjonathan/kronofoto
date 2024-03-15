from django.contrib.auth.decorators import user_passes_test
from ..models import Photo, Exhibit, Card
from django.shortcuts import get_object_or_404
from django.db.models.functions import Length
from django.template.response import TemplateResponse
from django.http import HttpResponse, HttpRequest
from .base import ArchiveRequest
from typing import Dict, Any

@user_passes_test(lambda user: user.is_staff) # type: ignore
def exhibit(request : HttpRequest, pk: int, title: str) -> HttpResponse:
    exhibit = get_object_or_404(Exhibit.objects.all().select_related('photo', 'photo__place', 'photo__donor'), pk=pk)
    context: Dict[str, Any] = {}
    context['exhibit'] = exhibit
    cards = exhibit.card_set.all().order_by('order').select_related(
        'photocard',
        'photocard__photo',
        'photocard__photo__donor',
        'photocard__photo__place',
        'photocard__doublephotocard',
        'photocard__doublephotocard__photo2',
        'photocard__doublephotocard__photo2__donor',
        'photocard__doublephotocard__photo2__place',
    )
    context['cards'] = cards

    return TemplateResponse(request, "archive/exhibit.html", context=context)
