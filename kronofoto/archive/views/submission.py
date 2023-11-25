from .multiform import MultiformView
from .basetemplate import BaseTemplateMixin
from django.views.generic.base import TemplateView, View
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
from dataclasses import dataclass

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
            'uuid',
            'archive',
            'uploader',
            'image',
        )
        labels = {"donor": "Contributor"}

class SubmissionImageForm(forms.Form):
    image = forms.ImageField()

class BaseSubmissionFormView(BaseTemplateMixin, MultiformView):
    form_classes = (
        SubmissionDetailsForm,
        SubmissionImageForm,
    )
    def get_extra_form_params(self, page):
        if page == 0:
            return {'force_archive': get_object_or_404(Archive.objects.all(), slug=self.kwargs['short_name'])}
        return {}
    template_name = 'archive/submission_create.html'
    def forms_valid(self, forms):
        submission_args = {**forms[0].cleaned_data, **forms[1].cleaned_data}
        if not self.request.user.is_anonymous:
            submission_args['uploader'] = self.request.user

        Submission.objects.create(
            archive=Archive.objects.get(slug=self.kwargs['short_name']),
            **submission_args,
        )
        return redirect("kronofoto:submission-done", **self.kwargs)



class SubmissionFormView(BaseSubmissionFormView):
    @method_decorator(require_agreement(extra_context={"reason": "You must agree to terms before uploading."}))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
