# Auth Service

Отдельный микросервис аутентификации, выделенный из монолита `shop_with_admin`.
Реализует один сценарий: **регистрация по email с подтверждением 6-значным кодом**, логин, refresh-токены, JWT.

## Стек
FastAPI + SQLAlchemy + SQLite (как в исходном проекте), JWT (python-jose), bcrypt (passlib).

## Запуск

```bash
cd auth_service
cp .env.example .env   # заполнить SECRET_KEY и SMTP_*
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Swagger UI: http://localhost:8001/docs

Если `SMTP_USER`/`SMTP_PASSWORD` не заданы — письма не отправляются, а код просто
печатается в консоль сервиса (удобно для локальной разработки/тестов).

## Docker

```bash
docker build -t auth-service .
docker run -p 8001:8001 --env-file .env auth-service
```

## Эндпойнты

| Метод | Путь | Описание | Авторизация |
|---|---|---|---|
| POST | `/auth/register` | шаг 1: email+пароль → отправка кода | нет |
| POST | `/auth/register/confirm` | шаг 2: email+код → активация + токены | нет |
| POST | `/auth/register/resend` | повторная отправка кода | нет |
| POST | `/auth/login` | вход по email+паролю → токены | нет |
| POST | `/auth/refresh` | обновление токенов по refresh_token | нет |
| GET | `/auth/me` | данные текущего пользователя | Bearer access_token |
| GET | `/`, `/health` | health-check | нет |

## Как другим сервисам проверять токен

Другие микросервисы (каталог, корзина и т.д.) не обращаются к auth-service по сети на каждый
запрос — они валидируют JWT локально тем же `SECRET_KEY`/`ALGORITHM` (см. `app/utils/security.py`,
функция `decode_token`). Это стандартный паттерн для stateless JWT в микросервисной архитектуре:
auth-service — единственный, кто **выдаёт** токены, а остальные сервисы их только **проверяют**.
