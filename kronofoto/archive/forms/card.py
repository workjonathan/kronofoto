from django.forms import ModelForm
from ..models import Card, PhotoCard

class CardForm(ModelForm):
    class Meta:
        model = Card
        fields = ['title', 'description']

class PhotoCardForm(ModelForm):
    class Meta:
        model = PhotoCard
        fields = ['title', 'description', 'photo', 'alignment']
