from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import normalize_email

User = get_user_model()


class AuthenticationForm(DjangoAuthenticationForm):
    username = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(
            attrs={"autocomplete": "username", "placeholder": "you@example.com"}
        ),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": "Введи пароль"}
        ),
    )


class RegistrationForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "placeholder": "student@university.edu"}
        ),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        min_length=6,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Придумай надёжный пароль",
            }
        ),
    )

    def clean_email(self):
        email = normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Пользователь с таким email уже зарегистрирован."
            )
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        email = self.cleaned_data.get("email", "")
        validate_password(password, user=User(email=email))
        return password
