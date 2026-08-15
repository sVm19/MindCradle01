-- Supabase migration: Add widget preferences to user_profiles table
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS widget_personalized_enabled boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS widget_memories_enabled boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS widget_aria_personalized_enabled boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS widget_sensitive_enabled boolean DEFAULT false;
