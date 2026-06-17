-- Add setting to user_profiles
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS notify_on_crisis boolean DEFAULT false;

-- Add details to crisis_flags logging table
ALTER TABLE public.crisis_flags
ADD COLUMN IF NOT EXISTS message text,
ADD COLUMN IF NOT EXISTS severity character varying;
