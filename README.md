# Job Platform

Платформа для управления вакансиями и резюме с Telegram ботом.

## Архитектура

Проект состоит из нескольких компонентов:

- **job_aggregator** - API сервер (FastAPI)
- **job-bot** - Telegram бот для управления вакансиями и резюме

## Быстрый старт

### Требования

- Docker и Docker Compose
- Python 3.11+
- `.env.dev` и `.env.hh.dev` файлы (получить у администратора)

### Запуск в режиме разработки

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

### Остановка

```bash
docker-compose down
```

## Интеграционные тесты

### Автоматический запуск

```bash
# Запуск всех интеграционных тестов в изолированном окружении
python run_integration_tests.py
```

### Ручной запуск

```bash
# Запуск тестового окружения
docker-compose -f docker-compose.test.yml up -d

# Запуск тестов API
cd job_aggregator && python -m pytest tests/ -v

# Запуск интеграционных тестов бота
cd job-bot && python -m pytest tests/integration/ -v

# Остановка тестового окружения
docker-compose -f docker-compose.test.yml down -v
```

### Структура тестов

- **Unit тесты** - быстрые тесты без зависимостей
- **Интеграционные тесты** - полные тесты с реальными сервисами

## Переменные окружения

### Основные

- `POSTGRES_HOST` - хост базы данных
- `POSTGRES_PORT` - порт базы данных
- `POSTGRES_USER` - пользователь БД
- `POSTGRES_PASSWORD` - пароль БД
- `POSTGRES_DB` - имя базы данных

### Bot

- `BOT_TOKEN` - токен Telegram бота
- `API_URL` - URL API сервера

### HH.ru Integration

- `HH_CLIENT_ID` - ID приложения HH.ru
- `HH_CLIENT_SECRET` - секрет приложения HH.ru
- `HH_REDIRECT_URI` - URI перенаправления

## Разработка

### Структура проекта

```
job-platform/
├── docker-compose.yml          # Основное окружение
├── docker-compose.test.yml     # Тестовое окружение
├── run_integration_tests.py    # Скрипт интеграционных тестов
├── .env.dev                    # Переменные разработки
├── .env.hh.dev                 # HH.ru переменные разработки
├── job_aggregator/             # API сервер
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── tests/                  # Unit и интеграционные тесты API
│   └── ...
└── job-bot/                    # Telegram бот
    ├── Dockerfile
    ├── requirements.txt
    ├── tests/
    │   ├── unit/               # Unit тесты
    │   └── integration/        # Интеграционные тесты
    └── ...
```

### Добавление новых тестов

1. **Unit тесты**: добавляйте в соответствующие директории `tests/unit/`
2. **Интеграционные тесты**: добавляйте в `tests/integration/`
3. Запускайте через `python run_integration_tests.py`

## CI/CD

Проект поддерживает автоматическое тестирование:

```bash
# Запуск всех тестов (вызывается в CI)
python run_integration_tests.py --verbose
```

## Безопасность

- Никогда не коммитьте `.env*` файлы
- Токены HH.ru хранятся только на стороне API
- Access токены хранятся в памяти бота
- Refresh токены хранятся в базе данных API

## Поддержка

При проблемах:
1. Проверьте логи: `docker-compose logs`
2. Запустите тесты: `python run_integration_tests.py`
3. Проверьте переменные окружения
