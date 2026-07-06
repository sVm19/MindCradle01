-- Remove PayPal-related columns from user_profiles table
ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS paypal_agreement_id;
ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS paypal_plan_id;

