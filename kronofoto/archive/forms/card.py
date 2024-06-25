from django.forms import ModelForm, Form, CharField, HiddenInput
from ..models import Card, PhotoCard, Figure

class CardFormType(Form):
    card_type = CharField(required=True, widget=HiddenInput)

class CardForm(ModelForm, CardFormType):
    class Meta:
        model = Card
        fields = ['title', 'description']

class FigureForm(ModelForm, CardFormType):
    parent = CharField(required=True, widget=HiddenInput)
    class Meta:
        model = Figure
        fields = ['caption', 'photo']

class PhotoCardForm(ModelForm, CardFormType):
    class Meta:
        model = PhotoCard
        fields = ['title', 'description', 'photo', 'alignment']
