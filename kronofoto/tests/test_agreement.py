from hypothesis.extra.django import from_model, register_field_strategy, TestCase
from django.test import Client, RequestFactory
from django.contrib.auth.models import AnonymousUser, User
from django.views.generic import TemplateView

from django import forms
from archive.views.agreement import AgreementDetailView, AgreementFormView, UserAgreementCheck, BaseAgreementView
from .models import Agreement, UserAgreement
from archive.models.archive import ArchiveAgreement, Archive
from archive.views.submission import SubmissionFormView

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
        archive = Archive.objects.create(slug="any-slug")
        agreement = ArchiveAgreement.objects.create(archive=archive)
        view = SubmissionFormView()
        kwargs = {'short_name': archive.slug}
        request = RequestFactory().get('/', kwargs=kwargs)
        request.user = AnonymousUser
        request.session = {}
        view.setup(request, **kwargs)
        resp = view.dispatch(request, **kwargs)
        self.assertIn("archive/anonymous_agreement.html", resp.template_name)

        agreementview = BaseAgreementView(form_class=AgreementForm)
        request = RequestFactory().post('/?next=/success', kwargs=kwargs, data={"agree": False})
        request.user = AnonymousUser
        request.session = {}
        agreementview.setup(request, **kwargs)
        resp = agreementview.dispatch(request, **kwargs)
        self.assertEqual(200, resp.status_code)

        agreementview = BaseAgreementView(form_class=AgreementForm)
        request = RequestFactory().post('/?next=/success', kwargs=kwargs, data={"agree": True})
        request.user = AnonymousUser
        request.session = {}
        agreementview.setup(request, **kwargs)
        resp = agreementview.dispatch(request, **kwargs)
        self.assertEqual(302, resp.status_code)

        session = request.session
        class TestTemplateView(TemplateView):
            template_name = 'anything.html'

        view = SubmissionFormView(view=TestTemplateView)
        request = RequestFactory().get('/', kwargs=kwargs)
        request.session = session
        request.user = AnonymousUser
        view.setup(request, **kwargs)
        resp = view.dispatch(request, **kwargs)
        self.assertIn("anything.html", resp.template_name)

    def test_user_check(self):
        archive = Archive.objects.create(slug="any-slug")
        agreement = ArchiveAgreement.objects.create(archive=archive)
        class TestTemplateView(TemplateView):
            template_name = 'anything.html'
        view = SubmissionFormView(view=TestTemplateView)
        user = User.objects.create_user("test", "test", "test")

        kwargs = {'short_name': archive.slug}
        request = RequestFactory().get('/', kwargs=kwargs)
        request.user = user
        request.session = {}
        view.setup(request, **kwargs)
        resp = view.dispatch(request, **kwargs)
        self.assertEqual(302, resp.status_code)

        agreementview = BaseAgreementView(form_class=AgreementForm)
        request = RequestFactory().post('/?next=/success', kwargs=kwargs, data={"agree": False})
        request.user = user
        request.session = {}
        agreementview.setup(request, **kwargs)
        resp = agreementview.dispatch(request, **kwargs)
        self.assertEqual(resp.status_code, 200)

        agreementview = BaseAgreementView(form_class=AgreementForm)
        request = RequestFactory().post('/?next=/success', kwargs=kwargs, data={"agree": True})
        request.user = user
        request.session = {}
        agreementview.setup(request, **kwargs)
        resp = agreementview.dispatch(request, **kwargs)
        self.assertEqual(resp.status_code, 302)

        session = request.session

        view = SubmissionFormView(view=TestTemplateView)
        request = RequestFactory().get('/', kwargs=kwargs)
        request.session = session
        request.user = user
        view.setup(request, **kwargs)
        resp = view.dispatch(request, **kwargs)
        self.assertIn("anything.html", resp.template_name)

        view = SubmissionFormView(view=TestTemplateView)
        request = RequestFactory().get('/', kwargs=kwargs)
        request.session = {} # no session, should still render our top secret template
        request.user = user
        view.setup(request, **kwargs)
        resp = view.dispatch(request, **kwargs)
        self.assertIn("anything.html", resp.template_name)
