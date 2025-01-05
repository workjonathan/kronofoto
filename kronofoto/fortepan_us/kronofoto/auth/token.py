from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.contrib.auth.models import User, AbstractBaseUser
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from fortepan_us.kronofoto.reverse import reverse
from django.conf import settings
from typing import Any, Dict, List, Union, Optional, Protocol

class TokenGen(Protocol):
    def make_token(self, user: User) -> str:
        ...
    def check_token(self, user: Optional[User], token: Optional[str]) -> bool:
        ...

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user: AbstractBaseUser, timestamp: Any) -> str:
        return '{uid}_{timestamp}_{active}'.format(
            uid=user.pk, timestamp=timestamp, active=user.is_active
        )

class UserEmailVerifier:
    def __init__(self, token_gen: TokenGen=AccountActivationTokenGenerator()):
        self.token_gen = token_gen

    def verify(self, user: User) -> None:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = self.token_gen.make_token(user)

        url = reverse('activate', kwargs={'uid': uid, 'token': token})
        message = """Hi,
        Thank you for making an account with Fortepan Iowa.
        Please click on the link below to confirm your email address.

        {path}

        If you don't know what this is about, please ignore this email.""".format(
            path=url
        )
        subject = 'Account Activation'

        email = EmailMessage(subject=subject, body=message, to=[user.email])
        email.send(fail_silently=False)

    def verify_token(self, uid: int, token: str) -> Optional[User]:
        uid2 = urlsafe_base64_decode(str(uid)).decode()
        try:
            user = User.objects.get(pk=uid2)
            if self.token_gen.check_token(user, token):
                user.is_active = True
                user.save()
                return user
            else:
                return None
        except User.DoesNotExist:
            return None
