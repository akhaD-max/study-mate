# Роли с требованиями и статус обучения в профиле

Ветка: `arena/60a6dca6-study-mate`

## 1. Требования к роли на странице проекта

- На странице проекта (`projects/templates/projects/detail.html`) название роли
  стало заголовком раскрывающегося блока `<details class="pg-role-details">`.
  Внутри — текст «Требования к роли»: описание роли (`ProjectRole.description`)
  и чипы обязательных навыков (`ProjectRole.required_skills`).
- Блок выводится только если у роли есть описание или навыки. Иначе название
  роли — обычный `<strong>`, как раньше. Нативные `<details>/<summary>` дают
  раскрытие без JS и работают с клавиатуры.
- Индикатор `+`/`−` реализован на CSS (`.pg-role-toggle`), доступность —
  через `summary` + `aria-hidden` у декоративной иконки.
- `ProjectRoleForm` получил поле `description` (textarea, 1000 символов,
  необязательное), `field_order = ("name", "capacity", "description", "required_skills")`.
  `create_project()` сохраняет его при создании роли. Так автор может задать
  требования при создании проекта, а не только через сиды.
- Миграции не нужны: поле `ProjectRole.description` уже было в схеме.

## 2. Статус обучения в профиле

Модель `accounts.User`:

| Поле | Значения |
| --- | --- |
| `education_status` | `""` (не указано), `studying`, `graduated` |
| `education_level` | `""`, `bachelor`, `specialist`, `master`, `postgraduate` |
| `course` | `1..6`, `NULL` (оставлено для совместимости) |

Набор курсов по уровню (`EDUCATION_COURSE_LIMITS`, `accounts/models.py`):

| Уровень | Курсы |
| --- | --- |
| Бакалавриат | 1–4 |
| Специалитет | 1–5 |
| Магистратура | 1–2 |
| Аспирантура | 1–3 |

Правила формы (`ProfileForm`):

- выбор курса заблокирован (`disabled`, пустой список), пока уровень не выбран;
- при статусе «обучаюсь» обязательны и уровень, и курс; курс обязан входить
  в диапазон уровня, иначе ошибка валидации;
- при статусе «закончил обучение» (и при пустом статусе) курс очищается
  в `cleaned_data`, поэтому в БД не сохраняется;
- список курсов пересобирается от выбранного уровня при отрисовке формы;
- `accounts/services.py::update_profile()` записывает новые поля
  (список `PROFILE_FIELDS`).

Клиентская часть (`static/js/profile.js`):

- уровень и курс дизейблятся/включаются по цепочке статус → уровень → курс;
- при смене уровня список опций курса пересобирается по тому же справочнику,
  выбранное значение сбрасывается, если оно не входит в новый диапазон.

Отображение: `profile_detail.html` показывает `education_summary()`
(например, «Обучаюсь · магистратура · 1 курс»); у выпускника курс не выводится.

## Миграция

`accounts/migrations/0004_education_fields.py`: добавлены два поля, у `course`
убран `choices` (остались валидаторы), добавлены check-constraints на
допустимые значения, затем `RunPython`, который проставляет существующим
пользователям с курсом 1–4 «обучаюсь / бакалавриат», а с курсом 5–6 —
«обучаюсь / специалитет».

## Проверки

```
.venv/bin/python -m ruff check .                     # All checks passed
manage.py check                                      # 0 issues
manage.py makemigrations --check --dry-run           # No changes detected
manage.py migrate                                    # 0004 применена
manage.py test --noinput                             # 199 тестов, 5 прежних падений + 1 прежняя ошибка
```

Новые тесты: `tests/accounts/test_profile_education.py` (11),
`tests/projects/test_role_requirements.py` (6).

Живая проверка (curl, пользователь `owner@studymate.local`):
`/profile/edit/` отдаёт три связанных селекта, курс сразу `disabled` с подсказкой
«Сначала выберите уровень образования»; `/projects/<id>/` рисует
`<details>` с названием роли в `summary`; `/projects/create/` показывает
textarea `roles-0-description`.
