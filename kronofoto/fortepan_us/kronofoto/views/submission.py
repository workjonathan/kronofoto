from .base import ArchiveRequest
from django.db.models import QuerySet, Manager
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, HttpRequest, QueryDict
from django.views.generic.base import TemplateView, View
from django.template.response import TemplateResponse
from django.shortcuts import redirect, get_object_or_404
from fortepan_us.kronofoto.models.term import Term, TermQuerySet
from fortepan_us.kronofoto.models.donor import Donor
from fortepan_us.kronofoto.models import Photo, Place
from fortepan_us.kronofoto.models.photo import Submission
from fortepan_us.kronofoto.models.archive import ArchiveAgreement, UserAgreement, Archive, ArchiveAgreementQuerySet
from django.contrib.gis.forms import OSMWidget
from .agreement import UserAgreementCheck, require_agreement, KronofotoTemplateView
from fortepan_us.kronofoto.fields import RecaptchaField, AutocompleteField
from fortepan_us.kronofoto.widgets import AutocompleteWidget, SelectMultipleTerms, ImagePreviewClearableFileInput, Select2
from fortepan_us.kronofoto.reverse import reverse_lazy
from fortepan_us.kronofoto.forms import ArchiveSubmissionForm
from django.utils.decorators import method_decorator
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, Protocol, Type, List, Tuple, Iterable
from abc import ABCMeta, abstractmethod
from django.utils.html import format_html

from django import forms


@dataclass
class TermChoices:
    items: Iterable[Term]

    def choices(self) -> List[Tuple[Optional[str], List[Tuple[int, Term]]]]:
        term_groups: Dict[Optional[str], List[Tuple[int, Term]]] = {}
        other: List[Tuple[int, Term]] = []
        for term in self.items:
            if term.group:
                term_groups.setdefault(term.group.name, [])
                group = term_groups[term.group.name]
            else:
                group = other
            if term.description:
                definition_part = term.description
            else:
                definition_part = ""
            #group.append((term.id, format_html('<span class="term-left">{}</span><span class="term-right">{}</span>', term.term, definition_part)))
            group.append((term.id, term))
        choices = sorted(term_groups.items())
        if len(term_groups) == 0:
            choices.append((None, other))
        elif len(other) > 0:
            choices.append(("Other", other))
        return choices

@dataclass
class SubmissionFormAttrs:
    archive: Archive

    def term_attrs(self) -> Dict[str, str]:
        return {
            'data-terms': "",
        }

class SubmissionDetailsForm(ArchiveSubmissionForm):
    prefix = "submission"
    required_css_class = "required"
    def __init__(self, *args: Any, force_archive: Archive, submission_form_attrs: Type[SubmissionFormAttrs] = SubmissionFormAttrs, **kwargs: Any):
        self.grouper = TermChoices
        super().__init__(*args, force_archive=force_archive, label_suffix="", **kwargs)
        form_attrs = submission_form_attrs(force_archive)

        category = self.fields.get('category')
        if category:
            category.help_text = 'Choose one term  from the list to indicate what kind of an item this is.'
            category.widget.attrs.update({
                'hx-get': reverse_lazy("kronofoto:term-list", kwargs={'short_name': force_archive.slug}),
                'hx-trigger': "change",
                "hx-target": '[data-terms]',
                "hx-push-url": "false",
                "autocomplete": "false",
            })
        terms = self.fields.get('terms')
        if terms:
            terms.widget.attrs.update(form_attrs.term_attrs())
            terms.help_text = 'Select as many terms as you like to indicate what the item is about.'
        field = self.fields.get('year')
        if field:
            field.help_text = 'The year that the item was created, if you are unsure, put in an approximate date and click the "Approximate date" box.'
        if field:
            field.help_text = 'The country where the item was created.'
        field = self.fields.get('caption')
        if field:
            field.help_text = 'Is there anything else you would like to share about this photo? Tell us in your own words and language.'
        field = self.fields.get('place')
        if field:
            field.widget.attrs.update({
                'data-select2-url': reverse_lazy("kronofoto:all-place-search"),
                "placeholder": "Place search",
            })
        field = self.fields.get('location_point')
        if field:
            field.widget.attrs.update({
                'style': 'width: 400px; height:400px;'
            })


    donor = AutocompleteField(
        queryset=Donor.objects.all(),
        to_field_name="id",
        widget=AutocompleteWidget(url=reverse_lazy("kronofoto:contributor-search")),
        label="Contributor",
        help_text="The person who is contributing this item to MTMS. Choose your name from the list.",
    )
    donor.widget.attrs.update({
        "placeholder": "Enter name...",
    })
    photographer = AutocompleteField(
        queryset=Donor.objects.all(),
        to_field_name="id",
        widget=AutocompleteWidget(url=reverse_lazy("kronofoto:contributor-search")),
        required=False,
        help_text='The name of the person who created the item you are submitting.',
    )
    photographer.widget.attrs.update({
        "placeholder": "Enter name...",
    })
    #scanner = AutocompleteField(
    #    queryset=Donor.objects.all(),
    #    to_field_name="id",
    #    widget=AutocompleteWidget(url=reverse_lazy("kronofoto:contributor-search")),
    #    required=False,
    #)
    #scanner.widget.attrs.update({
    #    "placeholder": "Enter name...",
    #})

    class Meta:
        model = Submission
        exclude = None
        fields = (
            "donor",
            "category",
            "year",
            "circa",
            "photographer",
            "place",
            'location_point',
            "terms",
            "caption",
            "image",
        )
        widgets = {
            'image': ImagePreviewClearableFileInput(attrs={"data-image-input": True}, img_attrs={"style": "width: 600px"}),
            'terms': SelectMultipleTerms(),
            'place': Select2(queryset=Place.objects.all()),
            'location_point': OSMWidget(),
        }
        labels = {
            "donor": "Contributor",
            "image": "Upload",
            "circa": "Approximate date",
            "address": "Location, Street Address",
            "city": "Location, City",
            "county": "Location, County",
            "state": "Location, State",
            "country": "Location, Country",
        }


    def get_term_choices(self, queryset: QuerySet) -> List[Tuple[Optional[str], List[Tuple[int, Term]]]]:
        return self.grouper(queryset).choices()

