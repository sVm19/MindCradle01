-- Create magic_login_tokens table
CREATE TABLE IF NOT EXISTS public.magic_login_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    token VARCHAR UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index for fast token lookups
CREATE INDEX IF NOT EXISTS idx_magic_login_token ON public.magic_login_tokens(token);

-- Enable Row Level Security (RLS)
ALTER TABLE public.magic_login_tokens ENABLE ROW LEVEL SECURITY;

-- RPC to securely create a magic login token for an email address (looks up user ID and inserts/replaces token)
CREATE OR REPLACE FUNCTION public.create_magic_login_token_for_email(
    email_address TEXT,
    magic_token TEXT,
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
    
    -- Insert or replace token for this user
    INSERT INTO public.magic_login_tokens (user_id, token, expires_at)
    VALUES (target_user_id, magic_token, expires_timestamp)
    ON CONFLICT (token) DO UPDATE 
    SET expires_at = expires_timestamp;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC to securely consume a magic login token (verifies, deletes, and returns user details)
CREATE OR REPLACE FUNCTION public.consume_magic_login_token(
    magic_token TEXT
)
RETURNS TABLE (
    user_id UUID,
    user_email VARCHAR,
    user_name TEXT
) AS $$
DECLARE
    target_user_id UUID;
    token_expiry TIMESTAMP WITH TIME ZONE;
    ret_email VARCHAR;
    ret_name TEXT;
BEGIN
    -- Find and validate token
    SELECT t.user_id, t.expires_at INTO target_user_id, token_expiry
    FROM public.magic_login_tokens t
    WHERE t.token = magic_token;

    IF target_user_id IS NULL OR token_expiry < now() THEN
        -- Delete if expired
        IF magic_token IS NOT NULL THEN
            DELETE FROM public.magic_login_tokens WHERE token = magic_token;
        END IF;
        RETURN;
    END IF;

    -- Get user details from auth.users (email) and metadata
    SELECT email, (raw_user_meta_data->>'name') INTO ret_email, ret_name FROM auth.users WHERE id = target_user_id;

    -- Delete all login tokens for this user
    DELETE FROM public.magic_login_tokens WHERE magic_login_tokens.user_id = target_user_id;

    RETURN QUERY SELECT target_user_id, ret_email, COALESCE(ret_name, '');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
