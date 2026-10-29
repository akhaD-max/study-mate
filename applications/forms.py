from django import forms


class ApplicationForm(forms.Form):
    projectRoleId = forms.TypedChoiceField(
        label="Роль", coerce=str,
        error_messages={"invalid_choice": "Выберите доступную роль этого проекта."},
    )
    comment = forms.CharField(
        label="Сопроводительное письмо", max_length=300, required=False,
        strip=False, widget=forms.Textarea(attrs={"maxlength": 300, "rows": 4}),
    )

    def __init__(self, *args, roles, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["projectRoleId"].choices = [
            (str(role.id), role.name) for role in roles if role.is_available
        ]
