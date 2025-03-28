from django import forms
from .photosphere import PhotoSphereInfoInlineForm
from fortepan_us.kronofoto.models import Tag, PhotoTag, Collection, Term, Donor, Photo, PhotoSphere, PhotoSpherePair, Place
from fortepan_us.kronofoto.search import expression
from django.contrib.auth.models import User
from fortepan_us.kronofoto.search.parser import Parser, NoExpression, BasicParser
from functools import reduce
from django.utils.text import slugify
from django.core.cache import cache
from django.conf import settings
from fortepan_us.kronofoto.widgets import HeadingWidget, PositioningWidget, Select2
from fortepan_us.kronofoto.models.photosphere import IncompleteGPSInfo
from fortepan_us.kronofoto.fields import RecaptchaField
from .photobase import PhotoForm, SubmissionForm, ArchiveSubmissionForm
from .card import CardForm, PhotoCardForm, FigureForm, CardFormType, PhotoCardFormWrapper, CardFormWrapper, FigureFormWrapper, FigureListForm, FigureListFormWrapper
from fortepan_us.kronofoto.reverse import reverse_lazy
from dataclasses import dataclass
from typing import Any, List, Dict, Optional, Union, Generator, Tuple, TypeVar, Type

class AgreementForm(forms.Form):
    agree = forms.BooleanField(required=True, label="I agree to these terms")
    captcha = RecaptchaField(required_score=0.55)

class WebComponentForm(forms.Form):
    CHOICES = [
        ('random', "Timeline view (random image)"),
        ('image', "Timeline view (current image)"),
        ('results', "Grid view"),
    ]
    page = forms.ChoiceField(
        widget=forms.Select(),
        initial="image",
        choices=CHOICES,
        label="View-type"
    )

    text_field1 = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={'placeholder': 'your embed title'}),
        max_length=100,
        required=False
    )

    text_field2 = forms.CharField(
        label="",
        max_length=100,
        initial='Photos of camping, Ankeney, Iowa',
        required=False
    )

class ListVisibilityForm(forms.Form):
    is_private = forms.BooleanField(label="Make Private", label_suffix="", required=False)
    is_private.widget.attrs.update({
        "class": "switch-input",
    })

class ListForm(forms.Form):
    name = forms.CharField(label="create a new FotoAlbum")
    name.widget.attrs['placeholder'] = "New FotoAlbum name"
    is_private = forms.BooleanField(label="Make Private", label_suffix="", required=False)
    is_private.widget.attrs.update({
        "class": "switch-input",
    })

class ListMemberForm(forms.Form):
    membership = forms.BooleanField(required=False, label_suffix="")
    collection = forms.IntegerField(widget=forms.HiddenInput())
    def __init__(self, *args: Any, initial: Dict[str, Any], **kwargs: Any):
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
        self.fields['membership'].label = initial['name']


class LocationChoiceField(forms.ChoiceField):
    def __init__(self, field: Any, *args: Any, **kwargs: Any):
        self.field = field
        super().__init__(*args, choices=[], **kwargs)

    def load_choices(self) -> None:
        key = 'form:' + self.field
        self.choices = cache.get(key, default=[])
        if not self.choices:
            self.choices = list(self.get_choices())
            cache.set(key, self.choices)

    def get_choices(self) -> Generator:
        yield ('', self.field.capitalize())
        yield from ((p[self.field], p[self.field]) for p in Photo.objects.filter(is_published=True, year__isnull=False).exclude(**{self.field: ''}).only(self.field).values(self.field).distinct().order_by(self.field))


