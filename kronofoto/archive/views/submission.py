from .multiform import MultiformView
from .base import ArchiveRequest
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, HttpRequest
from django.views.generic.base import TemplateView, View
from django.template.response import TemplateResponse
from django.shortcuts import redirect, get_object_or_404
from archive.models.donor import Donor
from archive.models.photo import Submission
from archive.models.archive import ArchiveAgreement, UserAgreement, Archive, ArchiveAgreementQuerySet
from .agreement import UserAgreementCheck, require_agreement, KronofotoTemplateView
from ..fields import RecaptchaField, AutocompleteField
from ..widgets import AutocompleteWidget
from ..reverse import reverse_lazy
from ..admin import SubmissionForm
from django.utils.decorators import method_decorator
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, Protocol, Type
from abc import ABCMeta, abstractmethod

from django import forms

class SubmissionDetailsForm(SubmissionForm):
    prefix = "submission"

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
        exclude = (
            #'uuid',
            'archive',
            'uploader',
        )
        labels = {"donor": "Contributor"}

class SubmissionImageForm(forms.Form):
    image = forms.ImageField()

class HasResponse(Protocol):
    def get_response(self) -> HttpResponse:
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



@require_agreement(extra_context={"reason": "You must agree to terms before uploading."})
def submission(request: HttpRequest, short_name: str) -> HttpResponse:
    context = ArchiveRequest(request, short_name=short_name).common_context
    archive = get_object_or_404(Archive.objects.all(), slug=short_name)
    return SubmissionFactory(request, request.user, archive, context, extra_form_kwargs={"force_archive": archive}).get_response()
