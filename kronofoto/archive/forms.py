from django import forms
from .models import Tag, PhotoTag, Collection
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class RegisterUserForm(forms.Form):
    username = forms.CharField()
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput())
    password2 = forms.CharField(label='Verify Password', widget=forms.PasswordInput())

    def clean(self):
        data = super().clean()
        if User.objects.filter(username=data['username']).exists():
            self.add_error('username', 'That username is taken')
        validate_password(data['password1'])
        if data['password1'] != data['password2']:
            self.add_error('password1', 'The password fields must be identical')
        return data


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
