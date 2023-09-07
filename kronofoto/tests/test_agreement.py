from hypothesis.extra.django import from_model, register_field_strategy, TestCase
from django.test import Client, RequestFactory
from django.contrib.auth.models import AnonymousUser, User

from django import forms
from archive.views.agreement import AgreementDetailView, AgreementFormView, AnonymousAgreementCheck, UserAgreementCheck
from .models import Agreement, UserAgreement

class AgreementForm(forms.Form):
    agree = forms.BooleanField(required=True, label="I agree to these terms.")

class TestAgreement(TestCase):
    def test_get(self):
        agreement = Agreement()
        view = AgreementDetailView(
            form_class=AgreementForm
        )
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
        self.assertTrue(view.should_handle(request, agreement, agreement.users.through))
        client = Client()
        client.force_login(request.user)
        resp = client.post('/test/postagreement/{}?next=/success'.format(agreement.pk), data={'agree': True})
        # requesting without session data, should retrieve agreement status from
        # db
        self.assertFalse(view.should_handle(request, agreement, agreement.users.through))

    def test_user_check_redirect(self):
        agreement = Agreement()
        agreement.pk = 1
        client = Client()
        resp = client.get('/test/agreementcheck/{}'.format(agreement.pk))
        self.assertRedirects(resp, '/test/postagreement/{pk}?next=http%3A//testserver/test/agreementcheck/{pk}'.format(pk=agreement.pk), fetch_redirect_response=False)
