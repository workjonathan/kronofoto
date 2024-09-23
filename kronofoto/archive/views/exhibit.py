from django.contrib.auth.decorators import user_passes_test
from functools import cached_property
from ..models import Photo, Exhibit, Card, Collection, PhotoCard
from django.shortcuts import get_object_or_404
from django.db.models.functions import Length
from django.db.models import QuerySet, Exists, OuterRef, Max, F, Q
from django.db import transaction
from django.template.response import TemplateResponse
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, QueryDict
from django.core.exceptions import PermissionDenied
from ..reverse import reverse
from .base import ArchiveRequest
from typing import Dict, Any, Iterator, Union, List, Optional, Tuple
from django.template.defaultfilters import linebreaksbr, linebreaks_filter
from django.contrib.auth.decorators import login_required
from django.forms import ModelForm, ModelChoiceField, Form, IntegerField
from django import forms
from ..templatetags.widgets import card_tag, image_url
from ..forms import CardForm, PhotoCardForm, FigureForm, CardFormType, CardFormWrapper, PhotoCardFormWrapper, FigureForm, FigureFormWrapper
import json
import uuid
from dataclasses import dataclass
from collections import defaultdict

def exhibit_figure_form(request: HttpRequest, pk: int, parent: str) -> HttpResponse:
    context = {}
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    context['form'] = FigureForm(prefix=str(uuid.uuid4()), initial={"card_type": "figure", "parent": parent})
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

class FigureCountForm(Form):
    count = IntegerField(required=False)


