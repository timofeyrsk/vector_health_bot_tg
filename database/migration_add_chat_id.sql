-- Migration: Add chat_id column to user_profiles table
-- This migration adds the chat_id column for storing Telegram chat IDs

-- Add chat_id column to user_profiles table
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS chat_id BIGINT;

-- Add comment to explain the column
COMMENT ON COLUMN user_profiles.chat_id IS 'Telegram Chat ID for sending messages';

-- Create index for better performance when querying by chat_id
CREATE INDEX IF NOT EXISTS idx_user_profiles_chat_id ON user_profiles(chat_id);

-- Log the migration
DO $$
BEGIN
    RAISE NOTICE 'Migration completed: Added chat_id column to user_profiles table';
END $$; 