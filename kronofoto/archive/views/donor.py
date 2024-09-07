from django.http import HttpResponse, HttpRequest, QueryDict
from .basetemplate import BaseTemplateMixin
from ..models.donor import Donor
from .agreement import UserAgreementCheck, require_agreement
from django.views.generic.base import View
from archive.models.archive import ArchiveAgreement, UserAgreement, Archive
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import CreateView
from ..reverse import reverse
from django.utils.decorators import method_decorator
from django.forms import Form, ModelForm
from typing import Any, Dict, List, Union, Optional

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
    def get_success_url(self) -> str:
        return reverse('kronofoto:contributor-created', kwargs=self.kwargs)
    def get_form(self, *args: Any, **kwargs: Any) -> Form:
        form = super().get_form(*args, **kwargs)
        form.fields['last_name'].required = True
        return form

    def form_valid(self, form: ModelForm) -> HttpResponse:
        form.instance.archive = get_object_or_404(Archive, slug=self.kwargs['short_name'])
        return super().form_valid(form)


class ContributorCreateView(BaseContributorCreateView):
    @method_decorator(require_agreement(extra_context={"reason": "You must agree to terms before creating contributors."}))
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().dispatch(request, *args, **kwargs)
