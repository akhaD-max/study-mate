# Запуск подготовленного каркаса

Это подробная инструкция для ветки `feature/django-docker-bootstrap`.
Краткий запуск приведён в README.
Созданы `manage.py`, `config`, шаблоны и инфраструктура. Пользовательских
приложений и миграций нет. Корневая страница возвращает страницу готовности.

## Всё в Docker

На компьютере нужны Git, запущенный Docker Desktop в режиме Linux containers
и Docker Compose. Python на компьютере для самой сборки не требуется.

```powershell
git clone https://github.com/akhaD-max/study-mate.git
cd study-mate
# До интеграции изменений в main:
git switch feature/django-docker-bootstrap
docker compose build
```

Команда сборки работает и без `.env`: скачивает закреплённые по digest образы
Python 3.13.16 и PostgreSQL 17.11, устанавливает Python-зависимости из
`requirements.txt`. Секреты понадобятся при запуске, в образ они не включаются.
PostgreSQL также имеет Dockerfile: поэтому его образ скачивается уже во время
`docker compose build`, а не только при первом `up`.

Создать `.env` можно Python из собранного образа, без установки Python на ПК:

```powershell
docker compose run --rm --no-deps --user 0 --volume "${PWD}:/workspace" --workdir /workspace web python scripts/setup_env.py
docker compose config --quiet
docker compose up -d --wait
docker compose ps
```

В Linux/macOS вместо `${PWD}` можно использовать `$(pwd)`. Временный контейнер
с `--user 0` нужен только для создания файла на смонтированном каталоге.
Обычный `web` работает от пользователя `django` без прав root.

Открыть http://127.0.0.1:8000/. HTMX уже находится в `static/vendor`, CDN и npm
не нужны. Код копируется в образ; после изменения исходников повторить
`docker compose build` и `docker compose up -d --wait`.

В `.env` при необходимости изменить `WEB_PORT` или `POSTGRES_PORT`.
Оба порта публикуются только на `127.0.0.1`. Данные PostgreSQL сохраняются
в именованном volume конкретного Compose-проекта.

```powershell
docker compose logs --tail=100 web db
docker compose stop
```

`stop` сохраняет данные. Не использовать `down -v` для обычной остановки.

## Локальный Python, PostgreSQL в Docker

В этой рабочей копии переносимый официальный CPython находится в
`.python/tools/python.exe`; `.venv` создана на его основе. Системный Python
3.11.9 не используется. `.python`, `.venv`, `.local` и `.env` игнорируются Git
и исключены из контекста Docker. Их не нужно переносить коллегам.

При уже установленном CPython 3.13.16 на другом Windows-компьютере:

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

В подготовленной рабочей копии:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe scripts/setup_env.py
docker compose up -d --wait db
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 runserver 127.0.0.1:8000
```

`setup_env.py` создаёт случайные ключ и пароль, существующий `.env` сохраняет.
`local.ps1` загружает `.env` в окружение процесса и устанавливает `DB_HOST`
в `127.0.0.1`, `DB_PORT` в значение `POSTGRES_PORT`. Django сам `.env` не читает.
Формат файла: `KEY=value` без кавычек и подстановок. ExecutionPolicy меняется
только для запуска указанного процесса, системная политика не меняется.
Не запускать локальный сервер и контейнер `web` на одном порту.

## Миграции и следующий шаг

Стандартные приложения `django.contrib` присутствуют в каркасе. Доменных
приложений пока нет. До создания первой рабочей схемы команда должна утвердить
кастомного пользователя, как указано в AGENTS.md. Автоматического `migrate`
при старте контейнера нет. Страница готовности работает без таблиц, admin
потребует согласованной схемы и применения миграций.

После согласования модели пользователя и добавления соответствующего приложения:

```powershell
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py createsuperuser
```

Для локального Python аналогично использовать `scripts/local.ps1 migrate`
и `scripts/local.ps1 createsuperuser`.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pip check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 makemigrations --check --dry-run
docker compose run --rm web python -m pip check
docker compose run --rm web python manage.py check
git diff --check
```

Ruff 0.17.1 установлен только в служебной `.local/lint` для проверки этой задачи:

```powershell
.\.local\lint\Scripts\python.exe -m ruff check .
```

Версии Ruff/pytest в командных зависимостях и их включение в dev-образ остаются
за техлидом согласно AGENTS.md. Исходный requirements.txt не изменён. Pytest
не запускался: тестов и бизнес-приложений ещё нет; фиктивные тесты не добавлены.

Этот Compose запускает сервер разработки Django. Подготовка production-сервера
и HTTPS в задачу создания каркаса не входит.
