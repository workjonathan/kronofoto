from django.test import SimpleTestCase, RequestFactory, tag
from django.urls import reverse
from ..auth.views import RegisterAccount
from django.contrib.auth.models import AnonymousUser


@tag("fast")
class RegisterAccountTest(SimpleTestCase):
    def testUserIsHumanShouldReturnFalse(self):
        req = RequestFactory().post(reverse('register-account'), data={'g-recaptcha-response': ''})
        req.user = AnonymousUser()
        v = RegisterAccount()
        v.request = req
        self.assertFalse(v.user_is_human())
