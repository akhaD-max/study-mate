# Контракты StudyMate

Требуемые эндпоинты для US-01–US-12. GET возвращает HTML с указанными данными, POST принимает поля формы; вложенные списки передаются Django formset. `*` — данных пока нет в схеме БД.

Все идентификаторы — UUID. Пользователь берётся из сессии; для POST нужен CSRF. Ошибка формы возвращает форму с введёнными данными и сообщением. Пароли в ответах не возвращаются.

## US-01. Регистрация и авторизация

**Эндпоинты:**

- `GET /accounts/register/` — форма регистрации.
- `POST /accounts/register/` — принимает `email: string`, `password: string` (минимум 6 символов); создаёт пользователя, выполняет вход, перенаправляет на `/profile/edit/`.
- `GET /accounts/login/` — форма входа.
- `POST /accounts/login/` — принимает `username: string` (email), `password: string`; перенаправляет на `/projects/`.
- `POST /accounts/logout/` — без полей; завершает сессию, перенаправляет на `/projects/`.

Email уникален без учёта регистра. При неверных реквизитах — «Неверный логин или пароль».

## US-02. Заполнение профиля

**Эндпоинты:**

- `GET /profile/edit/` — возвращает текущие данные профиля для редактирования.
- `POST /profile/edit/` — принимает поля ниже; формат `multipart/form-data`; после сохранения перенаправляет на `/profile/<user_id>/`.
- `GET /profile/<user_id>/` — возвращает публичные данные профиля.

**Поля формы:**

- `full_name: string` — до 150 символов.
- `avatar*: image` — необязательно.
- `university*: string`, `specialty*: string` — обязательно.
- `course*: integer` — 1–6, обязательно.
- `bio*: string` — до 1000 символов.
- `desired_role*: string` — необязательно.
- `skills*: uuid[]` — от 1 до 15 уникальных навыков.
- `interest_tags*: string[]` — без дублей.

**Данные просмотра:** `id`, `full_name`, `avatar_url*`, `university*`, `specialty*`, `course*`, `bio*`, `desired_role*`, `skills*: [{id, name, category}]`, `interest_tags*: [string]`.

## US-03. Проекты студента в профиле

**Эндпоинт:** `GET /profile/<user_id>/projects/`.

**Query:** `tab: active|completed` (по умолчанию `active`), `role: all|leader|member` (по умолчанию `all`).

**Данные карточки:**

- `id`, `title`, `status`.
- `category: {id, name}`, `short_description: string` — до 100 символов.
- `role_in_project: string` — «Руководитель» по `Project.author_id`, иначе `ProjectMember.role.name`.
- `teammates: [{id, full_name, avatar_url*}]` — до 5 человек; `remaining_count: integer`.

Ссылка карточки — `/projects/<project_id>/`. Собственные pending-заявки показываются отдельно от участия; внешнему посетителю доступны только `in_progress` и `completed`.

## US-04. Поиск и фильтрация проектов

**Эндпоинт:** `GET /projects/` — страница каталога; с `HX-Request: true` — HTML списка для `#catalog-content`.

**Query:**

- `q: string` — поиск по названию и описанию от 3 символов, без учёта регистра.
- `categories: uuid[]`, `roles: string[]` — множественные фильтры.
- `difficulty*: string[]` — Начальный / Средний / Продвинутый.
- `open_only: boolean` — по умолчанию `true`.
- `page: integer` — по 12 проектов.

Между группами фильтров — AND, внутри группы — OR.

**Данные:** `projects: [{id, title, description, status, category: {id, name}, difficulty*, author: {id, full_name, avatar_url*}, roles: [{id, name, capacity, occupied_places, free_places, is_open}]}]`, `page`, `total_pages`, `total_count`.

## US-05. Подача заявки

**Эндпоинты:**

- `GET /projects/<project_id>/` — возвращает `id`, `title`, `description`, `status`, `category`, `author`, `roles: [{id, name, capacity, occupied_places, free_places, is_open}]`, `can_apply: boolean`.
- `GET /projects/<project_id>/apply/` — форма выбора доступной роли.
- `POST /projects/<project_id>/apply/` — принимает `projectRoleId: uuid` и `comment: string` (необязательно, до 300 символов).

