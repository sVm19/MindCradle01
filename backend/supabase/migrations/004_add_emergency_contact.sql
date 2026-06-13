-- Add emergency_contact field to user_profiles
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS emergency_contact text;