class SubmissionImageForm(forms.Form):
    image = forms.ImageField()

class HasResponse(Protocol):
    def get_response(self) -> HttpResponse:
        ...

class HasTerms(Protocol):
    def get_terms(self) -> QuerySet:
        ...

@dataclass
class SubmissionFactory:
    request: HttpRequest
    user: Union[User, AnonymousUser]
    archive: Archive
    context: Dict[str, Any]
    extra_form_kwargs: Dict[str, Any] = field(default_factory=dict)
    form_class: Type[ArchiveSubmissionForm] = SubmissionDetailsForm

    def get_post_response(self, form: forms.ModelForm) -> HasResponse:
        if form.is_valid():
            return ValidSubmission(
                form,
                archive=self.archive,
                uploader=self.user if not self.user.is_anonymous else None
            )
        else:
            return DisplayForm(request=self.request, form=form, context=self.context)

    def get_handler(self) -> HasResponse:
        if self.request.method and self.request.method.lower() == "post":
            return self.get_post_response(
                self.form_class(self.request.POST, files=self.request.FILES, **self.extra_form_kwargs)
            )
        else:
            return DisplayForm(
                request=self.request, form=self.form_class(**self.extra_form_kwargs), context=self.context
            )

    def get_response(self) -> HttpResponse:
        return self.get_handler().get_response()

@dataclass
class ValidSubmission:
    form: forms.ModelForm
    archive: Archive
    uploader: Optional[User]

    def get_response(self) -> HttpResponse:
        submission = self.form.save(commit=False)
        submission.archive = self.archive
        submission.uploader = self.uploader
        submission.save()
        self.form.save_m2m()
        return redirect("kronofoto:submission-done", short_name=self.archive.slug)


@dataclass
class DisplayForm:
    request: HttpRequest
    context: Dict[str, Any]
    form: forms.ModelForm

    def get_response(self) -> HttpResponse:
        self.context['form'] = self.form
        return TemplateResponse(self.request, "kronofoto/pages/submission-create.html", self.context)

@dataclass
class NoCategory:
    terms: TermQuerySet
    def get_terms(self) -> QuerySet[Term]:
        return self.terms.none()

@dataclass
class CategoryTerms:
    terms: TermQuerySet
    archive: Archive
    category: int
    def get_terms(self) -> QuerySet[Term]:
        return self.terms.objects_for(archive=self.archive, category=self.category).order_by('term')

class TermRequestForm(forms.Form):
    prefix = "submission"
    category = forms.IntegerField()


@dataclass
class TermListFactory:
    archive: Archive
    data: Dict[str, str]
    terms: Any = Term.objects

    def get_term_grouper(self, items: Iterable[Term]) -> TermChoices:
        return TermChoices(items)

    def get_term_lister(self) -> HasTerms:
        form = TermRequestForm(self.data)
        if form.is_valid():
            return CategoryTerms(self.terms, self.archive, form.cleaned_data['category'])
        else:
            return NoCategory(self.terms)

    def get_terms(self) -> QuerySet[Term]:
        return self.get_term_lister().get_terms()

    def get_term_choices(self) -> List[Tuple[Optional[str], List[Tuple[int, Term]]]]:
        terms = self.get_terms()
        return self.get_term_grouper(terms).choices()

    def get_term_widget(self, *, choices: List[Tuple[Optional[str], List[Tuple[int, Term]]]]) -> forms.Widget:
        return SelectMultipleTerms(
            choices=choices,
            attrs=SubmissionFormAttrs(self.archive).term_attrs(),
        )

def list_terms(request: HttpRequest, short_name: str) -> HttpResponse:
    archive = get_object_or_404(Archive.objects.all(), slug=short_name)
    factory = TermListFactory(archive=archive, data=request.GET)
    terms = factory.get_term_choices()
    return HttpResponse(factory.get_term_widget(choices=terms).render("submission-terms", None))

@dataclass
class TermDefiner:
    terms: Any = Term.objects

    def get_term_ids(self, data: QueryDict, key: str="submission-terms") -> List[int]:
        terms = []
        for term in data.getlist(key):
            try:
                terms.append(int(term))
            except ValueError:
                pass
        return terms

    def get_response(self, request: HttpRequest, data: QueryDict) -> HttpResponse:
        terms = self.get_term_ids(data)
        return TemplateResponse(request, "kronofoto/widgets/define_terms.html", {"objects": self.terms.filter(id__in=terms)})

def define_terms(request: HttpRequest, **kwargs: Any) -> HttpResponse:
    return TermDefiner().get_response(request, request.GET)


@require_agreement(extra_context={"reason": "You must agree to terms before uploading."})
def submission(request: HttpRequest, short_name: str) -> HttpResponse:
    context = ArchiveRequest(request, short_name=short_name).common_context
    archive = get_object_or_404(Archive.objects.all(), slug=short_name)
    return SubmissionFactory(request, request.user, archive, context, extra_form_kwargs={"force_archive": archive}).get_response()
