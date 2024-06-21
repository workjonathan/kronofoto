from django.forms import ModelForm
from ..models import Card, PhotoCard, Figure

class CardForm(ModelForm):
    class Meta:
        model = Card
        fields = ['title', 'description']

class FigureForm(ModelForm):
    class Meta:
        model = Figure
        fields = ['caption', 'photo']

class PhotoCardForm(ModelForm):
    class Meta:
        model = PhotoCard
        fields = ['title', 'description', 'photo', 'alignment']
