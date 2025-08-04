# Vector-Health AI Nutritionist Bot - Текущая структура проекта

```
vector-health-bot/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container configuration
├── docker-compose.yml          # Docker Compose setup
├── readme.md                   # Comprehensive documentation
├── env_template.txt            # Environment variables template
├── todo.md                     # Development progress tracker
├── SETUP_INSTRUCTIONS.md       # Setup instructions
├── PROJECT_STRUCTURE.md        # This file
├── test_imports.py             # Import test script
│
├── src/
│   └── app.py                  # Flask application factory
│
├── config/
│   └── settings.py             # Configuration management
│
├── database/
│   ├── connection.py           # Database connection and session management
│   └── schema.sql              # PostgreSQL schema with pgvector
│
├── models/
│   ├── __init__.py            # Models package initialization
│   ├── user_profile.py        # User profile model
│   ├── food_log.py            # Food logging model with embeddings
│   └── activity_log.py        # Activity tracking model
│
├── routes/
│   ├── __init__.py            # Routes package initialization
│   ├── telegram_routes.py     # Telegram webhook endpoints
│   ├── terra_routes.py        # Terra API webhook endpoints
│   └── health_routes.py       # Health data API endpoints
│
├── services/
│   ├── __init__.py            # Services package initialization
│   ├── openai_service.py      # OpenAI GPT-4o and embeddings integration
│   ├── terra_service.py       # Terra API integration for wearables
│   ├── telegram_service.py    # Telegram bot logic and conversation flow
│   └── health_service.py      # Health calculations and data processing
│
├── utils/
│   └── health_utils.py        # Health calculation utilities and meal planning
│
└── tests/
    ├── __init__.py            # Tests package initialization
    ├── test_config.py         # Test configuration and base classes
    └── test_health_utils.py   # Unit tests for health utilities
```

## Статус проекта

### ✅ Завершено:
- ✅ Восстановлена правильная архитектура проекта
- ✅ Все файлы перенесены в соответствующие папки
- ✅ Исправлены все импорты в соответствии с новой структурой
- ✅ Созданы `__init__.py` файлы для всех пакетов
- ✅ Настроены отношения между моделями
- ✅ Все импорты проходят проверку
- ✅ Приложение успешно запускается

### 📋 Следующие шаги:
1. Создать файл `.env` на основе `env_template.txt`
2. Настроить переменные окружения (API ключи, токены)
3. Настроить базу данных (PostgreSQL с pgvector)
4. Запустить приложение: `python main.py`

### 🚀 Команды для работы:
```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Проверить импорты
python test_imports.py

# Запустить приложение
python main.py
```

## Архитектура

Проект теперь полностью соответствует документации и использует правильную модульную структуру:

- **src/**: Основное приложение Flask
- **config/**: Конфигурация и настройки
- **database/**: Подключение к базе данных и схемы
- **models/**: SQLAlchemy модели данных
- **routes/**: API маршруты и эндпоинты
- **services/**: Бизнес-логика и интеграции с внешними API
- **utils/**: Вспомогательные функции
- **tests/**: Модульные тесты

Все импорты настроены корректно и проект готов к дальнейшей разработке и развертыванию. 