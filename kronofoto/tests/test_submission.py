from archive.views.submission import SubmissionFactory
from django.test import SimpleTestCase, TestCase, Client, RequestFactory
from django.contrib.auth.models import AnonymousUser, User
from .models import FakeSubmission
from django.forms import ModelForm
from archive.models import Archive, ArchiveAgreement
from django.urls import reverse

class FakeSubmissionForm(ModelForm):
    class Meta:
        fields = ['x']
        model = FakeSubmission

class SubmissionTest(TestCase):
    def test_basic_request(self):
        c = Client()
        archive = Archive.objects.create(slug="any-slug")
        agreement = ArchiveAgreement.objects.create(archive=archive)
        session = c.session
        session[agreement.session_key] = True
        session.save()
        resp = c.get(reverse('kronofoto:submission-create', kwargs={'short_name': archive.slug}))
        self.assertEqual(200, resp.status_code)
        self.assertIn('form', resp.context_data)

    def test_invalid_post(self):
        request = RequestFactory().post("", data={})
        resp = SubmissionFactory(request, None, None, {}, form_class=FakeSubmissionForm).get_response()
        self.assertEqual(200, resp.status_code)
        self.assertIn("form", resp.context_data)

    def test_valid_post(self):
        request = RequestFactory().post("", data={"x": 19})
        archive = Archive.objects.create(slug="any-slug")
        resp = SubmissionFactory(request, AnonymousUser, archive, {}, form_class=FakeSubmissionForm).get_response()
        self.assertEqual(302, resp.status_code)
        self.assertTrue(FakeSubmission.objects.filter(x=19, uploader=None, archive=archive).exists())

    def test_valid_post_from_user(self):
        request = RequestFactory().post("", data={"x": 19})
        archive = Archive.objects.create(slug="any-slug")
        user = User.objects.create_user("test", "test", "test")
        resp = SubmissionFactory(request, user, archive, {}, form_class=FakeSubmissionForm).get_response()
        self.assertEqual(302, resp.status_code)
        self.assertTrue(FakeSubmission.objects.filter(x=19, uploader=user, archive=archive).exists())
