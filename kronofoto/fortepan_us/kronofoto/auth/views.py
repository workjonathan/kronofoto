from django.contrib.auth import views as django_views
from django.views.generic.base import RedirectView
from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from django.contrib.auth import login
from django.urls import reverse, reverse_lazy
from django.conf import settings
import urllib
import urllib.request
import json
from django.forms import Form
from django.http import HttpResponse
from fortepan_us.kronofoto.views import BaseTemplateMixin
from .token import UserEmailVerifier
from .forms import RegisterUserForm, FortepanAuthenticationForm
from typing import Any, Dict, List, Union, Optional

class LoginView(BaseTemplateMixin, django_views.LoginView):
    form_class = FortepanAuthenticationForm

class LogoutView(BaseTemplateMixin, django_views.LogoutView):
    pass

class PasswordResetView(BaseTemplateMixin, django_views.PasswordResetView):
    pass

class PasswordResetDoneView(BaseTemplateMixin, django_views.PasswordResetDoneView):
    pass


class PasswordResetConfirmView(BaseTemplateMixin, django_views.PasswordResetConfirmView):
    pass

class PasswordResetCompleteView(BaseTemplateMixin, django_views.PasswordResetCompleteView):
    pass


class PasswordChangeView(BaseTemplateMixin, django_views.PasswordChangeView):
    template_name = 'kronofoto/views/auth/password_change_form.html'


class PasswordChangeDoneView(BaseTemplateMixin, django_views.PasswordChangeDoneView):
    template_name = 'kronofoto/views/auth/password_change_done.html'

class VerifyToken(RedirectView):
    permanent = False
    pattern_name = 'kronofoto:random-image'
    verifier = UserEmailVerifier()

    def get_redirect_url(self, *args: Any, **kwargs: Any) -> Optional[str]:
        user = self.verifier.verify_token(uid=kwargs['uid'], token=kwargs['token'])
        if user:
            login(self.request, user)
        return super().get_redirect_url()

class RegisterAccount(BaseTemplateMixin, FormView):
    form_class = RegisterUserForm
    template_name = 'kronofoto/pages/auth/register-account.html'
    success_url = '/'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['RECAPTCHA_SITE_KEY'] = settings.GOOGLE_RECAPTCHA_SITE_KEY
        return context

    def user_is_human(self) -> bool:
        recaptcha_response = self.request.POST.get('g-recaptcha-response')
        data = {
            'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response,
        }
        args = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request('https://www.google.com/recaptcha/api/siteverify', data=args)
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode())
        return result['success']

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        return kwargs

    def form_valid(self, form: RegisterUserForm) -> HttpResponse:
        if self.user_is_human():
            form.create_user()
            self.success_url = reverse('email-sent')
        else:
            self.success_url = reverse('register-account')
        return super().form_valid(form)

class EmailSentView(BaseTemplateMixin, TemplateView):
    template_name  = 'kronofoto/pages/auth/email-sent.html'
