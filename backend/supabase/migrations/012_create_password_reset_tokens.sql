-- Create password_reset_tokens table
CREATE TABLE IF NOT EXISTS public.password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    token VARCHAR UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index for fast token lookups
CREATE INDEX IF NOT EXISTS idx_password_reset_token ON public.password_reset_tokens(token);

-- Enable Row Level Security (RLS)
ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;

-- RPC to securely create a reset token for an email address (looks up user ID and inserts/replaces token)
CREATE OR REPLACE FUNCTION public.create_password_reset_token_for_email(
    email_address TEXT,
    reset_token TEXT,
    expiry_seconds INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    target_user_id UUID;
    expires_timestamp TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Get user ID from auth.users securely
    SELECT id INTO target_user_id FROM auth.users WHERE email = email_address;
    
    IF target_user_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    expires_timestamp := now() + (expiry_seconds || ' seconds')::INTERVAL;
    
    -- Insert or replace existing token for this user
    INSERT INTO public.password_reset_tokens (user_id, token, expires_at)
    VALUES (target_user_id, reset_token, expires_timestamp)
    ON CONFLICT (token) DO UPDATE 
    SET expires_at = expires_timestamp;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC to securely fetch the password history for a valid/non-expired token (for history validations)
CREATE OR REPLACE FUNCTION public.get_password_history_by_token(reset_token TEXT)
RETURNS TABLE (password_hash TEXT) AS $$
DECLARE
    target_user_id UUID;
BEGIN
    -- Find user_id from token if token is valid and not expired
    SELECT user_id INTO target_user_id
    FROM public.password_reset_tokens
    WHERE token = reset_token AND expires_at >= now();
    
    IF target_user_id IS NOT NULL THEN
        RETURN QUERY
        SELECT h.password_hash
        FROM public.user_password_history h
        WHERE h.user_id = target_user_id
        ORDER BY h.created_at DESC
        LIMIT 5;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC to securely reset password in auth.users and record the new hash in password history
CREATE OR REPLACE FUNCTION public.reset_password_with_token(
    reset_token TEXT,
    new_encrypted_password TEXT,
    new_history_hash TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    target_user_id UUID;
    token_expiry TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Find and validate token
    SELECT user_id, expires_at INTO target_user_id, token_expiry
    FROM public.password_reset_tokens
    WHERE token = reset_token;

    IF target_user_id IS NULL THEN
        RETURN FALSE;
    END IF;

    IF token_expiry < now() THEN
        -- Delete expired token
        DELETE FROM public.password_reset_tokens WHERE token = reset_token;
        RETURN FALSE;
    END IF;

    -- Update the password in auth.users
    UPDATE auth.users
    SET encrypted_password = new_encrypted_password
    WHERE id = target_user_id;

    -- Record in password history
    INSERT INTO public.user_password_history (user_id, password_hash)
    VALUES (target_user_id, new_history_hash);

    -- Delete all tokens for this user after successful reset
    DELETE FROM public.password_reset_tokens WHERE user_id = target_user_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
