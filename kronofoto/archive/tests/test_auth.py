from django.test import TestCase, RequestFactory, tag
from django.urls import reverse
from ..auth.views import RegisterAccount
from django.contrib.auth.models import AnonymousUser


@tag("fast")
class RegisterAccountTest(TestCase):
    def testUserIsHumanShouldReturnFalse(self):
        req = RequestFactory().post(reverse('kronofoto:register-account'), data={'g-recaptcha-response': ''})
        req.user = AnonymousUser()
        v = RegisterAccount()
        v.request = req
        self.assertFalse(v.user_is_human())
