from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from .. import models

def place_types(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request=request,
        template="kronofoto/pages/placetypes.html",
        context={
            "placetypes": models.PlaceType.objects.order_by('name'),
        }
    )


def placelist(request: HttpRequest, pk: int) -> HttpResponse:
    return TemplateResponse(
        request=request,
        template="kronofoto/pages/placelist.html",
        context={
            "places": models.Place.objects.filter(place_type__pk=pk).order_by('name'),
        }
    )
