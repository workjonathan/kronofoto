from django.contrib.auth.decorators import user_passes_test
from ..models import Photo, Exhibit, Card
from django.shortcuts import get_object_or_404
from django.db.models.functions import Length
from django.db.models import QuerySet
from django.template.response import TemplateResponse
from django.http import HttpResponse, HttpRequest
from .base import ArchiveRequest
from typing import Dict, Any, Iterator, Union
from django.template.defaultfilters import linebreaksbr, linebreaks_filter

def cardinfo(cards: QuerySet[Card]) -> Iterator[Union[Card, Dict[str, Any]]]:
    for card in cards:
        if hasattr(card, 'photocard'):
            if hasattr(card.photocard, 'doublephotocard'):
                card = card.photocard.doublephotocard
                obj = {
                    'card_style': 0,
                    'description': card.description,
                    'description2': card.description2,
                    'photo': card.photo,
                    'photo2': card.photo2,
                    'template': 'archive/components/two-image-card.html',
                }
                obj['photocard'] = obj
                obj['doublephotocard'] = obj
                yield obj
            else:
                card = card.photocard
                if card.card_style == 0:
                    obj = {
                        'image_area_classes': ['full-image-area--contain'],
                        'card_style': 0,
                        'description': linebreaks_filter(card.description),
                        'photo': card.photo,
                        'template': 'archive/components/full-image-card.html',
                    }
                    obj['photocard'] = obj
                    yield obj
                elif card.card_style in (5, 7, 8):
                    obj = {
                        'image_area_classes': [],
                        'card_style': 0,
                        'description': linebreaksbr(card.description),
                        'photo': card.photo,
                        'template': 'archive/components/full-image-card.html',
                    }
                    obj['photocard'] = obj
                    yield obj
                elif card.card_style in (1,):
                    obj = {
                        'image_area_classes': ['two-column--image-left', 'two-column--variation-1'],
                        'card_style': 1,
                        'description': card.description,
                        'photo': card.photo,
                        'template': 'archive/components/two-column-card.html',
                    }
                    obj['photocard'] = obj
                    yield obj
                elif card.card_style in (3,):
                    obj = {
                        'image_area_classes': ['two-column--image-left', 'two-column--variation-3'],
                        'card_style': 1,
                        'description': card.description,
                        'photo': card.photo,
                        'template': 'archive/components/two-column-card.html',
                    }
                    obj['photocard'] = obj
                    yield obj
                elif card.card_style in (4,):
                    obj = {
                        'image_area_classes': ['two-column--image-right', 'two-column--variation-4'],
                        'card_style': 1,
                        'description': card.description,
                        'photo': card.photo,
                        'template': 'archive/components/two-column-card.html',
                    }
                    obj['photocard'] = obj
                    yield obj
                elif card.card_style in (2,):
                    obj = {
                        'image_area_classes': ['two-column--image-right', 'two-column--variation-2'],
                        'card_style': 1,
                        'description': card.description,
                        'photo': card.photo,
                        'template': 'archive/components/two-column-card.html',

                    }
                    obj['photocard'] = obj
                    yield obj
                elif card.card_style in (6,):
                    obj = {
                        'card_style': 1,
                        'description': card.description,
                        'photo': card.photo,
                        'template': 'archive/components/figure-card.html',

                    }
                    obj['photocard'] = obj
                    yield obj
        else:
            if card.card_style == 0:
                yield {
                    'content_attrs': {
                        'data-aos': 'fade-up',
                        'data-aos-duration': '1000',
                    },
                    'styles': {
                    },
                    'description': card.description,
                    'card_style': 0,
                    'template': 'archive/components/text-card.html',
                }
            elif card.card_style == 1:
                yield {
                    'content_attrs': {
                    },
                    'styles': {
                        'border-top': '1px solid #ffffff'
                    },
                    'description': card.description,
                    'card_style': 0,
                    'template': 'archive/components/text-card.html',
                }
            elif card.card_style == 2:
                yield {
                    'content_attrs': {
                    },
                    'styles': {
                    },
                    'description': card.description,
                    'card_style': 0,
                    'template': 'archive/components/text-card.html',
                }
            else:
                yield card

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
    context['cards'] = cardinfo(cards)

    return TemplateResponse(request, "archive/exhibit.html", context=context)
