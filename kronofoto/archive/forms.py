from django import forms
from .models import Tag, PhotoTag, Collection

class TagForm(forms.Form):
    tag = forms.CharField()

    def add_tag(self, photo):
        tag, _ = Tag.objects.get_or_create(tag=self.cleaned_data['tag'])
        phototag = PhotoTag.objects.get_or_create(tag=tag, photo=photo, defaults={'accepted': False})

class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['name', 'visibility']

class AddToListForm(forms.Form):
    collection = forms.ChoiceField(required=False)
    name = forms.CharField(required=False)
    visibility = forms.ChoiceField(required=False, choices=Collection.PRIVACY_TYPES)

    def __init__(self, *args, **kwargs):
        self.collection = kwargs.pop('collections')
        super().__init__(*args, **kwargs)
        self.fields['collection'].choices = self.collection

    def clean(self):
        data = super().clean()
        if not data['collection'] and not data['name']:
            self.add_error('name', 'A name must be provided')
        return data
