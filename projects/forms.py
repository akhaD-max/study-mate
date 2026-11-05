from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseFormSet, formset_factory

from .models import Category
from .selectors import list_categories


class CatalogFilterForm(forms.Form):
    """Проверяем GET так же, как данные обычной формы, до обращения к поиску.

    Не используем ChoiceField для направления/роли: корректное, но уже удалённое
    значение из сохранённой ссылки должно дать пустую выдачу, а не ошибку формы.
    Списки вариантов для интерфейса при этом всегда загружаются из БД.
    """

    q = forms.CharField(
        required=False, max_length=200,
        error_messages={"max_length": "Введите не более 200 символов"},
    )
    direction = forms.SlugField(
        required=False, max_length=100, allow_unicode=True,
        error_messages={"invalid": "Некорректный формат направления"},
    )
    role = forms.CharField(required=False, max_length=100)
    open_only = forms.ChoiceField(
        choices=[("true", "Только с открытым набором"), ("false", "Все проекты")],
        error_messages={
            "required": "Укажите open_only=true или open_only=false.",
            "invalid_choice": "Укажите open_only=true или open_only=false.",
        },
    )
    sort = forms.CharField(required=False)
    page = forms.CharField(required=False)

    def __init__(self, data):
        data = data.copy()
        # Отсутствие параметра и пустая строка — разные случаи. Пустую строку
        # для open_only не подменяем default: она должна получить HTTP 400.
        if "open_only" not in data:
            data["open_only"] = "true"
        super().__init__(data)

    def clean_open_only(self):
        # bool("false") даёт True; разбираем строковое значение явно.
        return self.cleaned_data["open_only"] == "true"

    def clean_sort(self):
        value = self.cleaned_data["sort"]
        return value if value in {"newest", "oldest", "members", "fewer_members"} else "newest"

    def clean(self):
        cleaned = super().clean()
        for name in self.fields:
            if len(self.data.getlist(name)) > 1:
                self.add_error(name, "Передайте параметр один раз")
        return cleaned


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
