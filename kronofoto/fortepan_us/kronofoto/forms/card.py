from django.forms import ModelForm, Form, CharField, HiddenInput, RadioSelect
from django.db.models import QuerySet
from fortepan_us.kronofoto.models import Card, PhotoCard, Figure, Photo
from dataclasses import dataclass, field
from typing import Optional, List



class CardFormType(Form):
    cardform_type = CharField(required=True, widget=HiddenInput)

class CardForm(ModelForm, CardFormType):
    class Meta:
        model = Card
        fields = ['title', 'description', "smalltext"]
        widgets = {
            "title": HiddenInput(attrs={"x-model": "title"}),
            "description": HiddenInput(attrs={"x-model": "description"}),
            "smalltext": HiddenInput(attrs={"x-model": "smalltext"}),
        }

class FigureListForm(ModelForm, CardFormType):
    class Meta:
        model = Card
        fields: List[str] = []

class FigureForm(ModelForm, CardFormType):
    parent = CharField(required=True, widget=HiddenInput)
    class Meta:
        model = Figure
        fields = ['caption', 'photo']
        widgets = {
            "caption": HiddenInput(attrs={"x-model": "caption"}),
            "photo": HiddenInput(attrs={"@change": "hasChanges = true"}),
        }

class PhotoCardForm(ModelForm, CardFormType):
    class Meta:
        model = PhotoCard
        fields = ['title', 'description', "smalltext", 'photo', 'fill_style', "card_type"]
        widgets = {
            "fill_style": RadioSelect,
            "title": HiddenInput(attrs={"x-model": "title"}),
            "description": HiddenInput(attrs={"x-model": "description"}),
            "smalltext": HiddenInput(attrs={"x-model": "smalltext"}),
            "photo": HiddenInput(attrs={"@change": "hasChanges = true"}),
            "card_type": HiddenInput,
        }

@dataclass
class FigureListFormWrapper:
    form: ModelForm
    figures: "List[FigureFormWrapper]" = field(default_factory=list)

    @property
    def figure_set(self) -> QuerySet[Figure]:
        return self.form.instance.figure_set

    @property
    def card(self) -> "FigureListFormWrapper":
        return self

    @property
    def id(self) -> int:
        return self.form.instance.id

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



@dataclass
class PhotoCardFormWrapper:
    form: ModelForm

    @property
    def title(self) -> str:
        return self.form['title'].value() or ""

    @property
    def fill_style(self) -> int:
        try:
            return int(self.form['fill_style'].value())
        except ValueError:
            return 1

    @property
    def card_type(self) -> int:
        try:
            return int(self.form['card_type'].value())
        except ValueError:
            return 1

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

    @property
    def smalltext(self) -> str:
        return self.form['smalltext'].value() or ""

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
