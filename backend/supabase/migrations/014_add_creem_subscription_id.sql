-- Add Creem subscription column to user_profiles
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS creem_subscription_id text DEFAULT null;
