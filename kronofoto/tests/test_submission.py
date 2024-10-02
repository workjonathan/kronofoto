from fortepan_us.kronofoto.views.submission import SubmissionFactory, TermListFactory, define_terms
from django.test import SimpleTestCase, TestCase, Client, RequestFactory
from django.http import QueryDict
from django.contrib.auth.models import AnonymousUser, User
from .models import FakeSubmission
from django.forms import ModelForm
from fortepan_us.kronofoto.models import Archive, ArchiveAgreement, Term, ValidCategory, Category
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

    def test_term_list_no_data(self):
        c = Client()
        archive = Archive.objects.create(slug="any-slug")
        resp = c.get(reverse('kronofoto:term-list', kwargs={'short_name': archive.slug}))
        self.assertEqual(200, resp.status_code)

    def test_term_list(self):
        archive1 = Archive.objects.create(slug="any-slug")
        archive2 = Archive.objects.create(slug="any-slug2")
        category1 = Category.objects.create(slug="cat-slug")
        category2 = Category.objects.create(slug="cat-slug2")
        term1 = Term.objects.create(term="a-term")
        term2 = Term.objects.create(term="a-term2")
        term3 = Term.objects.create(term="a-term3")
        term4 = Term.objects.create(term="a-term4")
        vc1 = ValidCategory.objects.create(archive=archive1, category=category1)
        vc2 = ValidCategory.objects.create(archive=archive1, category=category2)
        vc3 = ValidCategory.objects.create(archive=archive2, category=category1)

        vc1.terms.set([term1, term2])
        vc2.terms.set([term3])
        vc2.terms.set([term4])

        terms = TermListFactory(archive=archive1, data={"submission-category": f"{category1.id}"}).get_terms()
        self.assertIn(term1, terms)
        self.assertIn(term2, terms)
        self.assertNotIn(term3, terms)
        self.assertNotIn(term4, terms)

    def test_term_definer(self):
        term1 = Term.objects.create(term="a-term")
        term2 = Term.objects.create(term="a-term2")
        term3 = Term.objects.create(term="a-term3")
        data = QueryDict(f"submission-terms={term1.id}&submission-terms={term3.id}&submission-terms=cheese")
        request = RequestFactory().get("", data=data)
        resp = define_terms(request)
        self.assertIn(term1, resp.context_data['objects'])
        self.assertIn(term3, resp.context_data['objects'])
