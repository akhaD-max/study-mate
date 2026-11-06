# QA-отчёт Sprint Review — каталог Sprint 6

Дата проверки: **06.11.2026**. Ревью: **07.11.2026**. Исполнитель: Arena Agent. Ветка: `arena/999a17b1-study-mate`, базовый коммит `2059ff6`; проверялись новые документы и приёмочные тесты в рабочем дереве. Production-код, зависимости, общие настройки и `README.md` не изменялись.

## Verdict

**DEMO / API / DOCS подготовлены; полная QA-приёмка не закрыта.** Основной поиск, фильтры, HTML/HTMX, сортировка, пагинация, доступ и жизненный цикл заявки проверены фактически. Открыт один подтверждённый дефект: **S6-10 — зависший запрос не получает конечного таймаута**. Шесть кейсов полной версии не выполнялись: соответствующие функции не входят в Sprint 6.

Сводка:

- pytest: **147 passed + 106 subtests passed**; из них новые приёмочные: **15 passed + 56 subtests**.
- Chromium: **19 проверок, 18 passed, 1 failed**; единственное падение — штатный timeout S6-10.
- Основные S6-01–S6-09: **9/9 passed**. S6-10: **failed** по таймауту; HTTP 500 и обрыв сети внутри него passed.
- Регрессия R-01–R-04: **4/4 passed**.
- F-01–F-06: **blocked / not applicable для Sprint 6**, не выдаются за пройденные.
- Ruff, Django check, migration checks, `pip check`, OpenAPI validator: **OK**.

## Фактическое окружение

| Компонент | Что реально использовалось | Ограничение |
| --- | --- | --- |
| ОС | Linux sandbox | Не Windows-прогон команды |
| Python | CPython **3.11.2** | Целевой **3.13.16** не подтверждён: загрузка standalone-сборки была заблокирована сетью |
| Django | 5.2.17 | Совпадает с `requirements.txt` |
| psycopg / Pillow | 3.3.6 / 13.0.0 | Совпадают с `requirements.txt` |
| PostgreSQL | **17.11**, locale **C.UTF-8**, порт 55432 | Запущен из проверенного wheel, не из Docker-образа команды |
| Браузер | Chromium **143.0.7499.0**, playwright-core 1.58.2 | Safari/Firefox не проверялись |
| QA-инструменты | pytest 9.2.0, Ruff 0.17.4, openapi-spec-validator 0.9.0 | Установлены отдельно в `.local/tooling`; манифест не менялся |
| Приложение | `0.0.0.0:8000`, `DEBUG=0`, БД `studymate_review` | Использован локальный Arena preview override, не production-конфигурация |

Важно: успешный прогон на CPython 3.11.2 не объявляется проверкой целевого CPython 3.13.16. Docker-образ `postgres:17.11-bookworm` с указанным digest также отдельно не запускался.

## Выполненные команды и результат

Команды выполнялись из корня репозитория с локальным Python-окружением и переменными БД текущей сессии:

```text
python -m pip check                         -> No broken requirements found
python -m ruff check .                      -> All checks passed
python manage.py check                      -> System check identified no issues
python manage.py makemigrations --check --dry-run -> No changes detected
python manage.py migrate --check            -> exit 0
python -m pytest tests -q --tb=short        -> 147 passed, 106 subtests passed in 82.42s
python -m openapi_spec_validator docs/openapi.yaml -> OK
git diff --check                            -> exit 0
git diff --exit-code -- README.md           -> exit 0
```

Базовый набор до добавления приёмки: **132 passed + 50 subtests**. Новый модуль `tests/projects/test_catalog_review.py`: **15 passed + 56 subtests**. SQLite не использовалась; Django создавал отдельную тестовую PostgreSQL-БД.

## Реальные HTTP-наблюдения

Запросы выполнялись к запущенному приложению, не только через Django test client.

| Запрос | Фактический результат |
| --- | --- |
| `GET /projects/` | 200, полная HTML-страница, счётчик 3: P08/P07/P01 |
| `GET /projects/?q=Python` | 200, счётчик 2: P07/P01 |
| `q=Python&direction=development&role=Backend&open_only=true&sort=newest` | 200, счётчик 1: P01 |
| `q=Python&open_only=false` | 200, счётчик 9 |
| `q=Python`, `HX-Request: true` | 200, тело начинается с `<section id="catalog-content"`, счётчик 2 |
| Те же параметры + `HX-History-Restore-Request: true` | 200, полная HTML-страница |
| `open_only=maybe` | 400 HTML, ошибка поля, успешных карточек нет |
| `q=Python&q=Python` | 400 HTML, повтор параметра запрещён |
| `HEAD /projects/` | 405, `Allow: GET` |

Для ответов обработчика каталога наблюдался `Content-Type: text/html; charset=utf-8` и `Vary: HX-Request, HX-History-Restore-Request, Cookie`. На HEAD 405 middleware дал `Vary: Cookie`; это не объявляется нарушением контракта обработчика.

Методы проверены отдельно: POST без CSRF → 403; POST с form-токеном → 405; PUT/PATCH/DELETE с валидным `X-CSRFToken` → 405; HEAD/OPTIONS → 405 `Allow: GET`. Поэтому OpenAPI не обещает «любой не-GET сразу 405».

## Браузерная приёмка Chromium

Использовался временный Playwright harness в `.local`, не добавленный как зависимость репозитория. Итоговый прогон: `.local/browser-review-verified.log`, JSON: `.local/browser-review-results.json`. Эти файлы локальные и могут не входить в snapshot; ключевые результаты зафиксированы здесь.

