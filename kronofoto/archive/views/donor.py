from .basetemplate import BaseTemplateMixin
from ..models.donor import Donor
from .agreement import AnonymousAgreementCheck, UserAgreementCheck
from django.views.generic.base import View
from archive.models.archive import ArchiveAgreement, UserAgreement, Archive
from .submission import AnonymousAgreementCheckTemplateView, UserAgreementCheckRedirect
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import CreateView
from ..reverse import reverse

class BaseContributorCreateView(BaseTemplateMixin, CreateView):
    model = Donor
    fields = [
        'first_name',
        'last_name',
        'email',
        'home_phone',
        'street1',
        'street2',
        'city',
        'state',
        'zip',
        'country',
    ]
    def get_success_url(self):
        return reverse('kronofoto:contributor-created', kwargs=self.kwargs)
    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['last_name'].required = True
        return form

    def form_valid(self, form):
        form.instance.archive = get_object_or_404(Archive, slug=self.kwargs['short_name'])
        return super().form_valid(form)


class ContributorCreateView(View): # TODO: give this a better name and make generic
    checkers = (
        AnonymousAgreementCheckTemplateView,
        UserAgreementCheckRedirect,
    )
    extra_context = {}
    view = BaseContributorCreateView
    def dispatch(self, request, *args, **kwargs):
        object = get_object_or_404(ArchiveAgreement, archive__slug=self.kwargs['short_name'])
        for checker in self.checkers:
            if checker.should_handle(request, object, UserAgreement):
                view = checker.as_view(extra_context=self.extra_context)
                return view(request, *args, **kwargs)
        view = self.view.as_view()
        return view(request, *args, **kwargs)
