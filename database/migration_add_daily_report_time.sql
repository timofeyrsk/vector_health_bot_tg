-- Migration: Add daily_report_time field to user_profiles table
-- This field will store the time for daily reports in MSK timezone

ALTER TABLE user_profiles 
ADD COLUMN daily_report_time TIME;

-- Add comment to document the field
COMMENT ON COLUMN user_profiles.daily_report_time IS 'Time for daily reports in MSK timezone (HH:MM format)'; 