# Sprint Review 07.11.2026 — DEMO / API / QA / DOCS

Короткий сценарий для показа каталога Sprint 6. Проверяемый код: `2059ff6` + новые документы и приёмочные тесты в рабочем дереве; production-код не менялся.

**Что показываем:** поиск и фильтры каталога, реальный HTML/HTMX-запрос, результаты QA и один подтверждённый дефект таймаута, OpenAPI и предложение README.
**Что не показываем как готовое:** JSON API, Swagger UI в приложении, множественные фильтры, сложность, навыки, автопоиск от трёх символов.

Связанные файлы:

- [OpenAPI 3.1 — HTML/HTMX каталог](../openapi.yaml)
- [Предложение техлиду по README](readme-proposal.md)
- [QA-отчёт с фактическими результатами](qa-report.md)
- [Исходные тест-кейсы P01–P10 / Q01–Q13](catalog-test-cases.md)
- [Приёмочные pytest-тесты](../../tests/projects/test_catalog_review.py)
- [Данные для изолированной приёмки](../../tests/projects/review_data.py)

## 1. Быстрый старт демо

В текущей сессии приложение уже запущено в LIVE PREVIEW на порту `8000`, БД `studymate_review` наполнена P01–P10. Откройте `/projects/`.

Ожидаемая стартовая выдача при `open_only=true`:

| Порядок по умолчанию | Проект | Почему показан |
| --- | --- | --- |
| 1 | Робот помощник | open, открытая роль, есть место |
| 2 | User Research | open, открытая роль, есть место |
| 3 | Python Lab | open, Backend: 1 из 2 мест занято; pending не занимает место |

Счётчик: **3**. Если счётчик другой, проверьте, что открыта изолированная БД `studymate_review`, а не обычная `studymate` с `seed_demo`.

### Воспроизводимый запуск в отдельной БД

Ниже — PowerShell-команды для локальной машины команды. Они не выполнялись в текущем sandbox вместо Docker; фактический sandbox-прогон описан в QA-отчёте. Не запускайте наполнение в рабочей БД с пользовательскими данными.

```powershell
docker compose up -d --wait db

# Создать пустую БД с UTF-8 locale. Если БД уже существует, пропустить CREATE.
docker compose exec -T db psql -U studymate -d postgres -c "CREATE DATABASE studymate_review ENCODING 'UTF8' LC_COLLATE 'C.UTF-8' LC_CTYPE 'C.UTF-8' TEMPLATE template0;"

docker compose run --rm -e POSTGRES_DB=studymate_review web python manage.py migrate --noinput

# Локальный пароль только для демо-аккаунтов; не коммитить.
$env:REVIEW_PASSWORD = '<придумайте локальный пароль>'
docker compose run --rm -e POSTGRES_DB=studymate_review -e REVIEW_PASSWORD web python manage.py shell -c "import os; from tests.projects.review_data import seed_empty_review_catalog; seed_empty_review_catalog(password=os.environ['REVIEW_PASSWORD'])"

# Запуск web поверх отдельной БД; команда держит процесс в foreground.
docker compose run --rm --service-ports -e POSTGRES_DB=studymate_review web
```

Откройте `http://localhost:8000/projects/`. Helper откажется работать, если в БД уже есть пользователи, проекты или направления. Q01–Q13 создаются только в другой пустой БД функцией `seed_empty_pagination_catalog`; в текущем демо они не смешаны с P01–P10.

Для обычных pytest-тестов отдельная тестовая БД создаётся Django автоматически; вручную наполнять её не нужно.

## 2. DEMO — 5 минут

### 0:00–0:40. Поиск по названию и описанию

1. Открыть `/projects/`: три карточки, счётчик 3.
2. Ввести `Python`, нажать «Найти».
3. Показать **User Research** и **Python Lab**, счётчик 2.
4. Пояснить: User Research найден по описанию, хотя в названии нет Python.

### 0:40–1:40. Совместные фильтры

1. С поиском `Python` выбрать направление «Разработка» → только Python Lab.
2. Выбрать роль `Backend` → тот же один результат.
3. Сменить направление на «Дизайн» с ролью Backend → пустая выдача, HTTP 200, понятное сообщение и сброс.
4. Вернуть «Разработка» или сбросить фильтры.

Ключевая фраза: условия между группами работают через **AND**, текст ищется в названии **или** описании.

### 1:40–2:20. Открытый набор и сброс

1. Поиск `Python`, включён «Только с открытым набором» → 2 результата.
2. Выключить фильтр → 9 результатов: закрытые/завершённые проекты и занятые роли попадают в выдачу.
3. Нажать «Сбросить фильтры» → URL `/projects/`, поиск пуст, все направления, любая роль, набор включён, сортировка «Сначала новые», счётчик 3.

### 2:20–3:00. Сортировка, URL и история

1. Переключить «Сначала старые»: Python Lab, User Research, Робот помощник.
2. Переключить «Больше участников»: Python Lab первым.
3. Обновить страницу и выполнить Back/Forward: форма, карточки и счётчик соответствуют URL.

### 3:00–3:40. Ошибки ввода и сети

