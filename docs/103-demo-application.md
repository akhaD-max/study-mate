# 103 — проект → заявка → свои заявки

Ответственный: Влад. Ветка: `feat/103-demo_application`. Цель текущего этапа —
обычные HTML GET/POST с временным хранилищем вместо ещё не готовых моделей.
Модели/миграции — Денис, сессия — Даня, шаблоны — Ахад, корневые URL — техлид.
Это предложение контракта: утверждённого `sprint-4-contract.md` в копии нет.

## Передача Ахаду до интеграции

| Метод и URL | Имя | Шаблон и context |
| --- | --- | --- |
| GET `/projects/` | `projects:catalog` | `projects/catalog.html`: `projects` |
| GET `/projects/<uuid:project_id>/` | `projects:detail` | `projects/detail.html`: `project`, `roles`, `form`, `can_apply`, `application_block_reason` |
| POST `/projects/<uuid:project_id>/apply/` | `applications:submit` | Ошибка: тот же `projects/detail.html` и context, HTTP 200 |
| GET `/applications/` | `applications:mine` | `applications/my_applications.html`: `applications` |

Все операции требуют входа. POST — обычная форма с `{% csrf_token %}`,
`projectRoleId` (UUID роли), `comment` (необязательное письмо ≤300 символов).
Action: `{% url 'applications:submit' project.id %}`. Пользователь берётся
исключительно из `request.user`, проект — исключительно из URL.
При успехе — 302 на `applications:mine`, Django message
«Заявка успешно отправлена!». Страница списка читает сохранённые объекты.
Ошибки роли находятся в `form.projectRoleId.errors`, остальные —
`form.non_field_errors`; связанная форма сохраняет письмо. HTMX пока не реализован.
Неизвестный проект — 404, неподдерживаемый метод — 405, POST без CSRF — 403.

Проект: `id`, `title`, `description`, `author_id`, `status` (`open`).
Роль: `id`, `project_id`, `title`, `is_open`, `total_places`, `filled_places`,
`is_available`. `roles` содержит все роли; form choices — только доступные.
Заявка: `id`, `student_id`, `project`, `role`, `comment`, `created_at`,
`status`, `get_status_display()`; статусы: `pending`, `accepted`, `rejected`.
Список фильтруется по текущему студенту, новые записи сверху.

## Временное хранилище и запуск

`applications/storage.py` содержит только структуры данных Python, не ORM-модели.
Данные общие для вкладок одного процесса, защищены RLock на время проверки и
создания; pending не занимает место. Дубль pending/accepted запрещён на проект
независимо от роли. Проверяются авторство, членство, набор и вместимость.
Данные исчезают при перезапуске и **не разделяются между worker-процессами**.
Хранилище доступно только при `APPLICATIONS_USE_DEMO_STORAGE=True`.

Отдельные `applications/demo_settings.py` и `applications/demo_urls.py` позволяют
проверить интеграцию без правок командных settings/корневых URL:

```powershell
# Переменные окружения и зависимости — по README.
python manage.py runserver --settings=applications.demo_settings
```

Демо-карточка: `/projects/00000000-0000-0000-0000-000000000001/`.
Временные HTML-шаблоны лежат в `applications/demo_templates/`; поиск в них
включён только demo_settings. Ахад создаёт командные шаблоны по таблице выше.
Текущий accounts/login — заглушка: браузерная отправка требует сессии Дани;
самодельный вход и запись Django auth-миграций здесь не добавляются.

## Подключение реальной БД

После контракта Дениса заменить storage/selectors и транзакционную часть
`submit_application`, сохранив HTTP-контракт. Использовать `transaction.atomic`,
совместимые блокировки проекта/роли, повторное чтение статусов и членства,
ограничение уникальности активной заявки; ожидаемый IntegrityError переводить
в ValidationError после выхода из atomic. RLock не заменяет блокировки БД.
Имена ORM-полей и конкретный UniqueConstraint пока не утверждены.

Техлиду: подключить `projects.urls` и `applications.urls` по примеру demo_urls,
зарегистрировать приложения при появлении моделей, согласовать LOGIN_URL.
Модели, миграции, config, README, requirements и базовый шаблон не меняются.

## Проверки и приёмка

Регрессии в `tests/projects/` и `tests/applications/` не обращаются к БД;
они проверяют HTTP, валидацию, приватность, CSRF, повтор из второй вкладки и
конкурентный дубль в одном процессе. Это не проверка PostgreSQL-транзакций.
Совместная браузерная проверка с Ахадом, PostgreSQL, сохранение после перезапуска
и гонки на отдельных соединениях остаются обязательными при интеграции.

PR: «103: HTML-подача заявки и свои заявки с явным демохранилищем».
Публикацию и review выполняет разработчик; результаты локальных команд ниже
дополняются после запуска.

### Результаты локально

- Python 3.14 (имеется локально; командный Python 3.13.16 не установлен), Django 5.2.17.
- `python -m pytest tests -q`: **20 passed**, без обращения к БД.
- `python -m ruff check .` и дополнительная проверка E4/E7/E9/F: успешно.
- `python -m pip check`: успешно. Инструменты установлены только в игнорируемую
  `.venv`, командный requirements не менялся.
- `python manage.py check --settings=applications.demo_settings`: ошибок нет.
- `makemigrations --check --dry-run --settings=applications.demo_settings`:
  `No changes detected`, с предупреждением о недоступной истории миграций БД.
- `migrate --check --settings=applications.demo_settings`: не пройден,
  локальный PostgreSQL отвечает таймаутом подключения (также вне песочницы).
- `git diff --check`: успешно.

Проверки на командном Python, PostgreSQL и в браузере с настоящей сессией пока
не выполнены. В HTTP-тестах тестовый клиент подставляет пользователя в request;
это проверка границ доступа обработчиков, не проверка реализации входа Дани.
