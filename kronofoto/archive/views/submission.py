from .multiform import MultiformView
from .basetemplate import BaseTemplateMixin
from django.views.generic.base import TemplateView, View
from django.shortcuts import redirect, get_object_or_404
from archive.models.donor import Donor
from archive.models.photo import Submission
from archive.models.archive import ArchiveAgreement, UserAgreement, Archive
from .agreement import AnonymousAgreementCheck, UserAgreementCheck
from ..fields import RecaptchaField, AutocompleteField
from ..widgets import AutocompleteWidget
from ..reverse import reverse_lazy
from ..admin import SubmissionForm

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


class KronofotoTemplateView(BaseTemplateMixin, TemplateView):
    pass

class AnonymousAgreementCheckTemplateView(AnonymousAgreementCheck, KronofotoTemplateView):
    template_name = 'archive/anonymous_agreement.html'

class UserAgreementCheckRedirect(UserAgreementCheck):
    pattern_name = "kronofoto:agreement-create"

class SubmissionFormView(View):
    checkers = (
        AnonymousAgreementCheckTemplateView,
        UserAgreementCheckRedirect,
    )
    view = BaseSubmissionFormView
    extra_context = {}
    def dispatch(self, request, *args, **kwargs):
        object = get_object_or_404(ArchiveAgreement, archive__slug=self.kwargs['short_name'])
        for checker in self.checkers:
            if checker.should_handle(request, object, UserAgreement):
                view = checker.as_view(extra_context=self.extra_context)
                return view(request, *args, **kwargs)
        view = BaseSubmissionFormView.as_view()
        return view(request, *args, **kwargs)
