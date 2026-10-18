# Отчёт о подготовке StudyMate — 19.10.2026

Репозиторий клонирован прямо в `C:\Users\luvpl\OneDrive\Desktop\PythonDjango`.
`origin` указывает на `https://github.com/akhaD-max/study-mate.git`.
Работа выполнена в ветке `feature/django-docker-bootstrap` для PR в `main`.
Описание изменений и проверок — в `pr-description.md`.

## Версии

| Компонент | Было на ПК | Подготовлено для проекта |
| --- | --- | --- |
| Git | 2.51.0.windows.1 | Использован установленный |
| Python | 3.11.9 x64 по команде `python` | 3.13.16 x64 в `.python/tools`, отдельная `.venv` |
| Docker | 29.8.2 | Docker Desktop запущен, Linux containers |
| Docker Compose | v5.6.0 | Использован установленный |
| Django | В новом окружении отсутствовал | 5.2.17 локально и в контейнере |
| psycopg / psycopg-binary | В новом окружении отсутствовали | 3.3.6 |
| Pillow | В новом окружении отсутствовал | 13.0.0 |
| asgiref / sqlparse | В новом окружении отсутствовали | 3.12.1 / 0.6.0 |
| tzdata | В новом окружении отсутствовал | 2026.5 на Windows; в Linux пропускается по условию manifest |
| PostgreSQL | Локальная установка не обнаружена | 17.11 в Docker |
| HTMX | В проекте отсутствовал | 2.0.11, локальный файл с проверенной SHA-256 |

Python 3.11.9 не соответствует принятой версии проекта. Он сохранён;
для этой задачи использована `.venv` на CPython 3.13.16.

## Основные выполненные команды

```powershell
git clone https://github.com/akhaD-max/study-mate.git .
git switch -c feature/django-docker-bootstrap
git --version
python --version
docker --version
docker compose version
docker desktop start
```

Прочитаны AGENTS.md, requirements.txt и README.md целиком. AGENTS.md и
requirements.txt не изменены. В README сохранены исходные разделы, кроме
четырёх указанных владельцем; после стека добавлен утверждённый гайд запуска.
Установщик с python.org был скачан с проверкой SHA-256 и подписи,
но завершился ошибкой Windows Installer `0x80070003`. Рабочий вариант —
официальный переносимый пакет CPython из NuGet:

```powershell
Invoke-WebRequest https://api.nuget.org/v3-flatcontainer/python/3.13.16/python.3.13.16.nupkg -OutFile .local/python.3.13.16.zip
Expand-Archive .local/python.3.13.16.zip -DestinationPath .python
.\.python\tools\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m django startproject config .
.\.venv\Scripts\python.exe scripts/setup_env.py
```

Файлы каркаса дополнены настройками PostgreSQL, переменных окружения, шаблонов,
статических файлов и корневой страницы. Добавлены Dockerfile, Compose,
игнорирование локальных файлов и инструкции запуска. Дополнительных Django
приложений не создавалось, сторонних runtime-зависимостей не добавлено.

## Как собран Docker

```powershell
docker pull python:3.13.16-slim-bookworm
docker pull postgres:17.11-bookworm
docker buildx imagetools inspect postgres:17.11-bookworm
docker compose config --quiet
docker compose --progress plain build web
docker compose --progress plain build db
docker compose --progress plain build
docker compose up -d --wait --wait-timeout 90
docker compose ps
```

Оба базовых образа закреплены по версии и digest в Dockerfile. Слой web
выполняет `python -m pip install --no-cache-dir -r requirements.txt` и
`pip check`. Локальные `.env`, `.venv`, `.python`, `.local` в образ не попадают.
Процесс Django работает без root, web ждёт healthy PostgreSQL. База хранится
в volume `pythondjango_postgres_data`. Миграции при запуске не выполняются.

Первый запуск обнаружил занятый порт 8000. В локальном `.env` выбран
`WEB_PORT=8001`, общий пример для команды оставлен с портом 8000.

## Результаты проверки

- `pip check` локально и в контейнере: конфликтов нет.
- `manage.py check` локально и в контейнере: замечаний нет.
- Ruff 0.17.1 из отдельной `.local/lint`: `All checks passed!`.
- `makemigrations --check --dry-run`: новых миграций нет.
- PostgreSQL отвечает: `17.11 (Debian 17.11-1.pgdg12+2)`.
- В отдельной БД `studymate_bootstrap_verify` успешно применены 18 стандартных
  миграций Django, `migrate --check` завершился успешно. Рабочая `studymate`
  оставлена без таблиц до согласования кастомного пользователя.
- Страница `http://127.0.0.1:8001/` и локальный HTMX возвращают HTTP 200.
- Проверены шаблон, обработка boolean-переменных, обязательность секретов,
  отсутствие локальных секретов в образе и запуск web без root.
- Оба контейнера имеют состояние healthy.
- Pytest не запускался: тестов и бизнес-приложений пока нет. Командные версии
  Ruff/pytest и включение их в dev-образ остаются за техлидом по AGENTS.md.

Сборка успешно проверена на Windows x64 / Docker Linux amd64.
Проверка на других архитектурах не выполнялась.

Подробная инструкция для коллег: `docs/local-development.md`. Изменения
подготовлены к ревью и ручному слиянию владельцем задачи через PR.

Источники пакетов и образов: [Python 3.13.16](https://www.python.org/downloads/release/python-31316/),
[официальные NuGet-пакеты CPython](https://docs.python.org/3.13/using/windows.html#the-nuget-org-packages),
[Django 5.2.17](https://pypi.org/project/Django/5.2.17/),
[Pillow 13.0.0](https://pypi.org/project/pillow/13.0.0/),
[PostgreSQL 17.11](https://www.postgresql.org/docs/release/17.11/).