**Результат:** создаётся заявка с `id`, `project_id`, `role_id`, `user_id`, `comment`, `status=pending`, `created_at`. Обычный POST перенаправляет на `/applications/`; HTMX возвращает состояние «Заявка отправлена».

Автор, участник и пользователь с pending-заявкой на проект не могут подать повторный отклик. Роль должна принадлежать проекту, иметь свободные места и открытый набор; проект — `open`. Pending не занимает место.

## US-06. Мои заявки

**Эндпоинты:**

- `GET /applications/` — только собственные заявки, новые сверху.
- `POST /applications/<application_id>/withdraw/` — без полей; удаляет собственную pending-заявку, перенаправляет на `/applications/`.

**Query списка:** `status: all|pending|accepted|rejected`, `q: string` — поиск по названию проекта.

**Данные строки:** `id`, `project: {id, title}`, `role: {id, name}`, `comment`, `created_at` (ДД.ММ.ГГГГ), `status`, `reject_reason*`, `can_withdraw: boolean`.

Статусы: `pending` — «На рассмотрении», `accepted` — «Принята», `rejected` — «Отклонена». Отзыв не меняет занятость: pending место не занимал. Сохранение строки «Проект удалён» требует изменения схемы.

## US-07. Публикация проекта

**Эндпоинты:**

- `GET /projects/create/` — форма, `categories: [{id, name}]`, `skills*: [{id, name}]`.
- `POST /projects/create/` — принимает поля ниже; после сохранения перенаправляет на `/projects/<project_id>/`.

**Поля формы:**

- `title: string` — обязательно, 3–100 символов.
- `description: string` — обязательно, до 5000 символов.
- `category_id: uuid` — обязательно.
- `roles: [{name: string, capacity: integer}]` — минимум одна роль; мест 1–20.
- `difficulty*: string` — необязательно.
- `deadline*: date` — необязательно, не в прошлом.
- `skills*: uuid[]` — обязательные теги компетенций.

Автор назначается из сессии, `status=open`. Автор — руководитель; отдельная запись участника для него не обязательна. Название уникально у автора.

## US-08. Вопросы руководителю

**Эндпоинты:**

- `GET /projects/<project_id>/questions/` — публичный список вопросов и ответов.
- `POST /projects/<project_id>/questions/` — принимает `content*: string`, 15–500 символов.
- `POST /questions/<question_id>/delete/` — без полей; удаляет собственный вопрос без ответа.

**Данные вопроса*:** `id`, `author: {id, full_name, avatar_url}`, `content`, `created_at`, `answer: {id, content, author, created_at, updated_at}|null`, `can_delete: boolean`.

Вопрос задаёт вошедший студент в чужом проекте, максимум 5 вопросов на студента в проекте. После отправки возвращается обновлённый HTML списка. После удаления аккаунта вопрос сохраняется с подписью «Удалённый пользователь».

## US-09. Редактирование проекта

**Эндпоинты:**

- `GET /projects/<project_id>/edit/` — возвращает поля проекта и ролей для редактирования.
- `POST /projects/<project_id>/edit/` — принимает поля US-07, `roles: [{id?, name, capacity, is_open, DELETE?}]`, `stages*: string[]`, `status: open|in_progress`, `updated_at: datetime` для проверки версии.
- `POST /projects/<project_id>/delete/` — без полей; удаление после подтверждения, переход на `/projects/`.

Редактирование и удаление — только автору. Успешное редактирование перенаправляет на `/projects/<project_id>/`.

Нельзя уменьшать места ниже занятости, удалять занятую роль или завершённый проект. Удаление роли удаляет все её заявки после подтверждения. Остальные изменения, включая закрытие набора, сохраняют заявки и их статусы. Несовпадение `updated_at` — ошибка «Карточка была обновлена. Обновите страницу».

## US-10. Входящие заявки и компетенции

**Эндпоинт:** `GET /projects/<project_id>/applications/` — только автору проекта.

**Query:** `sort: match|date_new|date_old`, `role: all|uuid`, `status: all|pending|accepted|rejected`.

