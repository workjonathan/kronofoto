from django import forms
from .widgets import RecaptchaWidget
from django.conf import settings
from django.core.exceptions import ValidationError
import urllib
import json


class RecaptchaField(forms.CharField):
    widget = RecaptchaWidget
    def __init__(self, required_score=0.7, label=False, *args, **kwargs):
        super().__init__(label=label, *args, **kwargs)
        self.required = True
        self.widget.attrs['data-sitekey'] = settings.GOOGLE_RECAPTCHA3_SITE_KEY
        self.required_score = required_score

    def check_captcha(self, value):
        data = {
            'secret': settings.GOOGLE_RECAPTCHA3_SECRET_KEY,
            'response': value,
        }
        args = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request('https://www.google.com/recaptcha/api/siteverify', data=args)
        response = urllib.request.urlopen(req)
        return json.loads(response.read().decode())

    def validate(self, value):
        super().validate(value)
        result = self.check_captcha(value)
        if not result['success']:
            raise ValidationError("Captcha failure")
        if result['score'] < self.required_score:
            raise ValidationError("Captcha failure")
