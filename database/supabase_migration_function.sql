-- Функция для выполнения миграции добавления chat_id в Supabase
-- Выполните эту функцию в SQL редакторе Supabase

CREATE OR REPLACE FUNCTION migrate_add_chat_id()
RETURNS TEXT AS $$
DECLARE
    result TEXT;
BEGIN
    -- Проверяем, существует ли уже колонка chat_id
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_profiles' 
        AND column_name = 'chat_id'
    ) THEN
        result := 'Колонка chat_id уже существует в таблице user_profiles';
    ELSE
        -- Добавляем колонку chat_id
        ALTER TABLE user_profiles ADD COLUMN chat_id BIGINT;
        
        -- Добавляем комментарий к колонке
        COMMENT ON COLUMN user_profiles.chat_id IS 'Telegram Chat ID for sending messages';
        
        -- Создаем индекс для оптимизации запросов
        CREATE INDEX idx_user_profiles_chat_id ON user_profiles(chat_id);
        
        result := 'Миграция успешно выполнена: добавлена колонка chat_id в таблицу user_profiles';
    END IF;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Выполняем миграцию
SELECT migrate_add_chat_id();

-- Удаляем функцию после выполнения
DROP FUNCTION migrate_add_chat_id(); 