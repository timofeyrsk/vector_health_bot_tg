# Инструкции по настройке Vector-Health AI Nutritionist Bot

## ✅ Что уже сделано:
- ✅ Создано виртуальное окружение Python 3.13.3
- ✅ Установлены все зависимости из requirements.txt
- ✅ Восстановлена правильная архитектура проекта согласно документации
- ✅ Все файлы перенесены в соответствующие папки (src/, config/, database/, models/, routes/, services/, utils/, tests/)
- ✅ Исправлены все импорты в соответствии с новой структурой
- ✅ Проверена работоспособность всех модулей
- ✅ Приложение успешно запускается (требует настройки переменных окружения)

## 📋 Следующие шаги для запуска:

### 1. Создание файла .env
Скопируйте содержимое файла `env_template.txt` в новый файл `.env`:
```bash
cp env_template.txt .env
```

### 2. Настройка переменных окружения
Отредактируйте файл `.env` и заполните следующие обязательные переменные:

#### Обязательные:
- `DATABASE_URL` - URL подключения к PostgreSQL базе данных
- `OPENAI_API_KEY` - API ключ OpenAI
- `TELEGRAM_BOT_TOKEN` - Токен Telegram бота
- `TERRA_DEV_ID` - ID разработчика Terra API
- `TERRA_API_KEY` - API ключ Terra

#### Опциональные:
- `SUPABASE_URL` и `SUPABASE_KEY` - для использования Supabase
- `TELEGRAM_WEBHOOK_URL` - для настройки вебхука Telegram
- `TERRA_WEBHOOK_SECRET` - секрет для вебхука Terra

### 3. Настройка базы данных
Выберите один из вариантов:

#### Вариант A: Supabase (рекомендуется для новичков)
1. Создайте аккаунт на [supabase.com](https://supabase.com)
2. Создайте новый проект
3. Включите расширение `pgvector`
4. Выполните SQL скрипт из `schema.sql`
5. Скопируйте строку подключения в `DATABASE_URL`

#### Вариант B: Локальная PostgreSQL
1. Установите PostgreSQL
2. Создайте базу данных
3. Включите расширение `pgvector`
4. Выполните SQL скрипт из `schema.sql`

### 4. Создание Telegram бота
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен в `TELEGRAM_BOT_TOKEN`

### 5. Настройка OpenAI
1. Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com)
2. Создайте API ключ
3. Скопируйте ключ в `OPENAI_API_KEY`

### 6. Настройка Terra API (опционально)
1. Зарегистрируйтесь на [tryterra.co](https://tryterra.co)
2. Создайте приложение
3. Скопируйте Dev ID и API Key

### 7. Запуск приложения
```bash
# Активируйте виртуальное окружение (если еще не активировано)
source venv/bin/activate

# Запустите приложение
python main.py
```

## 🔧 Устранение неполадок

### Виртуальное окружение
- Активация: `source venv/bin/activate`
- Деактивация: `deactivate`
- Переустановка зависимостей: `pip install -r requirements.txt`

### Проверка установки
```bash
python -c "import flask, openai, sqlalchemy; print('Все пакеты установлены корректно')"
```

## 📚 Дополнительная информация
- Подробная документация: `readme.md`
- Структура проекта: `Vector-Health AI Nutritionist Bot - Project Structure.md`
- Список задач: `todo.md` 