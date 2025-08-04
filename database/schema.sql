-- Vector-Health AI Nutritionist Bot Database Schema
-- This script creates the necessary tables for the application

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- User profiles table
CREATE TABLE user_profiles (
    user_id BIGINT PRIMARY KEY,  -- Telegram User ID
    chat_id BIGINT,  -- Telegram Chat ID for sending messages
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    gender TEXT,
    age SMALLINT,
    height_cm SMALLINT,
    current_weight_kg NUMERIC(5,2),
    target_weight_kg NUMERIC(5,2),
    goal TEXT,  -- 'lose_weight', 'maintain_weight', 'gain_weight'
    activity_level TEXT,  -- 'sedentary', 'moderate', 'active'
    bmr NUMERIC(7,2),  -- Basal Metabolic Rate
    tdee NUMERIC(7,2),  -- Total Daily Energy Expenditure
    daily_calorie_target INTEGER,
    daily_protein_target_g NUMERIC(6,2),
    daily_fat_target_g NUMERIC(6,2),
    daily_carbs_target_g NUMERIC(6,2),
    terra_user_id TEXT  -- Terra API user ID for wearable integration
);

-- Food logs table
CREATE TABLE food_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT NOT NULL,
    dish_name TEXT,
    estimated_ingredients TEXT,
    estimated_weight_g NUMERIC(7,2),
    calories INTEGER,
    protein_g NUMERIC(6,2),
    fat_g NUMERIC(6,2),
    carbs_g NUMERIC(6,2),
    food_embedding_vector VECTOR(1536),  -- OpenAI text-embedding-3-small dimension
    log_type TEXT DEFAULT 'manual',  -- 'photo', 'text', 'manual'
    photo_url TEXT  -- Store photo URL if applicable
);

-- Activity logs table
CREATE TABLE activity_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    active_calories INTEGER,
    steps INTEGER,
    sleep_duration_min INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)  -- One record per user per day
);

-- Create indexes for better performance
CREATE INDEX idx_food_logs_user_id ON food_logs(user_id);
CREATE INDEX idx_food_logs_created_at ON food_logs(created_at);
CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_date ON activity_logs(date);

-- Create index for vector similarity search
CREATE INDEX ON food_logs USING ivfflat (food_embedding_vector vector_cosine_ops) WITH (lists = 100);

