# StudyMate

Платформа для студентов: поиск учебных проектов, подбор команды,
отклики на роли и профиль с компетенциями.

Основа проекта — Django и PostgreSQL. Подготовлены каркас проекта
и конфигурация Docker Compose.

## Клонирование

Откройте Powershell / терминал в папке, куда хотите скачать проект, и введите:

```powershell
git clone https://github.com/akhaD-max/study-mate.git
cd 'название папки'
```

## Первый запуск через Docker

Перед запуском откройте Docker Desktop в режиме Linux containers.

Далее соберите окружение проекта:

```powershell
docker compose build
```

Docker автоматически скачает Python 3.13.16, PostgreSQL 17.11
и установит точные версии библиотек из requirements.txt.

Создайте локальный файл настроек .env со случайными секретами:

```powershell
docker compose run --rm --no-deps --user 0 --volume "${PWD}:/workspace" --workdir /workspace web python scripts/setup_env.py
```

Запустите контейнеры:

```powershell
docker compose up -d --wait
```

Откройте http://localhost:8000/.

Если порт занят, измените WEB_PORT в файле .env, например
на 8001, и повторите команду запуска. Тогда адрес будет
http://localhost:8001/.
