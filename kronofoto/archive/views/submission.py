from .multiform import MultiformView
from .basetemplate import BaseTemplateMixin
from django.views.generic.base import TemplateView, View
from django.shortcuts import redirect, get_object_or_404
from archive.models.donor import Donor
from archive.models.photo import Submission
from archive.models.archive import ArchiveAgreement, UserAgreement, Archive
from .agreement import AnonymousAgreementCheck, UserAgreementCheck
from ..fields import RecaptchaField

from django import forms

class SubmissionDetailsForm(forms.ModelForm):
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

class SubmissionFormView(View):
    checkers = (
        AnonymousAgreementCheckTemplateView,
        UserAgreementCheck,
    )
    view = BaseSubmissionFormView
    def dispatch(self, request, *args, **kwargs):
        object = get_object_or_404(ArchiveAgreement, archive__slug=self.kwargs['short_name'])
        for checker in self.checkers:
            if checker.should_handle(request, object, UserAgreement):
                view = checker.as_view()
                return view(request, *args, **kwargs)
        view = BaseSubmissionFormView.as_view()
        return view(request, *args, **kwargs)