**Данные кандидата:**

- `application_id`, `role: {id, name}`, `comment`, `created_at`, `status`, `can_review: boolean`.
- `student: {id, full_name, avatar_url*, university*, specialty*, course*}`.
- `skills*: [{id, name, matched}]`, `missing_skills*: [{id, name}]`, `match_percent*: number`.

Соответствие = совпавшие навыки / требуемые навыки × 100%; пересчитывается при изменении навыков. Письмо длиннее 150 символов сворачивается. Профиль кандидата — `/profile/<user_id>/`.

## US-11. Ответы на вопросы

**Эндпоинты:**

- `GET /projects/<project_id>/questions/manage/` — вопросы руководителю; query `status: all|unanswered|answered`.
- `POST /questions/<question_id>/answer/` — принимает `content*: string`, 3–1000 символов.
- `POST /answers/<answer_id>/edit/` — принимает `content*: string`, 3–1000 символов.
- `POST /answers/<answer_id>/delete/` — без полей; удаляет ответ.

**Данные*:** `questions: [{id, author, content, created_at, answer, status}]`, `unread_count: integer`. Формат `answer` — как в US-08; дополнительно `is_edited: boolean`.

Действия доступны только руководителю. POST возвращает обновлённый HTML вопроса; после удаления ответа статус — «Без ответа». Вопросы и ответы видны публично.

## US-12. Управление командой и набором

**Эндпоинты:**

- `POST /applications/<application_id>/accept/` — без полей; `pending → accepted`, создаёт `ProjectMember` с `project_id`, `role_id`, `user_id` заявки.
- `POST /applications/<application_id>/reject/` — без полей; `pending → rejected`.
- `POST /projects/<project_id>/toggle-enrollment/` — принимает `status: open|in_progress`.
- `POST /projects/<project_id>/roles/<role_id>/toggle-enrollment/` — принимает `is_open: boolean`.
- `POST /projects/<project_id>/members/<user_id>/remove/` — без полей; удаляет членство, освобождает место.

**Результат:** обновлённый HTML заявки/команды с `status`, `members: [{user_id, full_name, role_id, role_name}]`, `roles: [{id, capacity, occupied_places, free_places, is_open}]`.

Действия — только автору. Принятие и создание членства выполняются атомарно с повторной проверкой свободных мест. Закрытие набора блокирует новые отклики и сохраняет статусы прежних заявок. Повторное открытие — `in_progress → open`.

## Чего не хватает в схеме БД

- **US-02, US-03, US-10:** аватар, вуз, специальность, курс, описание профиля, желаемая роль, навыки и теги интересов; справочник навыков и связи с пользователем.
- **US-04, US-07, US-09, US-10:** сложность, дедлайн, этапы проекта и связь требуемых навыков с проектом/ролью. `match_percent` вычисляется, но исходных данных для него нет.
- **US-06, US-10:** причина отказа и сохранение заявок после удаления проекта/пользователя. Сейчас `CASCADE` уничтожает записи; нельзя показать «Проект удалён» или карточку удалённого кандидата.
- **US-08, US-11:** модели вопросов и ответов, даты редактирования, данные о прочтении; сохранение текста после удаления автора.
- **US-05, US-06, US-08–US-12:** постоянные уведомления, получатель, признак прочтения и данные для суточной сводки. При удалении роли уведомляются её заявители; при остальных изменениях — участники и все заявители, без изменения статусов заявок.
- **Целостность заявок:** у `Application` нет ограничения БД, проверяющего принадлежность роли указанному проекту, в отличие от `ProjectMember`.
- **Ограничения:** БД не гарантирует максимум 20 мест, отсутствие переполнения роли, минимум 3 символа в названии, обязательное описание, наличие хотя бы одной роли и запрет удаления завершённого проекта. Эти правила требуют серверных проверок; локальные ограничения полей можно закрепить в БД.

Статуса `withdrawn` нет: отзыв pending можно реализовать удалением заявки. Отдельного общего флага набора нет: текущая схема использует `open/in_progress`, а для конкретной роли — `is_open`.