def exhibit_card_form(request: HttpRequest, pk: int, card_type: str) -> HttpResponse:
    context : Dict[str, Any] = {'exhibit_id' : pk}
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    context['exhibit'] = exhibit
    context['edit'] = True
    if card_type == "text":
        parent_uuid = str(uuid.uuid4())
        cardform = CardForm(initial={'card_type': "text"}, prefix=parent_uuid)
        figures = []
        form = FigureCountForm(request.GET, initial={"count": 0})
        if form.is_valid() and form.cleaned_data['count']:
            context['styles'] = {
                'border-top': '1px solid #ffffff',
            }
            figures = [
                FigureFormWrapper(FigureForm(prefix=str(uuid.uuid4()), initial={"parent": parent_uuid, "card_type": "figure"}))
                for _ in range(form.cleaned_data['count'])
            ]
        context['card'] = CardFormWrapper(form=cardform, figures=figures)
        context['form'] = cardform
        return TemplateResponse(
            template="archive/components/text-card.html",
            request=request,
            context=context,
        )
    elif card_type == "photo":
        alignment = int(request.GET.get("align", "2"))
        context['form'] = PhotoCardForm(initial={'card_type': 'photo', "alignment": alignment}, prefix=str(uuid.uuid4()))

        if alignment in (2,3):
            template = 'archive/components/two-column-card.html'
            context['image_area_classes'] = (
                ['two-column--image-left', 'two-column--variation-1']
                if alignment == PhotoCard.Alignment.LEFT
                else ['two-column--image-right', 'two-column--variation-2']
            )
        else:
            template = 'archive/components/full-image-card.html'
            image_area_classes = ['full-image-area--contain']

        return TemplateResponse(
            template=template,
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
            subq = Collection.objects.filter(id=exhibit.collection.id, photos=OuterRef("id"))
            q = Exists(subq) | Q(id=exhibit.photo.id)
            if exhibit.collection:
                self.fields['photo'].queryset = Photo.objects.filter(q)
            else:
                self.fields['photo'].queryset = Photo.objects.none()

    class Meta:
        model = Exhibit
        fields = ['name', 'title', 'description', 'photo', "credits"]

@dataclass
class ExhibitFormWrapper:
    form: ExhibitForm

    @property
    def pk(self) -> int:
        return self.form.instance.pk

    @property
    def id(self) -> int:
        return self.form.instance.id

    @property
    def name(self) -> str:
        return self.form['name'].value() or ""

    @property
    def credits(self) -> str:
        print(f"{self.form['credits'].value()=}")
        return self.form['credits'].value() or ""

    @property
    def title(self) -> str:
        return self.form['title'].value() or ""

    @property
    def photo(self) -> Optional[Photo]:
        val = self.form['photo'].value()
        if val:
            try:
                return Photo.objects.get(pk=val)
            except Photo.DoesNotExist:
                return None

        else:
            return None

    @property
    def description(self) -> str:
        return self.form['description'].value() or ""


def exhibit_two_column_image(request: HttpRequest, pk: int) -> HttpResponse:
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    target_id = request.GET.get("field")
    html_name = request.GET.get("html_name", "")
    try:
        photo_id = int(request.GET.get(html_name, ""))
        photo = get_object_or_404(Photo.objects.all(), pk=photo_id)
        form = {'photo': {'auto_id': target_id, 'html_name': html_name } }
        context = {
            "form": form,
            "edit": True,
            "photo": photo,
            "target_id": target_id,
            "exhibit": exhibit,
            "html_name": html_name
        }
        return TemplateResponse(request=request, context=context, template="archive/components/two-column-image.html", headers={"Hx-Trigger": "remove-empty"})
    except ValueError:
        return HttpResponse("", status=400)

def exhibit_figure_image(request: HttpRequest, pk: int) -> HttpResponse:
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    target_id = request.GET.get("field")
    html_name = request.GET.get("html_name", "")
    try:
        photo_id = int(request.GET.get(html_name, ""))
        photo = get_object_or_404(Photo.objects.all(), pk=photo_id)
        context = {
            "form": True,
            "edit": True,
            "photo": photo,
            "target_id": target_id,
            "exhibit": exhibit,
            "html_name": html_name
        }
        return TemplateResponse(request=request, context=context, template="archive/components/figure-image.html", headers={"Hx-Trigger": "remove-empty"})
    except ValueError:
        return HttpResponse("", status=400)

@login_required
def exhibit_full_image(request: HttpRequest) -> HttpResponse:
    html_name = request.GET.get("html_name", "")
    try:
        photo_id = int(request.GET.get(html_name, ""))
        photo = get_object_or_404(Photo.objects.all(), pk=photo_id)
        context = {
            "photo": photo
        }
        return TemplateResponse(
            request=request,
            context=context,
            template="archive/components/full-image.html",
        )
    except ValueError:
        return HttpResponse("", status=400)

@login_required
def exhibit_images(request: HttpRequest, pk: int) -> HttpResponse:
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    context : Dict[str, Any] = {}
    context['collection'] = exhibit.collection
    context['target'] = request.GET['target']

    return TemplateResponse(
        request=request,
        context=context,
        template="archive/components/images.html",
        headers={
            "Hx-Trigger": json.dumps({
                "kronofoto:modal:reveal": {
                },
            }),
        }
    )

@transaction.atomic
@login_required
def exhibit_edit(request : HttpRequest, pk: int) -> HttpResponse:
    assert not request.user.is_anonymous
    form : Any
    context = ArchiveRequest(request=request).common_context
    exhibit = get_object_or_404(Exhibit.objects.all(), pk=pk)
    if exhibit.owner.pk != request.user.pk:
        return HttpResponse("", status=400)
    form = ExhibitForm(instance=exhibit) # type: ignore
    context['exhibit'] = ExhibitFormWrapper(form)
    cards : Union[QuerySet[Card], List[Any]]
    if request.method == 'POST':
        card_types = [CardFormType(request.POST, prefix=prefix) for prefix in request.POST.getlist("prefix")]
        if all(typeform.is_valid() for typeform in card_types):
            forms = [
                CardForm(request.POST, prefix=form.prefix) if form.cleaned_data['card_type'] == 'text'
                else FigureForm(request.POST, prefix=form.prefix) if form.cleaned_data['card_type'] == 'figure'
                else PhotoCardForm(request.POST, prefix=form.prefix)
                for form in card_types
            ]
            cards = []
            figure_forms : Dict[str, List[Form]] = defaultdict(list)
            for form in forms:
                if form['card_type'].value() == 'figure':
                    matching_forms = figure_forms[form['parent'].value() or ""]
                    matching_forms.append(FigureFormWrapper(form)) # type: ignore
                    figure_forms[form['parent'].value() or ""] = matching_forms
            forms = []
            for form in card_types:
                if form.cleaned_data['card_type'] == "text":
                    card_form: ModelForm = CardForm(request.POST, prefix=form.prefix)
                    cards.append(CardFormWrapper(form=card_form, figures=figure_forms[form.prefix])) # type: ignore
                    forms.append(card_form)
                elif form.cleaned_data['card_type'] == "photo":
                    card_form = PhotoCardForm(request.POST, prefix=form.prefix)
                    cards.append(PhotoCardFormWrapper(form=card_form))
                    forms.append(card_form)
                else:
                    card_form = FigureForm(request.POST, prefix=form.prefix)
                    forms.append(card_form)
            context['cards'] = cards
            form = ExhibitForm(request.POST, instance=exhibit)
            context['exhibit'] = ExhibitFormWrapper(form)
            if all(form_.is_valid() for form_ in forms) and form.is_valid() and 'save' in request.POST and request.POST['save'] == "Save":
                form.save()
                from archive.models import Figure
                exhibit.card_set.all().delete()
                card_objs = {}
                for order, card_form in enumerate(forms):
                    if card_form.cleaned_data['card_type'] != 'figure':
                        card = card_form.save(commit=False)
                        card_objs[card_form.prefix] = card
                        card.exhibit = exhibit
                        card.order = order
                        card.card_style = 0
                        card.save()
                for order, card_form in enumerate(forms):
                    if card_form.cleaned_data['card_type'] == 'figure':
                        figure = card_form.save(commit=False)
                        figure.card = card_objs[card_form.cleaned_data['parent']]
                        figure.order = order
                        figure.save()
                return HttpResponseRedirect(reverse("kronofoto:user-page", kwargs={"username": request.user.username}))
            else:
                two_column_count = 0
                objs = []
                obj_context = CardContext()
                for i, card in enumerate(cards):
                    if 'preview' in request.POST:
                        obj, two_column_count = obj_context.context(card=card, i=i, two_column_count=two_column_count, mode="PREVIEW")
                    else:
                        obj, two_column_count = obj_context.context(card=card, i=i, two_column_count=two_column_count, mode="EDIT_POST")
                    objs.append(obj)
                context['cards'] = objs
                context['form'] = form
                if 'preview' in request.POST:
                    context['edit'] = False
                    return TemplateResponse(request, "archive/exhibit.html", context=context)
                else:
                    return TemplateResponse(request, "archive/exhibit_edit.html", context=context)
    cards = exhibit.card_set.all().order_by('order').select_related(
        'photocard',
        'photocard__photo',
        'photocard__photo__donor',
        'photocard__photo__place',
    )
    objs = []
    two_column_count = 0
    obj_context = CardContext()
    for i, card in enumerate(cards):
        obj, two_column_count = obj_context.context(card=card, two_column_count=two_column_count, i=i, mode="EDIT_GET")
        objs.append(obj)
    context['form'] = form
    context['cards'] = objs
    context['exhibit'] = exhibit
    return TemplateResponse(request, "archive/exhibit_edit.html", context=context)

@dataclass
class CardContext:
    def context(self, *, card: Union[Card, CardFormWrapper, PhotoCardFormWrapper], i: int, two_column_count: int, mode: str) -> Tuple[Dict[str, Any], int]:
        is_edit = mode != "DISPLAY" and mode != "PREVIEW"
        obj : Dict[str, Any] = {
            "zindex": 20 - i,
            "edit": is_edit,
        }
        if mode == "DISPLAY":
            assert isinstance(card, Card)
            if hasattr(card, 'photocard'):
                card = card.photocard
                obj['card'] = card
                obj['image_area_classes'] = []
                if card.alignment == PhotoCard.Alignment.FULL:
                    obj['template'] = 'archive/components/full-image-card.html'
                else:
                    obj['template'] = 'archive/components/two-column-card.html'
                    obj['image_area_classes'] += (
                        ['two-column--image-left', 'two-column--variation-1']
                        if card.alignment == PhotoCard.Alignment.LEFT
                        else ['two-column--image-right', 'two-column--variation-2']
                    )
                    if two_column_count % 2 == 0:
                        obj['image_area_classes'].append("two-column--alt")
                    two_column_count += 1
                if card.fill_style == PhotoCard.Fill.CONTAIN:
                    obj['image_area_classes'] += ['full-image-area--contain']
                else:
                    obj['image_area_classes'] += ['full-image-area--cover']
            else:
                if card.figure_set.all().exists():
                    obj['styles'] = {
                        'border-top': '1px solid #ffffff',
                    }

                obj['card'] = card
                obj['template'] = 'archive/components/text-card.html'
                obj['content_attrs'] = {
                    'data-aos': 'fade-up',
                    'data-aos-duration': '1000',
                }
        elif mode == "EDIT_GET":
            assert isinstance(card, Card)
            if hasattr(card, 'photocard'):
                card = card.photocard
                photoform = PhotoCardForm(instance=card, initial={"card_type": "photo"}, prefix=str(uuid.uuid4()))
                obj['form'] = photoform
                obj['card'] = PhotoCardFormWrapper(form=photoform)
                obj['image_area_classes'] = []
                if card.alignment == PhotoCard.Alignment.FULL:
                    obj['template'] = 'archive/components/full-image-card.html'
                else:
                    obj['template'] = 'archive/components/two-column-card.html'
                    obj['image_area_classes'] += (
                        ['two-column--image-left', 'two-column--variation-1']
                        if card.alignment == PhotoCard.Alignment.LEFT
                        else ['two-column--image-right', 'two-column--variation-2']
                    )
                    if two_column_count % 2 == 0:
                        obj['image_area_classes'].append("two-column--alt")
                    two_column_count += 1
                if card.fill_style == PhotoCard.Fill.CONTAIN:
                    obj['image_area_classes'] += ['full-image-area--contain']
                else:
                    obj['image_area_classes'] += ['full-image-area--cover']
            else:
                figures = []
                parent_uuid = str(uuid.uuid4())
                for figure in card.figure_set.all().order_by('order'):
                    obj['styles'] = {
                        'border-top': '1px solid #ffffff',
                    }
                    figures.append(
                        FigureFormWrapper(
                            FigureForm(
                                prefix=str(uuid.uuid4()),
                                initial={"parent": parent_uuid, "card_type": "figure"},
                                instance=figure,
                            )
                        )
                    )

                cardform = CardForm(instance=card, initial={"card_type": "text"}, prefix=parent_uuid)
                obj['form'] = cardform
                obj['card'] = CardFormWrapper(form=cardform, figures=figures)
                obj['template'] = 'archive/components/text-card.html'
                obj['content_attrs'] = {
                    'data-aos': 'fade-up',
                    'data-aos-duration': '1000',
                }
        else: # EDIT_POST
            assert not isinstance(card, Card)
            if card.form['card_type'].value() == 'text':
                assert isinstance(card, CardFormWrapper)
                obj['form'] = card.form
                obj['card'] = card
                obj['template'] = 'archive/components/text-card.html'
                obj['content_attrs'] = {
                    'data-aos': 'fade-up',
                    'data-aos-duration': '1000',
                }
            else:
                assert isinstance(card, PhotoCardFormWrapper)
                obj['form'] = card.form
                obj['card'] = card
                obj['image_area_classes'] = []
                if card.alignment == PhotoCard.Alignment.FULL:
                    obj['template'] = 'archive/components/full-image-card.html'
                else:
                    obj['template'] = 'archive/components/two-column-card.html'
                    obj['image_area_classes'] += (
                        ['two-column--image-left', 'two-column--variation-1']
                        if card.alignment == PhotoCard.Alignment.LEFT
                        else ['two-column--image-right', 'two-column--variation-2']
                    )
                    if two_column_count % 2 == 0:
                        obj['image_area_classes'].append("two-column--alt")
                    two_column_count += 1
                if card.fill_style == PhotoCard.Fill.CONTAIN:
                    obj['image_area_classes'] += ['full-image-area--contain']
                else:
                    obj['image_area_classes'] += ['full-image-area--cover']
        return obj, two_column_count

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
    objs = []
    obj_context = CardContext()
    two_column_count = 0
    for i, card in enumerate(cards):
        obj, two_column_count = obj_context.context(card=card, two_column_count=two_column_count, i=i, mode="DISPLAY")
        objs.append(obj)
    context['cards'] = objs
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