1. Открыть `/projects/?open_only=maybe` → HTTP 400, сообщение о true/false, карточек нет.
2. Вернуться к `q=Python`.
3. В DevTools включить Offline, изменить поиск на `Lab` → прежние две карточки остаются, появляется сообщение и повтор.
4. Выключить Offline, нажать повтор → остаётся Python Lab.
5. **Не объявлять таймаут готовым:** штатный `htmx.config.timeout=0`. Это подтверждённый дефект S6-10, подробности в QA-отчёте.

### 3:40–4:20. Регрессия заявки, если есть время

Аккаунты создаются helper-ом с паролем из `REVIEW_PASSWORD`:

- кандидат: `review-student4@studymate.local`;
- руководитель: `review-author@studymate.local`.

Сценарий: кандидат подаёт заявку на Backend в Python Lab → pending не занимает место → руководитель принимает → роль заполнена, Python Lab исчезает из открытого набора → кандидат выходит из проекта → место освобождается, карточка возвращается.

После демо удалить только созданную QA-заявку и связанное членство, либо пересоздать изолированную БД. Не использовать `down -v` для рабочей БД.

### 4:20–5:00. API и документы

Выполнить один curl-запрос из раздела 3, открыть `docs/openapi.yaml`, показать предложение README и QA-отчёт. Завершить честной формулировкой:

> Основной поиск, фильтры, HTML/HTMX, сортировка, пагинация и жизненный цикл заявки проверены. Полный набор автотестов зелёный. Один дефект приёмки открыт: зависший запрос не получает конечного таймаута. Целевой CPython 3.13.16 и Docker-образ в этом sandbox отдельно не подтверждены.

## 3. API — реальные запросы к существующему приложению

Это **HTML/HTMX**, не JSON. Авторизация и CSRF для GET не нужны.

### PowerShell

```powershell
curl.exe -i --get 'http://localhost:8000/projects/' `
  --data-urlencode 'q=Python' `
  --data-urlencode 'direction=development' `
  --data-urlencode 'role=Backend' `
  --data-urlencode 'open_only=true' `
  --data-urlencode 'sort=newest'
```

Ожидается: `200 OK`, `Content-Type: text/html; charset=utf-8`, `Vary` содержит `HX-Request`, `HX-History-Restore-Request`, `Cookie`; в HTML одна карточка **Python Lab**, счётчик 1.

### Bash

```bash
curl -i --get 'http://localhost:8000/projects/' \
  --data-urlencode 'q=Python' \
  --data-urlencode 'direction=development' \
  --data-urlencode 'role=Backend' \
  --data-urlencode 'open_only=true' \
  --data-urlencode 'sort=newest'
```

### HTMX-фрагмент

```powershell
curl.exe -i 'http://localhost:8000/projects/?q=Python' -H 'HX-Request: true'
```

Ожидается: `200 OK`, тело начинается с `<section id="catalog-content"`, счётчик 2. Это фрагмент для `outerHTML`, не JSON и не полная страница.

### Восстановление истории

```powershell
curl.exe -i 'http://localhost:8000/projects/?q=Python' `
  -H 'HX-Request: true' `
  -H 'HX-History-Restore-Request: true'
```

Ожидается полная HTML-страница, несмотря на `HX-Request: true`.

### Ошибка параметра

```powershell
curl.exe -i 'http://localhost:8000/projects/?open_only=maybe'
```

Ожидается `400 Bad Request`, HTML с ошибкой `open_only`, без успешных карточек.

### Методы

```powershell
curl.exe -I 'http://localhost:8000/projects/'
```

Ожидается `405 Method Not Allowed`, `Allow: GET`. POST без CSRF даёт 403 раньше проверки метода; с валидным CSRF — 405. Это отражено в OpenAPI, чтобы не обещать неверное поведение.

## 4. DOCS — что передать техлиду

1. `docs/openapi.yaml` — фактический контракт `GET /projects/`: query, HTMX-заголовки, 200/400/403/405/500, HTML-схемы и примеры.
2. `docs/sprint-6/readme-proposal.md` — готовые блоки замены устаревшего README. Корневой README не изменён.
3. `docs/sprint-6/qa-report.md` — окружение, команды, результаты, дефект и ограничения.
4. `tests/projects/test_catalog_review.py` и `tests/projects/review_data.py` — воспроизводимая HTTP-приёмка и изолированные данные.

OpenAPI можно импортировать во внешний редактор для чтения. Кнопка Try it out не является частью приложения и может не работать из-за Mixed Content/CORS; для демо используйте curl или браузер.

## 5. Команды проверки

Выполнять в окружении, где доступны инструменты. Ruff, pytest и openapi-spec-validator не добавлялись в `requirements.txt`.

```powershell
python -m pip check
python -m ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
python -m pytest tests -q
python -m openapi_spec_validator docs/openapi.yaml
git diff --check
git diff --exit-code -- README.md
```

Фактические результаты текущей сессии: **147 passed + 106 subtests**, Ruff/Django/migration checks OK, OpenAPI validator OK. Это не отменяет открытый дефект таймаута и ограничение по целевому CPython.