| ID | Статус | Фактический результат |
| --- | --- | --- |
| S6-01 | PASSED | `Python` находит P01 по названию и P07 по описанию; счётчик 2 |
| S6-02 | PASSED | Несуществующий запрос: 0 карточек, empty state и сброс, не ошибка сервера |
| S6-03 | PASSED | absent/empty/spaces дают 3; `Py` даёт 2 |
| S6-04 | PASSED | Латиница/кириллица, регистр и strip подтверждены в Chromium + PostgreSQL C.UTF-8 |
| S6-05 | PASSED | Открытый набор: только P01/P07/P08; pending и занятость подтверждены pytest |
| S6-06 | PASSED | AND направления/роли; `Backend`/`backend`; отсутствующая роль → 200/0 |
| S6-07 | PASSED | true → 2, false → 9; в URL ровно одно значение `open_only` |
| S6-08 | PASSED | Reset очищает URL и восстанавливает все defaults |
| S6-09 | PASSED | 400 отображается, ввод сохранён, карточек нет; invalid sort → newest |
| S6-10 HTTP 500 | PASSED | Injected 500: прежние карточки сохранены, ошибка видна, retry успешен |
| S6-10 network | PASSED | Abort сети: прежние карточки сохранены, ошибка видна, retry успешен |
| S6-10 timeout shipped | **FAILED** | `htmx.config.timeout=0`; после задержки loading остаётся, ошибки нет |
| S6-10 timeout injected | PASSED, diagnostic only | Только при test-injected `timeout=200` обработчик и retry работают |
| R-01 | PASSED | Четыре сортировки в браузере; Q01–Q13 и page fallback в pytest |
| R-02 | PASSED | Direct URL/reload/Back/Forward; fragment и history restore |
| R-03 | PASSED | Browser submit → pending → accept → full → leave → free |
| R-04 | PASSED | Guest catalog, login next, чужие заявки скрыты, mutation без CSRF → 403 |
| Keyboard/no-JS/mobile | PASSED | Enter работает; без JS GET-форма и сортировка работают; 390px без horizontal overflow |
| page-errors | PASSED | JS page errors: 0 |

Injected timeout — диагностический эксперимент, **не исправление** и не доказательство готовности S6-10.

## Дефект BUG-S6-10-TIMEOUT

**Название:** зависший запрос каталога не завершается по конечному таймауту.
**Связанный кейс:** S6-10, приоритет высокий. **Статус:** open. **Окружение:** Chromium 143, Django 5.2.17, PostgreSQL 17.11 C.UTF-8, коммит `2059ff6` + рабочее дерево.

**Предусловия:** каталог открыт на `/projects/?q=Python`, видны P01 и P07.

**Шаги воспроизведения:**

1. В DevTools Console выполнить `htmx.config.timeout` → наблюдается `0`.
2. Задержать следующий GET-запрос каталога, например через network route/throttling, минимум на 1,5 секунды.
3. Изменить поиск на `Lab` и отправить форму.
4. Дождаться больше типичного сетевого таймаута UI.

**Ожидалось:** конечный таймаут, сообщение об ошибке, прекращение loading, возможность повторить запрос; прежние карточки не теряются.

**Фактически:** loading продолжается, сообщение ошибки не появляется. Наблюдение harness:

```json
{"timeout":0,"error":false,"loading":true}
```

**Контрольный эксперимент:** если в тестовой странице установить `htmx.config.timeout = 200` и задержать ответ на 1 секунду, появляются ошибка и retry; после восстановления сети повтор возвращает корректные карточки. Значит обработчик `htmx:timeout` есть, но штатная конфигурация не задаёт конечное значение.

**Предлагаемое направление исправления:** задать согласованный конечный timeout для каталога через конфигурацию HTMX и добавить регрессионную браузерную проверку. В этой подготовке приложение не исправлялось, чтобы не смешивать QA-фиксацию с изменением production-кода.

## Окруженческая проблема, не дефект приложения

Первый прогон на PostgreSQL locale `C` дал **130 passed, 5 failed, 47 subtests**: падали кириллические сравнения регистра/constraint. После пересоздания кластера с `C.UTF-8` полный набор стал зелёным. Это зафиксировано как требование к окружению: для кириллического поиска нужна UTF-8 locale, а не `C`. Не переносить это в баг приложения без отдельного воспроизведения на целевом образе.

## Данные и очистка

Live-БД `studymate_review` содержит P01–P10, всего **10 проектов**. Q01–Q13 существуют только в rollback-тестах. Браузерный lifecycle создавал заявку `review-student4@studymate.local` с комментарием `QA lifecycle unique comment 6847`; после финального прогона она и связанное membership удалены. Контроль после очистки: Python Lab — **1 участник, 1 свободное место**.

Пароль демо-аккаунтов хранится только в локальном `.env` и не включён в документы.

## Ограничения и что не проверено

- Целевой CPython 3.13.16 и Docker-образ PostgreSQL с digest не запускались в этом sandbox.
- Safari, Firefox и реальная мобильная ОС не проверялись; mobile — только viewport Chromium 390px.
- Нагрузочное тестирование, security pentest и production deployment не выполнялись.
- F-01–F-06 полной версии не реализованы в Sprint 6 и не считаются дефектами демо.
- Внешний Swagger Try it out не проверялся; приложение не отдаёт JSON и не имеет CORS/Swagger UI.

## Повторение приёмки

1. Поднять отдельную PostgreSQL C.UTF-8 БД по [review-demo.md](review-demo.md).
2. Выполнить команды проверок из этого отчёта.
3. Прогнать `tests/projects/test_catalog_review.py` и полный `tests`.
4. Повторить браузерные шаги S6/R; для таймаута использовать задержку ответа и проверить штатное значение `htmx.config.timeout`.
5. После исправления дефекта обновить статус S6-10 и этот отчёт; до этого не объявлять полную приёмку закрытой.
