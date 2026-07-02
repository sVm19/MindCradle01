-- Add PayPal subscription columns to user_profiles
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS paypal_agreement_id text DEFAULT null,
ADD COLUMN IF NOT EXISTS paypal_plan_id text DEFAULT null;
