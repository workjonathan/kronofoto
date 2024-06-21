from django.contrib.auth.decorators import user_passes_test
from ..models import Photo, Exhibit, Card, Collection, PhotoCard
from django.shortcuts import get_object_or_404
from django.db.models.functions import Length
from django.db.models import QuerySet, Exists, OuterRef, Max, F
from django.db import transaction
from django.template.response import TemplateResponse
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, QueryDict
from django.core.exceptions import PermissionDenied
from ..reverse import reverse
from .base import ArchiveRequest
from typing import Dict, Any, Iterator, Union, List
from django.template.defaultfilters import linebreaksbr, linebreaks_filter
from django.contrib.auth.decorators import login_required
from django.forms import ModelForm, ModelChoiceField
from ..templatetags.widgets import card_tag
from ..forms import CardForm, PhotoCardForm
import json


@transaction.atomic
def card_edit(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method and request.method.lower() == 'delete':
        card = get_object_or_404(Card.objects.all(), pk=pk)
        if card.exhibit.owner != request.user:
            raise PermissionDenied
        Card.objects.filter(exhibit=card.exhibit, order__gt=card.order).update(order=F('order')-1)
        card.delete()
    if request.method and request.method.lower() == 'patch':
        if request.user.is_anonymous:
            raise PermissionDenied
        put_data = QueryDict(request.body)
        other_card = None
        if PhotoCard.objects.filter(pk=pk).exists():
            photocard = get_object_or_404(PhotoCard.objects.all(), pk=pk)
            if 'up' in put_data:
                other_card = Card.objects.get(exhibit=photocard.exhibit, order=photocard.order-1)
            if 'down' in put_data:
                other_card = Card.objects.get(exhibit=photocard.exhibit, order=photocard.order+1)
            if other_card:
                other_card.order, photocard.order = photocard.order, other_card.order
            if photocard.exhibit.owner != request.user:
                raise PermissionDenied
            photoform = PhotoCardForm(data=put_data, instance=photocard)
            if photoform.is_valid():
                photocard = photoform.save()
                if other_card:
                    other_card.save()
            context = card_tag(photocard, 0, edit=True)
            response = TemplateResponse(
                request=request,
                context=context,
                template=context['template'],
            )
            if 'down' in put_data:
                response['Hx-Trigger'] = json.dumps({
                    'kronofoto:exhibit:reorder': {
                        'id': f'#card-{photocard.id}',
                        'target': f'#card-{other_card.id}',
                        'swapStyle': 'afterend',
                    },
                })
            if 'up' in put_data:
                response['Hx-Trigger'] = json.dumps({
                    'kronofoto:exhibit:reorder': {
                        'id': f'#card-{photocard.id}',
                        'target': f'#card-{other_card.id}',
                        'swapStyle': 'beforebegin',
                    },
                })
            return response
        else:
            card = get_object_or_404(Card.objects.all(), pk=pk)
            if 'up' in put_data:
                other_card = Card.objects.get(exhibit=card.exhibit, order=card.order-1)
            if 'down' in put_data:
                other_card = Card.objects.get(exhibit=card.exhibit, order=card.order+1)
            if other_card:
                other_card.order, card.order = card.order, other_card.order
            if card.exhibit.owner != request.user:
                raise PermissionDenied
            form = CardForm(data=put_data, instance=card)
            if form.is_valid():
                card = form.save()
                if other_card:
                    other_card.save()
            context = card_tag(card, 0, edit=True)
            response = TemplateResponse(
                request=request,
                context=context,
                template=context['template'],
            )
            if 'down' in put_data:
                response['Hx-Trigger'] = json.dumps({
                    'kronofoto:exhibit:reorder': {
                        'id': f'#card-{card.id}',
                        'target': f'#card-{other_card.id}',
                        'swapStyle': 'afterend',
                    },
                })
            if 'up' in put_data:
                response['Hx-Trigger'] = json.dumps({
                    'kronofoto:exhibit:reorder': {
                        'id': f'#card-{card.id}',
                        'target': f'#card-{other_card.id}',
                        'swapStyle': 'beforebegin',
                    },
                })
            return response
    return HttpResponse()

def exhibit_cards(request: HttpRequest, pk: int) -> HttpResponse:
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    if exhibit.owner != request.user:
        raise PermissionDenied
    if request.method == "POST":
        photocardform = PhotoCardForm(request.POST)
        if photocardform.is_valid():
            photocard = photocardform.save(commit=False)
            photocard.exhibit = exhibit
            photocard.order = (exhibit.card_set.aggregate(Max("order"))['order__max'] or 0) + 1
            photocard.card_style = 0
            photocard.save()
            context = card_tag(photocard, 0, edit=True)
            return TemplateResponse(
                request=request,
                context=context,
                template=context['template'],
            )
        else:
            cardform = CardForm(request.POST)
            if cardform.is_valid():
                card = cardform.save(commit=False)
                card.exhibit = exhibit
                card.order = (exhibit.card_set.aggregate(Max("order"))['order__max'] or 0) + 1
                card.card_style = 0
                card.save()
                context = card_tag(card, 0, edit=True)
                return TemplateResponse(
                    request=request,
                    context=context,
                    template=context['template'],
                )
            else:
                return HttpResponse(status=400)
    else:
        return HttpResponse(status=400)

def exhibit_card_form(request: HttpRequest, pk: int, card_type: str) -> HttpResponse:
    context : Dict[str, Any] = {'exhibit_id' : pk}
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    if card_type == "text":
        context['form'] = CardForm()
        return TemplateResponse(
            template="archive/components/card-form.html",
            request=request,
            context=context,
        )
    elif card_type == "photo":
        context['form'] = PhotoCardForm()
        if exhibit.collection:
            context['form'].fields['photo'].queryset = exhibit.collection.photos.all()
        else:
            context['form'].fields['photo'].queryset = Photo.objects.none()
        return TemplateResponse(
            template="archive/components/card-form.html",
            request=request,
            context=context,
        )
    else:
        return HttpResponse("invalid type", status=400)


class ExhibitForm(ModelForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs:
            exhibit = kwargs['instance']
            assert hasattr(self.fields['photo'], 'queryset')
            if exhibit.collection:
                self.fields['photo'].queryset = exhibit.collection.photos.all() | Photo.objects.filter(id=exhibit.photo.id)
            else:
                self.fields['photo'].queryset = Photo.objects.none()

    class Meta:
        model = Exhibit
        fields = ['name', 'title', 'description', 'photo']

@login_required
def exhibit_edit(request : HttpRequest, pk: int) -> HttpResponse:
    context = ArchiveRequest(request=request).common_context
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    cards = exhibit.card_set.all().order_by('order').select_related(
        'photocard',
        'photocard__photo',
        'photocard__photo__donor',
        'photocard__photo__place',
    )
    form = ExhibitForm(instance=exhibit)
    context['form'] = form
    context['exhibit'] = exhibit
    context['cards'] = cards
    return TemplateResponse(request, "archive/exhibit_edit.html", context=context)


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
    )
    context['cards'] = cards
    return TemplateResponse(request, "archive/exhibit.html", context=context)

class ExhibitCreateForm(ModelForm):
    class Meta:
        model = Exhibit
        fields = ['collection']

@login_required
def exhibit_create(request: HttpRequest) -> HttpResponse:
    assert not request.user.is_anonymous
    context = ArchiveRequest(request=request).common_context
    if request.method == "POST":
        form = ExhibitCreateForm(request.POST)
        if form.is_valid():
            exhibit = form.save(commit=False)
            if exhibit.collection.owner == request.user and exhibit.collection.photos.exists():
                exhibit.photo = exhibit.collection.photos.order_by("?")[0]
                exhibit.name = exhibit.collection.name
                exhibit.owner = request.user
                exhibit.save()
                return HttpResponseRedirect(reverse("kronofoto:user-page", kwargs={"username": request.user.username}))
    else:
        form = ExhibitCreateForm()
        assert hasattr(form.fields['collection'], "queryset")
        form.fields['collection'].queryset = Collection.objects.filter(owner=request.user).filter(Exists(Photo.objects.filter(collection__id=OuterRef("id"))))

    context['form'] = form
    context['exhibits'] = Exhibit.objects.filter(owner=request.user)
    return TemplateResponse(request, template='archive/exhibit_list.html', context=context)


@login_required
def exhibit_list(request: HttpRequest) -> HttpResponse:
    assert not request.user.is_anonymous
    areq = ArchiveRequest(request=request)
    context = areq.common_context
    exhibits = Exhibit.objects.filter(owner=request.user).order_by("name")
    context['exhibits'] = exhibits
    context['profile_user'] = request.user
    context['form'] = ExhibitCreateForm()
    context['form'].fields['collection'].queryset = Collection.objects.filter(owner=request.user)
    return TemplateResponse(request, "archive/exhibit_list.html", context=context)
