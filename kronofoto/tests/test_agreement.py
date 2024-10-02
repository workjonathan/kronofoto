from hypothesis.extra.django import from_model, register_field_strategy, TestCase
from django.test import Client, RequestFactory, SimpleTestCase
from django.contrib.auth.models import AnonymousUser, User
from django.views.generic import TemplateView

from django import forms
from fortepan_us.kronofoto.views.agreement import AgreementDetailView, AgreementFormView, UserAgreementCheck, BaseAgreementView, AgreementCheckFactory
from .models import Agreement, UserAgreement
from fortepan_us.kronofoto.models.archive import ArchiveAgreement, Archive

class AgreementForm(forms.Form):
    agree = forms.BooleanField(required=True, label="I agree to these terms.")

class AgreementFake:
    session_key="session-key"
    version=2


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

    def test_user_check(self):
        agreement = Agreement.objects.create()
        user = User.objects.create_user("test", "test", "test")
        self.assertEqual(4,
            AgreementCheckFactory(
                view=3,
                redirect_view=4,
                func=5,
                session={},
                user=user,
                agreement=agreement,
                user_agreement_queryset=UserAgreement.objects.all(),
            ).get_agreement_checker().view
        )
        self.assertEqual(5,
            AgreementCheckFactory(
                view=3,
                redirect_view=4,
                func=5,
                session={'session-key': True},
                user=user,
                agreement=agreement,
                user_agreement_queryset=UserAgreement.objects.all(),
            ).get_agreement_checker().view
        )
        UserAgreement.objects.create(version=0, user=user, agreement=agreement)
        self.assertEqual(5,
            AgreementCheckFactory(
                view=3,
                redirect_view=4,
                func=5,
                session={},
                user=user,
                agreement=agreement,
                user_agreement_queryset=UserAgreement.objects.all(),
            ).get_agreement_checker().view
        )
        agreement.version = 1
        agreement.save()
        self.assertEqual(4,
            AgreementCheckFactory(
                view=3,
                redirect_view=4,
                func=5,
                session={},
                user=user,
                agreement=agreement,
                user_agreement_queryset=UserAgreement.objects.all(),
            ).get_agreement_checker().view
        )

class SimpleAgreementTestCase(SimpleTestCase):

    def test_anonymous_check(self):
        agreement = AgreementFake()
        self.assertEqual(3,
            AgreementCheckFactory(view=3,
                redirect_view=4,
                func=5,
                session={},
                user=AnonymousUser,
                agreement=agreement,
            ).get_agreement_checker().view
        )
        self.assertEqual(5,
            AgreementCheckFactory(
                view=3,
                redirect_view=4,
                func=5,
                session={'session-key': True},
                user=AnonymousUser,
                agreement=agreement,
            ).get_agreement_checker().view
        )
