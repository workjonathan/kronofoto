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
from ..forms import CardForm, PhotoCardForm, FigureForm, CardFormType
import json
import uuid

def exhibit_figure_form(request: HttpRequest, pk: int, parent: str) -> HttpResponse:
    context = {}
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    context['form'] = FigureForm(prefix=str(uuid.uuid1()), initial={"card_type": "figure", "parent": parent})
    assert hasattr(context['form'].fields['photo'], 'queryset')
    if exhibit.collection:
        context['form'].fields['photo'].queryset = exhibit.collection.photos.all()
    else:
        context['form'].fields['photo'].queryset = Photo.objects.none()
    return TemplateResponse(
        template="archive/components/figure-form.html",
        request=request,
        context=context,
    )

def exhibit_card_form(request: HttpRequest, pk: int, card_type: str) -> HttpResponse:
    context : Dict[str, Any] = {'exhibit_id' : pk}
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    if card_type == "text":
        context['form'] = CardForm(initial={'card_type': "text"}, prefix=str(uuid.uuid1()))
        return TemplateResponse(
            template="archive/components/text-card.html",
            request=request,
            context=context,
        )
    elif card_type == "photo":
        context['form'] = PhotoCardForm(initial={'card_type': 'photo'}, prefix=str(uuid.uuid1()))
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

@transaction.atomic
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
    if request.method == 'POST':
        body_data = QueryDict(request.body)
        card_types = [CardFormType(request.POST, prefix=prefix) for prefix in body_data.getlist("prefix")]
        if all(typeform.is_valid() for typeform in card_types):
            forms = [
                CardForm(request.POST, prefix=form.prefix) if form.cleaned_data['card_type'] == 'text'
                else FigureForm(request.POST, prefix=form.prefix) if form.cleaned_data['card_type'] == 'figure'
                else PhotoCardForm(request.POST, prefix=form.prefix)
                for form in card_types
            ]
            if all(form.is_valid() for form in forms):
                from archive.models import Figure
                print(Figure.objects.all().count())
                exhibit.card_set.all().delete()
                print(Figure.objects.all().count())
                card_objs = {}
                for order, form in enumerate(forms):
                    if form.cleaned_data['card_type'] != 'figure':
                        card = form.save(commit=False)
                        card_objs[form.prefix] = card
                        card.exhibit = exhibit
                        card.order = order
                        card.card_style = 0
                        card.save()
                for order, form in enumerate(forms):
                    if form.cleaned_data['card_type'] == 'figure':
                        figure = form.save(commit=False)
                        figure.card = card_objs[form.cleaned_data['parent']]
                        figure.order = order
                        figure.save()
            else:
                print('not valid?')
        else:
            print('not valid?')
    form = ExhibitForm(instance=exhibit) # type: ignore
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