class SearchForm(forms.Form):
    basic = forms.CharField(required=False, label='')
    basic.group = 'BASIC' # type: ignore
    basic.widget.attrs.update({
        'id': 'search-box'
    })
    tag = forms.CharField(required=False, label='')
    tag.group = 'TAG' # type: ignore
    tag.widget.attrs.update({
        'data-autocomplete-url': reverse_lazy("kronofoto:tag-search"),
        'data-autocomplete-min-length': 3,
        'placeholder': 'Tag Search',
    })
    term = forms.ModelChoiceField(required=False, label='', queryset=Term.objects.all())
    term.group = "CATEGORY" # type: ignore

    startYear = forms.IntegerField(required=False, label='', widget=forms.NumberInput(attrs={'placeholder': 'Start'}) )
    startYear.group = 'DATE RANGE' # type: ignore
    endYear = forms.IntegerField(required=False, label='', widget=forms.NumberInput(attrs={'placeholder': 'End'}) )
    endYear.group = 'DATE RANGE' # type: ignore

    donor = forms.ModelChoiceField(required=False, label='', queryset=Donor.objects.all(), widget=Select2(queryset=Donor.objects.all()))
    donor.widget.attrs.update({
        'data-select2-url': reverse_lazy("kronofoto:contributor-search2"),
        "placeholder": "Contributor search",
    })
    donor.group = "CONTRIBUTOR" # type: ignore

    place: forms.ModelChoiceField = forms.ModelChoiceField(required=False, label='', queryset=Place.objects.all(), widget=Select2(queryset=Place.objects.all()))
    place.widget.attrs.update({
        'data-select2-url': reverse_lazy("kronofoto:place-search"),
        "placeholder": "Place search",
    })
    place.group = "LOCATION" # type: ignore

    city = forms.CharField(required=False, label='', widget=forms.HiddenInput)
    city.group = 'LOCATION' # type: ignore
    county = forms.CharField(required=False, label='', widget=forms.HiddenInput)
    county.group = 'LOCATION' # type: ignore
    state = forms.CharField(required=False, label='', widget=forms.HiddenInput)
    state.group = 'LOCATION' # type: ignore
    country = forms.CharField(required=False, label='', widget=forms.HiddenInput)
    country.group = 'LOCATION' # type: ignore

    query = forms.CharField(required=False, label='')
    query.widget.attrs.update({
        'placeholder': 'Keywords, terms, photo ID#, contributor',
    })
    query.group = "ADVANCED SEARCH" # type: ignore

    def clean(self) -> Optional[Dict[str, Any]]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return None
        cleaned_data['expr'] = None
        if self.is_valid():
            try:
                cleaned_data['expr'] = self._as_expression(cleaned_data)
                if cleaned_data['expr'].complexity() > settings.KRONOFOTO_SEARCH_LIMIT:
                    cleaned_data['expr'] = None
            except NoExpression:
                pass
        return cleaned_data

    def _as_expression(self, cleaned_data: Dict[str, Any]) -> expression.Expression:
        form_exprs = []
        year_exprs = []
        try:
            parser = Parser.tokenize(cleaned_data['query'])
            form_exprs.append(parser.parse().shakeout())
        except NoExpression:
            pass
        except:
            try:
                form_exprs.append(parser.simple_parse().shakeout())
            except NoExpression:
                pass
        if cleaned_data['basic']:
            try:
                form_exprs.append(BasicParser.tokenize(cleaned_data['basic']).parse())
            except NoExpression:
                pass

        if cleaned_data['term']:
            form_exprs.append(expression.TermExactly(cleaned_data['term']))
        if cleaned_data['tag']:
            form_exprs.append(expression.TagExactly(cleaned_data['tag']))
        if cleaned_data['startYear']:
            year_exprs.append(expression.YearGTE(cleaned_data['startYear']))
        if cleaned_data['endYear']:
            year_exprs.append(expression.YearLTE(cleaned_data['endYear']))
        if len(year_exprs) > 0:
            form_exprs.append(reduce(expression.And, year_exprs))
        if cleaned_data['donor']:
            form_exprs.append(expression.DonorExactly(cleaned_data['donor']))
        if cleaned_data['city']:
            form_exprs.append(expression.City(cleaned_data['city']))
        if cleaned_data['county']:
            form_exprs.append(expression.County(cleaned_data['county']))
        if cleaned_data['state']:
            form_exprs.append(expression.State(cleaned_data['state']))
        if cleaned_data['place']:
            form_exprs.append(expression.PlaceExactly(cleaned_data['place']))
        if cleaned_data['country']:
            form_exprs.append(expression.Country(cleaned_data['country']))
        if len(form_exprs):
            return reduce(expression.And, form_exprs)
        raise NoExpression

class CarouselForm(SearchForm):
    id = forms.IntegerField(widget=forms.HiddenInput(), required=True)
    forward = forms.BooleanField(widget=forms.HiddenInput(), required=False)
    offset = forms.IntegerField(widget=forms.HiddenInput(), required=True)
    width = forms.IntegerField(widget=forms.HiddenInput(), required=True)

class TimelineForm(SearchForm):
    year = forms.IntegerField(widget=forms.HiddenInput())
    year.widget.attrs['data-timeline-target'] = 'formYear'


T = TypeVar("T", bound="Bounds")

@dataclass
class Bounds:
    west: float
    south: float
    east: float
    north: float

    @classmethod
    def full_bounds(cls: Type[T]) -> T:
        return cls(west=-180, east=180, south=-90, north=90)

    def as_tuple(self) -> Tuple[float, float, float, float]:
        return (self.west, self.south, self.east, self.north)


class BoundsSearchForm(SearchForm):
    locals()["bounds:west"] = forms.FloatField(widget=forms.HiddenInput(), required=False)
    locals()["bounds:east"] = forms.FloatField(widget=forms.HiddenInput(), required=False)
    locals()["bounds:south"] = forms.FloatField(widget=forms.HiddenInput(), required=False)
    locals()["bounds:north"] = forms.FloatField(widget=forms.HiddenInput(), required=False)

    def clean(self) -> Optional[Dict[str, Any]]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return None
        directions = ['west', 'east', 'north', 'south']
        fields = [f'bounds:{name}' for name in directions]
        if any(cleaned_data[field] is None for field in fields):
            cleaned_data['search_bounds'] = None
            cleaned_data['map_bounds'] = Bounds.full_bounds()
        else:
            init_kwargs = {
                direction: cleaned_data[field]
                for (direction, field) in zip(directions, fields)
            }
            bounds = Bounds(**init_kwargs)
            cleaned_data['search_bounds'] = bounds
            cleaned_data['map_bounds'] = bounds
        return cleaned_data



