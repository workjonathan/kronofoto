from hypothesis.extra.django import from_model, register_field_strategy, TestCase
from unittest.mock import Mock
from django.test import Client, RequestFactory, SimpleTestCase
from django.contrib.auth.models import AnonymousUser, User

from django.views.generic import FormView
from django import forms
from archive.widgets import RecaptchaWidget
from archive.fields import RecaptchaField



class RecaptchaForm(forms.Form):
    response = RecaptchaField()

class RecaptchaFormView(FormView):
    form_class = RecaptchaForm

    def get_success_url(self):
        return self.request.GET['next']

    def form_valid(self, form):
        pass

class TestForm(SimpleTestCase):
    def testFail(self):
        form = RecaptchaForm(data={"response": "alksdjf"})
        form.fields['response'].check_captcha = Mock(return_value={'success': False})
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors)

    def testSucceed(self):
        form = RecaptchaForm(data={"response": "alksdjf"})
        form.fields['response'].check_captcha = Mock(return_value={'success': True, 'score': 0.9})
        self.assertTrue(form.is_valid())
        self.assertFalse(form.errors)
