# 103 — подача заявки через ORM

Ответственный: Влад. Ветка: `feat/103-demo_application`.

Цель: заменить временное хранилище моделями из main. Критерии приёмки:
запись заявки в PostgreSQL, проверка набора, мест, авторства, членства и дублей;
просмотр только своих заявок, защита от одновременной отправки, вход и CSRF.
Зависимости: модели и миграции Дениса, авторизация Дани, шаблоны Ахада.

В ветку включена сохранённая origin/main (`d494724`) с моделями accounts.User,
projects.Project, ProjectRole, ProjectMember, applications.Application и
начальными миграциями. Схема не изменена. Fetch завершился ошибкой TLS GitHub,
поэтому актуальность удалённой main на момент работы подтвердить не удалось.

## Изменения

- applications/services.py: ORM вместо памяти, поля user/project/role/comment,
  pending по умолчанию. Только pending блокирует повторную заявку; rejected
  допускает повтор. Членство проверяется через ProjectMember.
- Проверка и создание выполняются в transaction.atomic, сначала блокируется
  проект, затем роль. Остальные операции изменения набора/состава должны
  соблюдать этот порядок. Ожидаемый конфликт уникальности переводится в
  ошибку формы; остальные IntegrityError не скрываются.
- projects/selectors.py: ORM-выборки, with_occupancy для ролей.
- projects/views.py, applications/forms.py, временные шаблоны используют
  name/capacity/occupied_places. Каталог использует main.views.catalog.
- applications/storage.py удалён. Тесты драфта заменены проверками ORM/HTTP
  и гонки с отдельными соединениями PostgreSQL. tests/conftest.py поднимает
  отдельную тестовую БД для pytest без pytest-django.

## Подключение

Общие config, README, requirements и базовый шаблон не редактировались.
Существующий applications.demo_settings теперь подключает applications
и использует настоящую PostgreSQL. Нужны переменные окружения по README.

```powershell
python manage.py migrate --settings=applications.demo_settings
python manage.py seed_demo --settings=applications.demo_settings
python manage.py runserver --settings=applications.demo_settings
```

Маршруты драфта сохранены: GET /projects/ (projects:catalog),
GET /projects/<uuid:project_id>/ (projects:detail),
POST /projects/<uuid:project_id>/apply/ (applications:submit),
GET /applications/ (applications:mine). Все требуют входа.
POST принимает projectRoleId и comment до 300 символов; пользователь из
сессии, проект из URL. Успех: redirect в свои заявки; ошибка: HTTP 200 с формой.

Маршруты /applications/create/, /applications/my/ и HTMX-фрагменты из
командного контракта этим драфтом пока не реализованы. Подключение общих URL
и окончательных шаблонов требует согласования с техлидом и Ахадом.

## Проверки

Среда: Python 3.14.0, Django 5.2.17; командный Python 3.13.16 не установлен.
Инструменты установлены только в игнорируемую .venv.

- pip check и manage.py check --settings=applications.demo_settings: успешно.
- makemigrations --check --dry-run с теми же settings: No changes detected;
  история миграций не проверена из-за недоступной БД.
- python -m ruff check applications projects tests: успешно.
- python -m ruff check .: три существующих RET501 в accounts/middleware.py
  из main; чужой модуль не исправлялся.
- git diff --check: успешно.
- migrate --check и python -m pytest tests блокируются недоступной PostgreSQL
  на 127.0.0.1:5432. Docker Compose не смог скачать закреплённый образ
  PostgreSQL 17.11: TLS timeout Docker Hub.
- Браузерный сценарий и сохранение после перезапуска не проверены без БД.

## Передача PR

Заголовок: «103: заменить хранилище заявок моделями из main».

Описание: Подача и просмотр заявок используют согласованные ORM-модели.
Транзакция и блокировки защищают от повторной отправки. Формы и шаблоны
используют реальные поля ролей и занятость из ProjectMember. Схема не меняется.
Статические проверки изменённых модулей проходят; поведенческие требуют
доступного PostgreSQL 17.11.

Следующий шаг Влада: проверки на PostgreSQL 17.11 и Python 3.13.16, браузерный
сценарий, согласование URL/шаблонов и публикация PR на ревью.
Push и публикация PR в этой сессии не выполнялись.
