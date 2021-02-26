from django import forms
from .models import Tag, PhotoTag, Collection, Term, Donor, Photo
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .search import expression
from .search.parser import Parser, NoExpression, BasicParser
from functools import reduce
from .token import UserEmailVerifier
from django.utils.text import slugify
from django.core.cache import cache


class LocationChoiceField(forms.ChoiceField):
    def __init__(self, field, *args, **kwargs):
        self.field = field
        super().__init__(*args, choices=[], **kwargs)

    def load_choices(self):
        key = 'form:' + self.field
        self.choices = cache.get(key, default=[])
        if not self.choices:
            self.choices = list(self.get_choices())
            cache.set(key, self.choices)

    def get_choices(self):
        yield ('', self.field.capitalize())
        yield from ((p[self.field], p[self.field]) for p in Photo.objects.filter(is_published=True, year__isnull=False).exclude(**{self.field: ''}).only(self.field).values(self.field).distinct().order_by(self.field))


class SearchForm(forms.Form):
    basic = forms.CharField(required=False, label='')
    basic.group = 'BASIC'
    basic.widget.attrs.update({
        'placeholder': 'Search...',
    })
    tag = forms.CharField(required=False, label='')
    tag.group = 'TAG'
    tag.widget.attrs.update({
        'id': 'search-box',
        'placeholder': 'Tag Search',
    })
    term = forms.ModelChoiceField(required=False, label='', queryset=Term.objects.all().order_by('term'))
    term.group = "CATEGORY"

    startYear = forms.IntegerField(required=False, label='', widget=forms.NumberInput(attrs={'placeholder': 'Start'}) )
    startYear.group = 'DATE RANGE'
    endYear = forms.IntegerField(required=False, label='', widget=forms.NumberInput(attrs={'placeholder': 'End'}) )
    endYear.group = 'DATE RANGE'

    donor = forms.ModelChoiceField(required=False, label='', queryset=Donor.objects.filter_donated())
    donor.group = "DONOR"

    city = LocationChoiceField(required=False, label='', field='city')
    city.group = 'LOCATION'
    county = LocationChoiceField(required=False, label='', field='county')
    county.group = 'LOCATION'
    state = LocationChoiceField(required=False, label='', field='state')
    state.group = 'LOCATION'
    country = LocationChoiceField(required=False, label='', field='country')
    country.group = 'LOCATION'

    query = forms.CharField(required=False, label='')
    query.widget.attrs.update({
        'placeholder': 'Keywords, terms, photo ID#, donor',
    })
    query.group = "ADVANCED SEARCH"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].load_choices()
        self.fields['county'].load_choices()
        self.fields['state'].load_choices()
        self.fields['country'].load_choices()

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
        if self.cleaned_data['basic']:
            try:
                form_exprs.append(BasicParser.tokenize(self.cleaned_data['basic']).parse())
            except NoExpression:
                pass

        if self.cleaned_data['term']:
            form_exprs.append(expression.TermExactly(self.cleaned_data['term']))
        if self.cleaned_data['tag']:
            form_exprs.append(expression.TagExactly(self.cleaned_data['tag']))
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
        if self.cleaned_data['county']:
            form_exprs.append(expression.County(self.cleaned_data['county']))
        if self.cleaned_data['state']:
            form_exprs.append(expression.State(self.cleaned_data['state']))
        if self.cleaned_data['country']:
            form_exprs.append(expression.Country(self.cleaned_data['country']))
        if len(form_exprs):
            return reduce(expression.And, form_exprs)
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

    def clean(self):
        data = super().clean()
        data['tag'] = [s.strip() for s in data['tag'].split(', ')]
        for text in data['tag']:
            if Term.objects.filter(slug=slugify(text)).exists():
                self.add_error('tag', 'Tags which are already categories are not allowed: {}'.format(text))
        return data


    def add_tag(self, photo, user):
        for text in self.cleaned_data['tag']:
            tag, _ = Tag.objects.get_or_create(slug=slugify(text), defaults={'tag': text})
            accepted = (
                user.has_perm('archive.add_tag') and
                user.has_perm('archive.change_tag') and
                user.has_perm('archive.add_phototag') and
                user.has_perm('archive.change_phototag')
            )
            phototag, created = PhotoTag.objects.get_or_create(tag=tag, photo=photo, defaults={'accepted': accepted})
            if not created:
                phototag.accepted |= accepted
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
