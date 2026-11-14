from typing import ClassVar

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import Skill, Specialization, normalize_email

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


class UniqueSkillsField(forms.ModelMultipleChoiceField):
    def clean(self, value):
        if value:
            # UUID нормализуется до сравнения: разные написания одного UUID — дубль.
            try:
                normalized = [
                    self.queryset.model._meta.pk.to_python(item) for item in value
                ]
            except (forms.ValidationError, TypeError, ValueError):
                raise forms.ValidationError("Выберите навыки из справочника.") from None
            if len(normalized) != len(set(normalized)):
                raise forms.ValidationError("Навыки не должны повторяться.")
            if len(normalized) > 15:
                raise forms.ValidationError("Выберите не больше 15 навыков.")
        return super().clean(value)


class ProfileForm(forms.ModelForm):
    university = forms.CharField(
        label="Вуз",
        max_length=200,
        error_messages={"required": "Заполните обязательное поле"},
    )
    specialty = forms.CharField(
        label="Специальность",
        max_length=200,
        error_messages={"required": "Заполните обязательное поле"},
    )
    course = forms.TypedChoiceField(
        label="Курс",
        coerce=int,
        choices=[("", "Выберите курс")]
        + [(number, str(number)) for number in range(1, 7)],
        error_messages={
            "required": "Укажите корректный курс обучения",
            "invalid_choice": "Укажите корректный курс обучения",
        },
    )
    skills = UniqueSkillsField(
        label="Навыки",
        queryset=Skill.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text="Выберите от 1 до 15 навыков суммарно из обеих категорий.",
        error_messages={
            "required": "Выберите хотя бы один навык.",
            "invalid_choice": "Выберите навыки из справочника.",
            "invalid_pk_value": "Выберите навыки из справочника.",
        },
    )
    desired_role = forms.ModelChoiceField(
        label="Желаемая роль",
        queryset=Specialization.objects.none(),
        required=False,
        empty_label="Не указана",
        help_text="Выберите, какие задачи вы хотите выполнять в команде",
        error_messages={"invalid_choice": "Выберите доступную роль из справочника."},
    )

    class Meta:
        model = User
        fields = (
            "full_name",
            "university",
            "specialty",
            "course",
            "skills",
            "desired_role",
            "bio",
        )
        labels: ClassVar[dict] = {"full_name": "Имя и фамилия"}
        widgets: ClassVar[dict] = {
            "bio": forms.Textarea(attrs={"rows": 8, "aria-describedby": "bio-counter"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skills"].queryset = Skill.objects.filter(is_active=True)
        self.fields["desired_role"].queryset = Specialization.objects.filter(
            is_active=True
        )
        self.fields["skills"].label_from_instance = lambda skill: (
            f"{skill.name} — {skill.get_category_display()}"
        )
