# Модель данных — Data Dictionary → Django ORM

Короткое соответствие для первого дня спринта. Владелец схемы и миграций — Денис. Остальные передают изменения ему.

## Принцип переноса

Не переносим механически. Заменяем своим Django-механизмом: `sessions`, `password_reset_tokens`, `password_hash` → `django.contrib.auth` + `sessions`. OAuth откладываем. Остальное переносим только под сценарий спринта (п. 8 README).

## Где живут модели

- `accounts.User` — кастомный пользователь (UUID, email-вход)
- `projects.Project`, `projects.ProjectRole`, `projects.Membership` — карточка, роли, членство
- `applications.Application` — отклики

Приложения `projects` и `applications` появятся в `002` вместе с миграциями. Договор фиксируем сейчас, чтобы не было двух `0001_initial`.

## 1. Пользователь

**Было в Data Dictionary:** `users(id uuid, email unique, full_name not null, password_hash, oauth_provider, ...)`, `sessions`, `password_reset_tokens`.

**Стало в Django:**

```python
# accounts/models.py
class User(AbstractBaseUser, PermissionsMixin):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = EmailField(unique=True, db_index=True)  # храним в lower, проверка на уровне БД: UniqueConstraint(Lower("email"))
    full_name = CharField(max_length=150, blank=True, default="")  # закрывает NOT NULL + пустую регистрацию
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)
    date_joined = DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()  # normalize_email + lower
```

Разделение ролей: системная роль — `is_staff`/`is_superuser`. Роль в проекте — через `ProjectRole`/`Membership`. Пароль хранит Django (`set_password`, PBKDF2). Сессии — `django_session`.

## 2. Проект

**Было:** `projects(id uuid, author_id, title varchar(255), description text, status, category, deadline, ...)`.

**Стало:**

```python
class Project(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = FK(User, on_delete=CASCADE, related_name="authored_projects")
    title = CharField(max_length=100)  # 3..100, валидируем в форме
    description = TextField(max_length=5000, blank=True)
    status = CharField(choices=[("open","Открыт"),("in_progress","В работе"),("completed","Завершён"),("cancelled","Отменён")], default="open")
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["author","title"], name="uniq_author_title")]
        indexes = [Index(fields=["status","created_at"])]
```

`category`, `deadline` из Data Dictionary пока не переносим — в backlog. `title` сужаем до 100 по макету.

## 3. Роль в проекте

**Было:** `project_roles(id, project_id, name, count/max_members int)`, набор смешивался со статусом проекта.

**Стало:**

```python
class ProjectRole(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = FK(Project, on_delete=CASCADE, related_name="roles")
    name = CharField(max_length=100)  # напр. "Backend", "Дизайн"
    description = TextField(blank=True)
    capacity = PositiveSmallIntegerField()  # 1..20, единое имя вместимости
    is_open = BooleanField(default=True)  # явный признак открытого набора (требование спринта)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["project","name"], name="uniq_role_per_project")]
```

Занятость считаем по `Membership`, а не по `count` из старой БД. `is_open` отделяет закрытие набора от `Project.status`.

## 4. Членство (занятость мест)

**Было:** `memberships(project_id, user_id, role_text)`, роль — текстом, без FK.

**Стало:**

```python
class Membership(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = FK(Project, on_delete=CASCADE, related_name="memberships")
    role = FK(ProjectRole, on_delete=PROTECT, related_name="memberships")  # PROTECT — не дать удалить занятую роль
    user = FK(User, on_delete=CASCADE, related_name="memberships")
    joined_at = DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["project","user"], name="uniq_member_per_project")]
        indexes = [Index(fields=["role","user"])]
```

Источник занятости: `occupied = Membership.objects.filter(role=role).count()`. `pending` не считаем (см. ниже).

## 5. Заявка (отклик)

**Было:** `applications(id, user_id, project_id, comment, status, ...)`, без `role_id`.

**Стало:**

```python
class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На рассмотрении"
        ACCEPTED = "accepted", "Принята"      # зарезервировано
        REJECTED = "rejected", "Отклонена"    # зарезервировано
        WITHDRAWN = "withdrawn", "Отозвана"    # зарезервировано

    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant = FK(User, on_delete=CASCADE, related_name="applications")
    project = FK(Project, on_delete=CASCADE, related_name="applications")
    role = FK(ProjectRole, on_delete=CASCADE, related_name="applications")
    comment = CharField(max_length=300, blank=True, default="")
    status = CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # один активный отклик на проект независимо от роли
            UniqueConstraint(fields=["project","applicant"], condition=Q(status="pending"), name="uniq_pending_per_project"),
        ]
        indexes = [Index(fields=["applicant","status"]), Index(fields=["role","status"])]
```

Правила из контракта: автор и действующий участник (`Membership`) не могут создавать `pending`; `role.project == project`; `role.is_open` и `occupied < capacity` проверяем в сервисе в транзакции с `select_for_update` на `ProjectRole`.

История: при удалении проекта заявки не каскадим в никуда — оставляем через `on_delete=CASCADE` с предупреждением, soft-delete проекта в backlog.

## Что заменили и что отложили

| Data Dictionary | Решение |
|---|---|
| `users.password_hash`, `sessions`, `password_reset_tokens`, `oauth_*` | Заменено `django.contrib.auth`/`sessions`, сброс через `PasswordResetTokenGenerator`. OAuth — backlog |
| `users.full_name NOT NULL` | `blank=True, default=""` — регистрация только email+пароль |
| `projects.category`, `deadline`, `complexity`, `stages` | Backlog, не нужны для сценария |
| `project_roles.count` | `capacity` + `is_open` + подсчёт по `Membership` |
| `applications` без `role_id` | Добавили `role FK` с проверкой принадлежности |
| `invitations`, `attachments`, `comments`, `notifications`, `views`, `skills` | Backlog, единый справочник навыков — позже |

## Миграции

Порядок делает Денис: `accounts 0001` (кастомный User) → `projects 0001` → `applications 0001`. Проверяем на пустой БД (`migrate`) и на `migrate --check` в CI. `DEFAULT_AUTO_FIELD` остаётся `BigAutoField`, но наши PK — UUID явно.

## Как считать свободные места

```python
occupied = Membership.objects.filter(role=role).count()
free = role.capacity - occupied
is_available = role.is_open and free > 0 and project.status == "open"
```

`pending` в `free` не участвует — так закрепили на спринт.