class TagForm(forms.Form):
    tag = forms.CharField(strip=True, min_length=2, required=True)

    def clean(self) -> Optional[Dict[str, Any]]:
        data = super().clean()
        if data is None:
            return None
        if 'tag' in data:
            data['tag'] = [s.strip() for s in data['tag'].split(', ')]
            for text in data['tag']:
                if Term.objects.filter(slug=slugify(text)).exists():
                    self.add_error('tag', 'Tags which are already categories are not allowed: {}'.format(text))
        return data


    def add_tag(self, photo: Photo, user: User) -> None:
        for text in self.cleaned_data['tag']:
            tag, _ = Tag.objects.get_or_create(slug=slugify(text), defaults={'tag': text})
            accepted = (
                user.has_perm('kronofoto.add_tag') and
                user.has_perm('kronofoto.change_tag') and
                user.has_perm('kronofoto.add_phototag') and
                user.has_perm('kronofoto.change_phototag')
            )
            phototag, created = PhotoTag.objects.get_or_create(tag=tag, photo=photo, defaults={'accepted': accepted})
            if not created:
                phototag.accepted |= accepted
            phototag.creator.add(user)
            phototag.save()


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['name']


class AddToListForm(forms.Form):
    collection = forms.ChoiceField(required=False)
    name = forms.CharField(required=False)
    visibility = forms.ChoiceField(required=False, choices=Collection.PRIVACY_TYPES)

    def __init__(self, *args: Any, **kwargs: Any):
        self.collection = kwargs.pop('collections')
        super().__init__(*args, **kwargs)
        self.fields['collection'].choices = self.collection # type: ignore

    def clean(self) -> Optional[Dict[str, Any]]:
        data = super().clean()
        if data is None:
            return None
        if not data['collection'] and not data['name']:
            self.add_error('name', 'A name must be provided')
        return data

class PhotoSphereAddForm(forms.ModelForm):
    class Meta:
        model = PhotoSphere
        fields = ('title', 'image', "is_published", "tour", "mainstreetset")


    def save(self, commit: bool=False) -> PhotoSphere:
        instance = super().save(commit=False)
        if instance.image:
            try:
                instance.location = instance.exif_location()
            except IncompleteGPSInfo:
                pass
        if commit:
            instance.save()
        return instance


class PhotoSphereChangeForm(forms.ModelForm):
    class Meta:
        model = PhotoSphere
        widgets = {
            'heading': HeadingWidget,
        }
        fields = '__all__'

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.fields['heading'].widget.attrs['photo'] = kwargs['instance'].image.url
        self.fields['heading'].widget.attrs["useNewAnglesOrder"] = kwargs['instance'].use_new_angles


class PhotoPositionField(forms.MultiValueField):
    widget = PositioningWidget
    def __init__(self, **kwargs: Any):
        fields = (
            forms.FloatField(),
            forms.FloatField(),
            forms.FloatField(),
        )
        super().__init__(fields=fields, **kwargs)

    def compress(self, data_list: Tuple[Union[int, float], Union[int, float], Union[int, float]]) -> Dict[str, Union[int, float]]:
        return dict(azimuth=data_list[0], inclination=data_list[1], distance=data_list[2])


class PhotoSpherePairInlineForm(forms.ModelForm):
    position = PhotoPositionField(required=False, help_text="Set photo position using the sliders in the top right")
    class Meta:
        model = PhotoSpherePair
        fields = ['photo', 'photosphere']

    def __init__(self, *args: Any, **kwargs: Any):
        if 'instance' in kwargs and kwargs['instance']:
            instance = kwargs['instance']
            initial = dict(
                position=dict(
                    azimuth=instance.azimuth,
                    inclination=instance.inclination,
                    distance=instance.distance,
                )
            )
            kwargs['initial'] = initial
            super().__init__(
                *args,
                **kwargs,
            )
            position = self.fields['position'].widget
            position.attrs['photosphere'] = instance.photosphere.image.url
            position.attrs['photo'] = instance.photo.h700.url
            position.attrs["useNewAnglesOrder"] = instance.photosphere.use_new_angles
            position.attrs['photo_w'] = instance.photo.h700.width
            position.attrs['photo_h'] = instance.photo.h700.height
        else:
            super().__init__(
                *args,
                **kwargs,
            )

    def save(self, *args: Any, **kwargs: Any) -> PhotoSpherePair:
        position = self.cleaned_data['position']
        self.instance.azimuth = position['azimuth']
        self.instance.inclination = position['inclination']
        self.instance.distance = position['distance']
        return super().save(*args, **kwargs)
