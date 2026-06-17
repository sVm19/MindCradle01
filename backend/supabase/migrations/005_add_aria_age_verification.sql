-- Add age verification fields to user_profiles
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS aria_age_verified boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS aria_verified_at timestamp with time zone;
