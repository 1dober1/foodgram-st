# Foodgram

Веб-приложение для публикации рецептов. Пользователи могут создавать рецепты, добавлять их в избранное, подписываться на авторов и формировать список покупок.

## Технологии

- Backend: Python 3.9, Django 3.2, Django REST Framework, PostgreSQL
- Frontend: React
- Инфраструктура: Docker, Nginx

## Требования

- Docker
- Docker Compose

## Запуск проекта

### 1. Клонирование репозитория

```bash
git clone <URL репозитория>
cd foodgram-st
```

### 2. Настройка переменных окружения

Перейдите в папку `infra` и создайте файл `.env` на основе примера:

```bash
cd infra
cp env.example .env
```

Отредактируйте файл `.env` при необходимости:

```
POSTGRES_USER=foodgram
POSTGRES_PASSWORD=foodgram
POSTGRES_DB=foodgram
DB_HOST=db
DB_PORT=5432
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

### 3. Запуск контейнеров

Находясь в папке `infra`, выполните команду:

```bash
docker-compose up -d
```

### 4. Выполнение миграций и сбор статики

После запуска контейнеров выполните:

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py collectstatic --noinput
```

### 5. Загрузка ингредиентов

```bash
docker-compose exec backend python manage.py load_ingredients
```

### 6. Создание суперпользователя

```bash
docker-compose exec backend python manage.py createsuperuser
```

## Доступ к приложению

- Веб-приложение: http://localhost
- Документация API: http://localhost/api/docs/
- Панель администратора: http://localhost/admin/

## Остановка проекта

```bash
cd infra
docker-compose down
```

Для удаления данных (volumes):

```bash
docker-compose down -v
```
