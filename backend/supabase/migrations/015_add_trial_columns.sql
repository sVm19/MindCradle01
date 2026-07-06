-- Add Trial columns to user_profiles
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS trial_started_at timestamp with time zone DEFAULT null,
ADD COLUMN IF NOT EXISTS trial_ends_at timestamp with time zone DEFAULT null,
ADD COLUMN IF NOT EXISTS trial_used boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS trial_active boolean DEFAULT false;

-- Create check_expired_trials RPC to clean up expired trials
CREATE OR REPLACE FUNCTION public.check_expired_trials()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE public.user_profiles
    SET 
        is_premium = false,
        trial_active = false,
        subscription_expires_at = null,
        subscription_token = null
    WHERE 
        trial_active = true 
        AND trial_ends_at <= timezone('utc'::text, now());
END;
$$;
