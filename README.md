# Portfolio API — бэкенд портфолио разработчика

REST API для сайта-портфолио с AI-анализом обратной связи, email-уведомлениями и файловым хранилищем.

## 🚀 Деплой

*   **Интерактивная документация (Swagger):** [docs](https://test-proj-fastapi.onrender.com/docs)
*   **Главная страница приложения:** [test-proj-fastapi.onrender.com](https://test-proj-fastapi.onrender.com)


**Важно:** Render блокирует отправку писем на бесплатном тарифе по SMTP (локально я использовал яндекс почту и отправка/получение писем работает). 
И в бесплатном тарифе если нет активности render отключает сервис на время. Нужно около 1 минуты для автоматического запуска.

---

## Быстрый старт

**Требования:** Python 3.9+, pip.

```bash
# 1. Клонировать репозиторий
git clone <url-репозитория>
cd test-proj-fastapi

# 2. Создать и активировать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # macOS / Linux

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить переменные окружения
cp .env.example .env
# Отредактировать .env — указать OPENROUTER_API_KEY
# (получить ключ: https://openrouter.ai/keys)

# 5. Запустить сервер
uvicorn app.main:app --reload
```

После запуска:

- Фронтенд: <http://127.0.0.1:8000/>
- Swagger-документация: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

### Переменные окружения

```ini
# AI (OpenRouter) — обязательное поле
OPENROUTER_API_KEY=sk-or-v1-...

# Модель (по умолчанию openrouter/free)
OPENROUTER_MODEL=openrouter/free

# SMTP для email-уведомлений (необязательно)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=app-password
SMTP_FROM=noreply@portfolio.dev
SMTP_TO=owner@email.com

# Rate Limiting (по умолчанию 5 запросов в час)
RATE_LIMIT_MAX_REQUESTS=5
RATE_LIMIT_WINDOW_SECONDS=3600
```

**Важно:** Для AI-аналитики нужен `OPENROUTER_API_KEY`. Без него — fallback-значения. Email опционален — без SMTP письма имитируются.

---

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| **Язык** | Python 3.14 |
| **Фреймворк** | FastAPI 0.115+ |
| **ASGI-сервер** | Uvicorn |
| **Валидация** | Pydantic 2.9+ (Pydantic Settings) |
| **AI-анализ** | OpenRouter (бесплатные модели) + Google AI |
| **HTTP-клиент** | httpx (async) |
| **Email** | smtplib |
| **Хранилище** | JSON-файлы |
| **Фронтенд** | Alpine.js + Tailwind CSS (CDN) |
| **Документация** | Swagger (/docs), ReDoc (/redoc) |

**Почему так:**

- **FastAPI** — современный, асинхронный, со встроенной OpenAPI-документацией.
- **Pydantic** — runtime-валидация на входе, схемы для Swagger.
- **OpenRouter** — бесплатный доступ к множеству AI-моделей через единый API.
- **Файловое хранилище** — для портфолио БД не нужна, JSON проще в развёртывании.
- **httpx** — асинхронный HTTP-клиент (не блокирует event loop).

---

## Архитектура

### Структура проекта

```
test-proj-fastapi/
├── app/
│   ├── core/
│   │   └── config.py              # Pydantic Settings (.env)
│   ├── routers/
│   │   └── contact_router.py      # Controller — эндпоинты + DI
│   ├── schemas/
│   │   └── contact_schema.py      # Pydantic-модели
│   ├── services/
│   │   ├── ai_service.py          # AI-анализ через OpenRouter
│   │   └── email_service.py       # SMTP-уведомления
│   ├── repositories/
│   │   └── metrics_repository.py  # Чтение/запись JSON
│   ├── storage/                   # metrics.json, rate_limits.json, app.log
│   ├── static/
│   │   └── index.html             # Фронтенд (Alpine.js)
│   └── main.py                    # Точка входа, middleware, error handler
├── .env.example
└── requirements.txt
```

### Паттерны

Многослойная архитектура (layered):

```
HTTP Request → Router (Controller) → Service Layer → Repository Layer → File System
```

- **Router** — HTTP, валидация, DI, статус-коды.
- **Service** — бизнес-логика, внешние API.
- **Repository** — хранение (файлы).

**Dependency Injection:** Зависимости передаются через `Depends()`.

---

## API

### POST /api/contact

Основной эндпоинт. Принимает форму → AI-анализ → email → статистика.

**Request:**
```json
{
  "name": "Иван Петров",
  "phone": "+7 999 123 45 67",
  "email": "ivan@example.com",
  "comment": "Отличное портфолио! Хочу обсудить проект."
}
```

**Success (201):**
```json
{
  "success": true,
  "message": "Thank you! Your message has been received.",
  "sentiment": "позитивный",
  "category": "сотрудничество"
}
```

**Errors:**
- **422** — валидация: `name` (2–100), `phone` (7–20), `email` (EmailStr), `comment` (10–2000)
- **429** — rate limit: `{"detail": "Слишком много запросов. Попробуйте через 1845 секунд."}`
- **500** — внутренняя ошибка сервера

### GET /api/health

```json
{"status": "ok", "service": "portfolio-api"}
```

### GET /api/metrics

```json
{
  "total_contacts": 12,
  "sentiments": {
    "позитивный": 5, "негативный": 2,
    "нейтральный": 4, "неопределен": 1
  },
  "categories": {
    "сотрудничество": 3, "фидбек": 5,
    "вопрос": 2, "общее": 2
  }
}
```

---

## AI-интеграция

### Инструменты

- **Провайдер:** [OpenRouter](https://openrouter.ai/) — бесплатные модели (также использовался Google AI).
- **Модель:** `openrouter/free` — автоматический выбор доступной бесплатной модели.
- **HTTP-клиент:** `httpx.AsyncClient` — асинхронные запросы.

### Системный промпт

```text
Ты — ИИ-классификатор обращений. Твоя задача — проанализировать комментарий
пользователя на русском языке.

Верни СТРОГО один JSON-объект. Не пиши никакого текста до или после JSON.
Не используй разметку ```json.

Формат ответа: {"sentiment": "позитивный", "category": "вопрос"}

Допустимые sentiment: позитивный, негативный, нейтральный.
Допустимые category: оффер, сотрудничество, вопрос, фидбек, спам, общее.
```

Промпт содержит few-shot примеры. `response_format: json_object`, `temperature: 0.1`.

### Fallback

При любой ошибке (сетевой сбой, неверный JSON, нет API-ключа):
```json
{"sentiment": "неопределен", "category": "общее"}
```
Форма продолжает работать, даже если AI недоступен.

---

## Хранение данных

Всё хранится в `app/storage/`:

- **`metrics.json`** — статистика обращений.
- **`rate_limits.json`** — метки запросов для rate limiting.
- **`app.log`** — лог всех запросов в формате `[timestamp] CONTACT ip=... email=...`.

Файлы и директория создаются автоматически при первом запуске.

---

## Rate Limiting

Скользящее окно на основе JSON-файла:
- **По умолчанию:** 5 запросов в час с одного IP.
- **Настройка:** `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS`.
- **Механизм:** для каждого IP хранятся временные метки. Старые удаляются. При превышении лимита — HTTP 429 + заголовок `Retry-After`.
- **IP detection:** учитывает `X-Forwarded-For`.

---

## Что сделано с помощью AI

Проект написан с использованием AI-ассистентов из OpenRouter (бесплатные модели + deepseek).

**Сгенерировано автоматически:**

- Почти весь код — структура FastAPI, роутеры, схемы, сервисы, репозитории, фронтенд, README.
- Большие архитектурные промпты и точечные запросы на улучшение.
- Перед написанием проводился ресерч best-practices.

**Что исправлено вручную:**

- Немного дизайн фронтенда.
- Неточности README.
---
