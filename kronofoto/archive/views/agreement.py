from django.views.generic import DetailView, FormView, RedirectView
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin
from django.http import QueryDict
from ..models.archive import ArchiveAgreement, UserAgreement
from ..forms import AgreementForm
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

class AnonymousAgreementCheck:
    @staticmethod
    def should_handle(request, object, *args, **kwargs):
        if request.user.is_anonymous:
            session_key = "kf.agreement.{}.{}".format(object.pk, object.version)
            agreed = request.session.get(session_key, False)
            return not agreed
        return False

class UserAgreementCheck(RedirectView):
    redirect_field_name = 'next'

    def get_redirect_url(self, *args, **kwargs):
        url = super().get_redirect_url(*args, **kwargs)
        params = QueryDict(mutable=True)
        params[self.get_redirect_field_name()] = self.request.build_absolute_uri()
        qs = params.urlencode(safe="/")
        return "{}?{}".format(url, qs)

    def get_redirect_field_name(self):
        return self.redirect_field_name

    @staticmethod
    def should_handle(request, object, user_agreement_model):
        if not request.user.is_anonymous:
            session_key = "kf.agreement.{}.{}".format(object.pk, object.version)
            agreed = request.session.get(session_key, False)
            if not agreed:
                agreed = user_agreement_model.objects.filter(user=request.user, agreement=object, version__gte=object.version)
                request.session[session_key] = agreed
            return not agreed
        return False

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
