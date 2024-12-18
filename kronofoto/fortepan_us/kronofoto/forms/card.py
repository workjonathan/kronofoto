from django.forms import ModelForm, Form, CharField, HiddenInput, RadioSelect, IntegerField
from django.db.models import QuerySet
from fortepan_us.kronofoto.models import Card, PhotoCard, Figure, Photo
from dataclasses import dataclass, field
from typing import Optional, List



class CardFormType(Form):
    cardform_type = CharField(required=True, widget=HiddenInput)

class CardForm(ModelForm, CardFormType):
    figure_count = IntegerField(required=False, widget=HiddenInput)

    def clean_figure_count(self) -> int:
        return self.cleaned_data.get('figure_count', 0)

    class Meta:
        model = Card
        fields = ['title', 'description', "smalltext", 'photo', 'fill_style', "card_type"]
        widgets = {
            "fill_style": RadioSelect,
            "title": HiddenInput(attrs={"x-model": "title"}),
            "description": HiddenInput(attrs={"x-model": "description"}),
            "smalltext": HiddenInput(attrs={"x-model": "smalltext"}),
            "photo": HiddenInput(attrs={"@change": "hasChanges = true"}),
            "card_type": HiddenInput,
        }

FigureListForm = CardForm

class FigureForm(ModelForm, CardFormType):
    parent = CharField(required=True, widget=HiddenInput)
    class Meta:
        model = Figure
        fields = ['caption', 'photo']
        widgets = {
            "caption": HiddenInput(attrs={"x-model": "caption"}),
            "photo": HiddenInput(attrs={"@change": "hasChanges = true"}),
        }

PhotoCardForm = CardForm

@dataclass
class CardFormWrapper:
    form: ModelForm
    figures: "List[FigureFormWrapper]" = field(default_factory=list)

    @property
    def figure_set(self) -> QuerySet[Figure]:
        return self.form.instance.figure_set

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
    def title(self) -> str:
        return self.form['title'].value() or ""

    @property
    def figure_count(self) -> int:
        try:
            return int(self.form['figure_count'].value())
        except ValueError:
            return 0

    @property
    def card_type(self) -> int:
        try:
            return int(self.form['card_type'].value())
        except ValueError:
            return 0

    @property
    def fill_style(self) -> int:
        try:
            return int(self.form['fill_style'].value())
        except ValueError:
            return 1
    @property
    def card(self) -> "CardFormWrapper":
        return self

    @property
    def id(self) -> int:
        return self.form.instance.id

    @property
    def description(self) -> str:
        return self.form['description'].value() or ""

    @property
    def smalltext(self) -> str:
        return self.form['smalltext'].value() or ""

PhotoCardFormWrapper = CardFormWrapper
FigureListFormWrapper = CardFormWrapper

@dataclass
class FigureFormWrapper:
    form: ModelForm

    @property
    def caption(self) -> str:
        return self.form['caption'].value() or ""

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
