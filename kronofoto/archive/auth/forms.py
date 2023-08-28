from .token import UserEmailVerifier
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import AuthenticationForm

class FortepanAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'

class RegisterUserForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    password2 = forms.CharField(label='Verify Password', widget=forms.PasswordInput(attrs={'placeholder': 'Password again'}))

    def __init__(self, user_checker=UserEmailVerifier(), **kwargs):
        self.user_checker = user_checker
        super().__init__(**kwargs)

    def clean(self):
        data = super().clean()
        if 'email' in data and User.objects.filter(username=data['email']).exists():
            self.add_error('email', 'There is already an account associated with that email address.')
        if 'password1' in data:
            validate_password(data['password1'])
            if 'password2' not in data or data['password1'] != data['password2']:
                self.add_error('password1', 'The password fields must be identical')
        return data

    def create_user(self):
        username = self.cleaned_data['email']
        password = self.cleaned_data['password1']
        user = User.objects.create_user(username, password=password, email=username, is_active=False)
        self.user_checker.verify(user)
