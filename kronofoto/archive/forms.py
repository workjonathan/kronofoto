from django import forms
from .models import Tag, PhotoTag, Collection, Term, Donor, Photo
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .search import expression
from .search.parser import Parser, NoExpression
from functools import reduce
from .token import UserEmailVerifier
from django.utils.text import slugify


generate_choices = lambda field: lambda: [('', field.capitalize())] + [(p[field], p[field]) for p in Photo.objects.exclude(**{field: ''}).values(field).distinct().order_by(field)]


class SearchForm(forms.Form):
    query = forms.CharField(required=False, label='')
    query.widget.attrs.update({
        'id': 'search-box',
        'placeholder': 'Keywords, terms, photo ID#, donor',
    })
    query.group = "QUERY"

    term = forms.ModelChoiceField(required=False, label='', queryset=Term.objects.all().order_by('term'))
    term.group = "CATEGORY"

    startYear = forms.IntegerField(required=False, label='', widget=forms.NumberInput(attrs={'placeholder': 'Start'}) )
    startYear.group = 'DATE RANGE'
    endYear = forms.IntegerField(required=False, label='', widget=forms.NumberInput(attrs={'placeholder': 'End'}) )
    endYear.group = 'DATE RANGE'

    donor = forms.ModelChoiceField(required=False, label='', queryset=Donor.objects.filter_donated())
    donor.group = "DONOR"

    city = forms.ChoiceField(required=False, label='', choices=generate_choices('city'))
    city.group = 'LOCATION'
    county = forms.ChoiceField(required=False, label='', choices=generate_choices('county'))
    county.group = 'LOCATION'
    state = forms.ChoiceField(required=False, label='', choices=generate_choices('state'))
    state.group = 'LOCATION'
    country = forms.ChoiceField(required=False, label='', choices=generate_choices('country'))
    country.group = 'LOCATION'

    def as_expression(self):
        form_exprs = []
        year_exprs = []
        try:
            parser = Parser.tokenize(self.cleaned_data['query'])
            form_exprs.append(parser.parse().shakeout())
        except NoExpression:
            pass
        except:
            try:
                form_exprs.append(parser.simple_parse().shakeout())
            except NoExpression:
                pass
        if self.cleaned_data['term']:
            form_exprs.append(expression.TermExactly(self.cleaned_data['term']))
        if self.cleaned_data['startYear']:
            year_exprs.append(expression.YearGTE(self.cleaned_data['startYear']))
        if self.cleaned_data['endYear']:
            year_exprs.append(expression.YearLTE(self.cleaned_data['endYear']))
        if len(year_exprs) > 0:
            form_exprs.append(reduce(expression.And, year_exprs))
        if self.cleaned_data['donor']:
            form_exprs.append(expression.DonorExactly(self.cleaned_data['donor']))
        if self.cleaned_data['city']:
            form_exprs.append(expression.City(self.cleaned_data['city']))
        if self.cleaned_data['state']:
            form_exprs.append(expression.State(self.cleaned_data['state']))
        if self.cleaned_data['country']:
            form_exprs.append(expression.Country(self.cleaned_data['country']))
        if len(form_exprs):
            return reduce(expression.Or, form_exprs)
        raise NoExpression


class RegisterUserForm(forms.Form):
    email = forms.EmailField()
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput())
    password2 = forms.CharField(label='Verify Password', widget=forms.PasswordInput())

    def __init__(self, user_checker=UserEmailVerifier(), **kwargs):
        self.user_checker = user_checker
        super().__init__(**kwargs)

    def clean(self):
        data = super().clean()
        if 'email' in data and User.objects.filter(username=data['email']).exists():
            self.add_error('email', 'There is already an account associated with that email address.')
        if 'password1' in data:
            validate_password(data['password1'])
            if 'password2' not in data or data['password1'] != data['password2']:
                self.add_error('password1', 'The password fields must be identical')
        return data

    def create_user(self):
        username = self.cleaned_data['email']
        password = self.cleaned_data['password1']
        user = User.objects.create_user(username, password=password, email=username, is_active=False)
        self.user_checker.verify(user)


class TagForm(forms.Form):
    tag = forms.CharField()

    def add_tag(self, photo, user):
        text = self.cleaned_data['tag']
        tag, _ = Tag.objects.get_or_create(slug=slugify(text), defaults={'tag': text})
        accepted = (
            user.has_perm('archive.add_tag') and
            user.has_perm('archive.change_tag') and
            user.has_perm('archive.add_phototag') and
            user.has_perm('archive.change_phototag')
        )
        phototag, created = PhotoTag.objects.update_or_create(tag=tag, photo=photo, defaults={'accepted': accepted})
        phototag.creator.add(user)
        phototag.save()


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
