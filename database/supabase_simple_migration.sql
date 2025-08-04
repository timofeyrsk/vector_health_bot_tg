-- Простая миграция для добавления chat_id в Supabase
-- Скопируйте и вставьте этот код в SQL редактор Supabase

-- 1. Добавляем колонку chat_id (если её нет)
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS chat_id BIGINT;

-- 2. Добавляем комментарий к колонке
COMMENT ON COLUMN user_profiles.chat_id IS 'Telegram Chat ID for sending messages';

-- 3. Создаем индекс для оптимизации (если его нет)
CREATE INDEX IF NOT EXISTS idx_user_profiles_chat_id ON user_profiles(chat_id);

-- 4. Проверяем результат
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'user_profiles' 
AND column_name = 'chat_id'; 