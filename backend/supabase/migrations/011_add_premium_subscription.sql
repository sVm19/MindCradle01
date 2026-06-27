-- Add premium subscription columns to user_profiles
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS is_premium boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS subscription_expires_at timestamp with time zone DEFAULT null,
ADD COLUMN IF NOT EXISTS subscription_token text DEFAULT null;
