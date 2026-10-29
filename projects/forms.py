from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseFormSet, formset_factory

from .models import Category
from .selectors import list_categories


class ProjectCreateForm(forms.Form):
    title = forms.CharField(label="Название", min_length=3, max_length=100)
    description = forms.CharField(label="Описание", max_length=5000, widget=forms.Textarea)
    category_id = forms.ModelChoiceField(label="Категория", queryset=Category.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category_id"].queryset = list_categories()


class ProjectRoleForm(forms.Form):
    name = forms.CharField(label="Название роли", max_length=100)
    capacity = forms.IntegerField(label="Количество мест", min_value=1, max_value=20)


class BaseProjectRoleFormSet(BaseFormSet):
    @classmethod
    def get_default_prefix(cls):
        return "roles"

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        names = set()
        for form in self.forms:
            if not form.cleaned_data:
                continue
            name = form.cleaned_data["name"].casefold()
            if name in names:
                raise ValidationError("Названия ролей внутри проекта не должны повторяться.")
            names.add(name)


ProjectRoleFormSet = formset_factory(
    ProjectRoleForm, formset=BaseProjectRoleFormSet,
    extra=0, min_num=1, validate_min=True,
)
