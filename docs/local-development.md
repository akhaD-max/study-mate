# Запуск подготовленного окружения и демо-данных

Инструкция по локальному запуску `StudyMate` через Docker Compose или локальную
`.venv`, применению миграций и загрузке повторяемых демонстрационных данных.
Краткий порядок приведён также в `README.md`.

## Всё в Docker

На компьютере нужны Git, запущенный Docker Desktop в режиме Linux containers
и Docker Compose. Python на компьютере для самой сборки не требуется.

```powershell
git clone https://github.com/akhaD-max/study-mate.git
cd study-mate
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
```

В Linux/macOS вместо `${PWD}` можно использовать `$(pwd)`. Временный контейнер
с `--user 0` нужен только для создания файла на смонтированном каталоге.
Обычный `web` работает от пользователя `django` без прав root.

В `.env` при необходимости изменить `WEB_PORT` или `POSTGRES_PORT`.
Оба порта публикуются только на `127.0.0.1`. Данные PostgreSQL сохраняются
в именованном volume конкретного Compose-проекта. Файл `.env` и реальные пароли
пользователей никогда не коммитятся в репозиторий.

```powershell
docker compose logs --tail=100 web db
docker compose stop
```

`stop` сохраняет данные. Не использовать `down -v` для обычной остановки.

## Локальный Python, PostgreSQL в Docker

В подготовленной рабочей копии переносимый официальный CPython находится в
`.python/tools/python.exe`; `.venv` создана на его основе. `.python`, `.venv`,
`.local` и `.env` игнорируются Git и исключены из контекста Docker.

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
Формат файла: `KEY=value` без кавычек и подстановок. Не запускать локальный
сервер и контейнер `web` на одном порту.

## Миграции и демонстрационные данные (`seed_demo`)

Автоматического `migrate` и автозагрузки фикстур при старте контейнера или внутри
миграций нет: и миграции, и демо-данные запускаются явно.

### Запуск в Docker Compose

```powershell
docker compose up -d --wait db
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py seed_demo --password <ваш_демо_пароль>
docker compose up -d --wait web
```

Вместо аргумента `--password` можно передать переменную окружения
`SEED_DEMO_PASSWORD` (поддерживается и алиас `DEMO_PASSWORD`):

```powershell
docker compose run --rm -e SEED_DEMO_PASSWORD=<ваш_демо_пароль> web python manage.py seed_demo
```

### Запуск через локальную `.venv`

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 migrate --noinput
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 seed_demo --password <ваш_демо_пароль>
```

Либо с переменной окружения в текущей PowerShell-сессии:

```powershell
$env:SEED_DEMO_PASSWORD = '<ваш_демо_пароль>'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 seed_demo
```

### Правила пароля и идемпотентности

- Пароль должен содержать **минимум 6 символов** (единое правило со сценарием
  регистрации и входа в `accounts`). Пароль хешируется стандартным механизмом
  Django (`set_password` / PBKDF2) и в открытом виде нигде не хранится.
- Учётные записи реальных пользователей (например, созданные через регистрацию
  или `createsuperuser`) командой не затрагиваются.
- Повторный вызов `seed_demo` безопасен: дубли пользователей, направлений,
  проектов, ролей, членства и заявок не создаются, а заявки и статусы, уже
  отправленные или изменённые при ручной проверке, не удаляются и не сбрасываются.

### Что создаёт `seed_demo` для проверки 4-го спринта

| Учётная запись | Назначение |
| --- | --- |
| `author@studymate.local` | Автор демо-проектов (проверка запрета отклика на собственный проект) |
| `student1@studymate.local` | Основной студент для проверки подачи заявки, негативных сценариев и раздела «Мои заявки» |
| `student2@studymate.local` | Второй студент (занимает место в команде и имеет собственную заявку для проверки изоляции чужих откликов) |

| Проект | Статус | Подготовленные роли и сценарии проверки |
| --- | --- | --- |
| Платформа учебных команд StudyMate | `open` | `Backend-разработчик` (свободная роль, `0/2`) — успешная подача; `Frontend-разработчик` (занятая роль, `1/1`, участник `student2`) — отказ из-за отсутствия мест; `UI/UX дизайнер` (`is_open=False`) — отказ из-за закрытого набора роли |
| Телеграм-бот расписания и дедлайнов | `open` | У `student1` уже создана заявка `pending` («На рассмотрении») на `Python-разработчик` — проверка блокировки повторного активного отклика на проект |
| Аналитика вовлечённости онлайн-курсов | `in_progress` | Набор проекта закрыт, `student1` состоит в команде (`Data Analyst`) и имеет образец заявки `accepted` («Принята») |
| Дизайн-система студенческих сервисов | `open` | Образец заявки `rejected` («Отклонена») у `student1` и активная заявка `pending` у `student2` (проверка всех статусов и невидимости чужих заявок) |

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pip check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 makemigrations --check --dry-run
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local.ps1 migrate --check
docker compose run --rm web python -m pip check
docker compose run --rm web python manage.py check
git diff --check
```

Ruff 0.17.1+ используется для статической проверки `python -m ruff check .`, а
автотесты запускаются командами `python manage.py test tests` / `python -m pytest tests`
на отдельной тестовой БД PostgreSQL. Этот Compose запускает сервер разработки
Django; подготовка production-сервера и HTTPS в текущую задачу не входит.
