from hypothesis.extra.django import from_model, register_field_strategy, TestCase
from django.test import Client, RequestFactory
from .models import Agreement, UserAgreement
from django.contrib.auth.models import AnonymousUser, User

from django.views.generic import DetailView, FormView, RedirectView
from django.views.generic.detail import SingleObjectMixin
from django import forms
from django.http import QueryDict

class AgreementForm(forms.Form):
    agree = forms.BooleanField(required=True, label="I agree to these terms.")

class AgreementDetailView(DetailView):
    def get_form(self):
        return AgreementForm()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['form'] = self.get_form()
        return context

class AgreementFormView(SingleObjectMixin, FormView):
    form_class = AgreementForm

    def get_success_url(self):
        return self.request.GET['next']

    def form_valid(self, form):
        object = self.get_object()
        self.request.session['kf.agreement.{}.{}'.format(object.pk, object.version)] = True
        if not self.request.user.is_anonymous:
            object.users.through.objects.update_or_create(defaults={'version': object.version}, user=self.request.user, agreement=object)
        return super().form_valid(form)

    def post(self, *args, **kwargs):
        self.object = super().get_object()
        return super().post(*args, **kwargs)

class AnonymousAgreementCheck(DetailView):
    @classmethod
    def should_handle(cls, request, object):
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

    @classmethod
    def should_handle(cls, request, object):
        if not request.user.is_anonymous:
            session_key = "kf.agreement.{}.{}".format(object.pk, object.version)
            agreed = request.session.get(session_key, False)
            if not agreed:
                agreed = object.users.through.objects.filter(user=request.user, agreement=object, version__gte=object.version)
            return not agreed
        return False

class TestAgreement(TestCase):
    def test_get(self):
        agreement = Agreement()
        view = AgreementDetailView()
        view.model = Agreement
        request = RequestFactory().get('/', kwargs={'pk': agreement.pk}, data={"next":"success"})
        view.setup(request, pk=agreement.pk)
        view.object = agreement
        context = view.get_context_data()
        self.assertIn('form', context)

    def test_post_anonymous_disagree(self):
        agreement = Agreement.objects.create()
        client = Client()
        resp = client.post('/test/postagreement/{}?next=/success'.format(agreement.pk))
        self.assertFalse(client.session.get('kf.agreement.{}.{}'.format(agreement.pk, agreement.version), False))
        self.assertEqual(resp.status_code, 200)

    def test_post_anonymous_agree(self):
        agreement = Agreement.objects.create()
        form = AgreementForm(data={'agree': True})
        client = Client()
        resp = client.post('/test/postagreement/{}?next=/success'.format(agreement.pk), data=form.data)
        self.assertTrue(client.session['kf.agreement.{}.{}'.format(agreement.pk, agreement.version)])
        self.assertRedirects(resp, '/success', fetch_redirect_response=False)

    def test_post_user_agree(self):
        agreement = Agreement.objects.create()
        form = AgreementForm(data={'agree': True})
        client = Client()
        resp = client.post('/test/postagreement/{}?next=/success'.format(agreement.pk), data=form.data)
        self.assertTrue(client.session['kf.agreement.{}.{}'.format(agreement.pk, agreement.version)])
        self.assertRedirects(resp, '/success', fetch_redirect_response=False)

    def test_anonymous_check(self):
        agreement = Agreement.objects.create()
        view = AnonymousAgreementCheck
        request = RequestFactory().get('/', kwargs={'pk': agreement.pk})
        request.user = AnonymousUser
        request.session = {}
        self.assertTrue(view.should_handle(request, agreement))
        client = Client()
        resp = client.post('/test/postagreement/{}?next=/success'.format(agreement.pk), data={'agree': True})
        request.session = client.session
        self.assertFalse(view.should_handle(request, agreement))

    def test_user_check(self):
        agreement = Agreement.objects.create()
        view = UserAgreementCheck
        request = RequestFactory().get('/', kwargs={'pk': agreement.pk})
        request.user = User.objects.create_user("test", "test", "test")
        request.session = {}
        self.assertTrue(view.should_handle(request, agreement))
        client = Client()
        client.force_login(request.user)
        resp = client.post('/test/postagreement/{}?next=/success'.format(agreement.pk), data={'agree': True})
        # requesting without session data, should retrieve agreement status from
        # db
        self.assertFalse(view.should_handle(request, agreement))

    def test_user_check_redirect(self):
        agreement = Agreement()
        agreement.pk = 1
        client = Client()
        resp = client.get('/test/agreementcheck/{}'.format(agreement.pk))
        self.assertRedirects(resp, '/test/postagreement/{pk}?next=http%3A//testserver/test/agreementcheck/{pk}'.format(pk=agreement.pk), fetch_redirect_response=False)
