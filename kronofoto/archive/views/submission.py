from .multiform import MultiformView
from .base import ArchiveRequest
from django.db.models import QuerySet, Manager
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, HttpRequest, QueryDict
from django.views.generic.base import TemplateView, View
from django.template.response import TemplateResponse
from django.shortcuts import redirect, get_object_or_404
from archive.models.term import Term, TermQuerySet
from archive.models.donor import Donor
from archive.models.photo import Submission
from archive.models.archive import ArchiveAgreement, UserAgreement, Archive, ArchiveAgreementQuerySet
from .agreement import UserAgreementCheck, require_agreement, KronofotoTemplateView
from ..fields import RecaptchaField, AutocompleteField
from ..widgets import AutocompleteWidget, SelectMultipleTerms, ImagePreviewClearableFileInput
from ..reverse import reverse_lazy
from ..admin import SubmissionForm
from django.utils.decorators import method_decorator
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, Protocol, Type, List
from abc import ABCMeta, abstractmethod

from django import forms

class SubmissionDetailsForm(SubmissionForm):
    prefix = "submission"
    def __init__(self, *args: Any, force_archive: Archive, **kwargs: Any):
        super().__init__(*args, force_archive=force_archive, **kwargs)
        category = self.fields.get('category')
        if category:
            category.widget.attrs.update({
                'hx-get': reverse_lazy("kronofoto:term-list", kwargs={'short_name': force_archive.slug}),
                'hx-trigger': "change",
                "hx-target": '[data-terms]',
                "hx-push-url": "false",
            })
        terms = self.fields.get('terms')
        if terms:
            terms.widget.attrs.update({
                'data-terms': "",
                'hx-get': reverse_lazy("kronofoto:define-terms", kwargs={'short_name': force_archive.slug}),
                'hx-trigger': "change",
                "hx-target": '[data-term-definitions]',
                "hx-swap": "innerHTML",
                "hx-push-url": "false",
            })

    donor = AutocompleteField(
        queryset=Donor.objects.all(),
        to_field_name="id",
        widget=AutocompleteWidget(url=reverse_lazy("kronofoto:contributor-search")),
        label="Contributor",
    )
    donor.widget.attrs.update({
        "placeholder": "Enter name...",
    })
    photographer = AutocompleteField(
        queryset=Donor.objects.all(),
        to_field_name="id",
        widget=AutocompleteWidget(url=reverse_lazy("kronofoto:contributor-search")),
        required=False,
    )
    photographer.widget.attrs.update({
        "placeholder": "Enter name...",
    })
    scanner = AutocompleteField(
        queryset=Donor.objects.all(),
        to_field_name="id",
        widget=AutocompleteWidget(url=reverse_lazy("kronofoto:contributor-search")),
        required=False,
    )
    scanner.widget.attrs.update({
        "placeholder": "Enter name...",
    })

    class Meta:
        model = Submission
        exclude = None
        fields = (
            "category",
            "donor",
            "image",
            "year",
            "circa",
            "photographer",
            "terms",
            "address",
            "city",
            "county",
            "state",
            "country",
            "caption",
        )
        widgets = {
            'image': ImagePreviewClearableFileInput(attrs={"data-image-input": True}, img_attrs={"style": "width: 600px"}),
            'terms': SelectMultipleTerms(ul_attrs={"data-term-definitions": ""}),
        }
        labels = {"donor": "Contributor"}

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
    form_class: Type[SubmissionForm] = SubmissionDetailsForm

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
        return redirect("kronofoto:submission-done", short_name=self.archive.slug)


@dataclass
class DisplayForm:
    request: HttpRequest
    context: Dict[str, Any]
    form: forms.ModelForm

    def get_response(self) -> HttpResponse:
        self.context['form'] = self.form
        return TemplateResponse(self.request, "archive/submission_create.html", self.context)

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
    terms: Any = Term.objects

    def get_term_lister(self, data: Dict[str, str], archive: Archive) -> HasTerms:
        form = TermRequestForm(data)
        if form.is_valid():
            return CategoryTerms(self.terms, archive, form.cleaned_data['category'])
        else:
            return NoCategory(self.terms)

    def get_terms(self, data: Dict[str, str], archive: Archive) -> QuerySet[Term]:
        return self.get_term_lister(data, archive).get_terms()

def list_terms(request: HttpRequest, short_name: str) -> HttpResponse:
    archive = get_object_or_404(Archive.objects.all(), slug=short_name)
    terms = TermListFactory().get_terms(request.GET, archive)
    return TemplateResponse(request, 'admin/widgets/terms.html', {'objects': terms})

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
        return TemplateResponse(request, "archive/widgets/define_terms.html", {"objects": self.terms.filter(id__in=terms)})

def define_terms(request: HttpRequest, **kwargs: Any) -> HttpResponse:
    return TermDefiner().get_response(request, request.GET)


@require_agreement(extra_context={"reason": "You must agree to terms before uploading."})
def submission(request: HttpRequest, short_name: str) -> HttpResponse:
    context = ArchiveRequest(request, short_name=short_name).common_context
    archive = get_object_or_404(Archive.objects.all(), slug=short_name)
    return SubmissionFactory(request, request.user, archive, context, extra_form_kwargs={"force_archive": archive}).get_response()
