from django.views.generic import DetailView, FormView, RedirectView
from django.views.generic.base import View, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.http import QueryDict
from ..models.archive import ArchiveAgreement, UserAgreement
from django.shortcuts import redirect, get_object_or_404
from archive.models.archive import ArchiveAgreement, UserAgreement, Archive, ArchiveAgreementQuerySet
from django.db.models import QuerySet
from ..forms import AgreementForm
from dataclasses import dataclass
from .basetemplate import BaseTemplateMixin

class AgreementDetailView(DetailView):
    form_class = None

    def get_form(self):
        return self.form_class()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['form'] = self.get_form()
        return context

class AgreementFormView(SingleObjectMixin, FormView):
    user_agreement_model = None

    def get_success_url(self):
        return self.request.GET['next']

    def form_valid(self, form):
        object = self.get_object()
        self.request.session['kf.agreement.{}.{}'.format(object.pk, object.version)] = True
        if not self.request.user.is_anonymous:
            self.user_agreement_model.objects.update_or_create(defaults={'version': object.version}, user=self.request.user, agreement=object)
        return super().form_valid(form)

    def post(self, *args, **kwargs):
        self.object = super().get_object()
        return super().post(*args, **kwargs)


class UserAgreementCheck(RedirectView):
    redirect_field_name = 'next'
    extra_context = {}

    def get_redirect_url(self, *args, **kwargs):
        url = super().get_redirect_url(*args, **kwargs)
        params = QueryDict(mutable=True)
        params[self.get_redirect_field_name()] = self.request.build_absolute_uri()
        qs = params.urlencode(safe="/")
        return "{}?{}".format(url, qs)

    def get_redirect_field_name(self):
        return self.redirect_field_name


class BaseAgreementView(View):
    model = ArchiveAgreement
    form_class = AgreementForm
    detail = AgreementDetailView
    formview = AgreementFormView
    template_name = 'archive/archiveagreement_detail.html'

    def get(self, request, *args, **kwargs):
        view = self.detail.as_view(
            model=self.model,
            template_name = self.template_name,
            form_class=self.form_class,
            slug_url_kwarg="short_name",
            slug_field="archive__slug",
        )
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = self.formview.as_view(
            model=self.model,
            template_name = self.template_name,
            form_class=self.form_class,
            user_agreement_model=UserAgreement,
            slug_url_kwarg="short_name",
            slug_field="archive__slug",
        )
        return view(request, *args, **kwargs)

class KronofotoAgreementDetailView(BaseTemplateMixin, AgreementDetailView):
    pass

class KronofotoAgreementFormView(BaseTemplateMixin, AgreementFormView):
    pass

class AgreementView(BaseAgreementView):
    detail = KronofotoAgreementDetailView
    formview = KronofotoAgreementFormView

@dataclass
class BasicView:
    view: callable

class UserAgreementCheckRedirect(UserAgreementCheck):
    pattern_name = "kronofoto:agreement-create"

class KronofotoTemplateView(BaseTemplateMixin, TemplateView):
    template_name = 'archive/anonymous_agreement.html'

@dataclass
class AgreementCheckFactory:
    view: callable
    func: callable
    agreement: "any"
    session: "any"
    user: "User"
    redirect_view: callable = UserAgreementCheckRedirect.as_view()
    user_agreement_queryset: QuerySet[UserAgreement] = UserAgreement.objects

    def post_session_check(self, agreed):
        if not agreed:
            if self.user.is_anonymous:
                return BasicView(self.view)
            else:
                return UserDbAgreementCheck(
                    user=self.user,
                    agreement=self.agreement,
                    session=self.session,
                    factory_method=self.post_db_check,
                    user_agreement_queryset=self.user_agreement_queryset,
                )
        return BasicView(self.func)

    def post_db_check(self, agreed):
        if not agreed:
            return BasicView(self.redirect_view)
        return BasicView(self.func)

    def get_agreement_checker(self):
        return SessionCheck(agreement=self.agreement, session=self.session, factory_method=self.post_session_check)

@dataclass
class UserDbAgreementCheck:
    user: "User"
    agreement: "any"
    session: "any"
    factory_method: callable
    user_agreement_queryset: QuerySet[UserAgreement]

    @property
    def view(self):
        agreed = self.user_agreement_queryset.filter(user=self.user, agreement=self.agreement, version__gte=self.agreement.version).exists()
        self.session[self.agreement.session_key] = agreed
        return self.factory_method(agreed).view

@dataclass
class SessionCheck:
    agreement: "any"
    session: "any"
    factory_method: callable

    @property
    def view(self):
        agreed = self.session.get(self.agreement.session_key, False)
        return self.factory_method(agreed).view

@dataclass
class require_agreement:
    extra_context: str
    agreement_queryset: ArchiveAgreementQuerySet = ArchiveAgreement.objects

    def __call__(self, func):
        def wrapper(request, *args, short_name, **kwargs):
            object = get_object_or_404(self.agreement_queryset.object_for(short_name))
            factory = AgreementCheckFactory(view=KronofotoTemplateView.as_view(extra_context=self.extra_context), func=func, agreement=object, session=request.session, user=request.user)
            return factory.get_agreement_checker().view(request, *args, short_name=short_name, **kwargs)
        return wrapper
