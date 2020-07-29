from django import forms
from .models import Tag, PhotoTag, Collection, Term, Donor, Photo
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


generate_choices = lambda field: lambda: [('', field.capitalize())] + [(p[field], p[field]) for p in Photo.objects.exclude(**{field: ''}).values(field).distinct().order_by(field)]


class SearchForm(forms.Form):
    query = forms.CharField(required=False)
    term = forms.ModelChoiceField(required=False, queryset=Term.objects.all().order_by('term'))
    startYear = forms.IntegerField(required=False)
    endYear = forms.IntegerField(required=False)
    donor = forms.ModelChoiceField(required=False, queryset=Donor.objects.all().order_by('last_name', 'first_name'))
    city = forms.ChoiceField(required=False, choices=generate_choices('city'))
    county = forms.ChoiceField(required=False, choices=generate_choices('county'))
    state = forms.ChoiceField(required=False, choices=generate_choices('state'))
    country = forms.ChoiceField(required=False, choices=generate_choices('country'))


class RegisterUserForm(forms.Form):
    email = forms.EmailField()
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput())
    password2 = forms.CharField(label='Verify Password', widget=forms.PasswordInput())

    def clean(self):
        data = super().clean()
        if 'email' in data and User.objects.filter(username=data['email']).exists():
            self.add_error('email', 'There is already an account associated with that email address.')
        if 'password1' in data:
            validate_password(data['password1'])
            if 'password2' not in data or data['password1'] != data['password2']:
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
