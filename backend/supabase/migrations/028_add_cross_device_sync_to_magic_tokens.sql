-- Migration 028: Add cross-device sync columns and helper functions for magic_login_tokens

-- 1. Add columns to public.magic_login_tokens
ALTER TABLE public.magic_login_tokens ADD COLUMN IF NOT EXISTS session_id VARCHAR;
ALTER TABLE public.magic_login_tokens ADD COLUMN IF NOT EXISTS verified_device VARCHAR;
ALTER TABLE public.magic_login_tokens ADD COLUMN IF NOT EXISTS used BOOLEAN DEFAULT FALSE;

-- 2. Re-create create_magic_login_token_for_email to accept session_id
CREATE OR REPLACE FUNCTION public.create_magic_login_token_for_email(
    email_address TEXT,
    magic_token TEXT,
    expiry_seconds INTEGER,
    p_session_id TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    target_user_id UUID;
    normalized_email TEXT;
    expires_timestamp TIMESTAMP WITH TIME ZONE;
BEGIN
    normalized_email := lower(trim(email_address));

    SELECT id INTO target_user_id
    FROM auth.users
    WHERE email = normalized_email;

    IF target_user_id IS NULL THEN
        target_user_id := gen_random_uuid();

        INSERT INTO auth.users (
            id,
            instance_id,
            email,
            encrypted_password,
            email_confirmed_at,
            raw_app_meta_data,
            raw_user_meta_data,
            created_at,
            updated_at,
            role,
            aud
        ) VALUES (
            target_user_id,
            '00000000-0000-0000-0000-000000000000',
            normalized_email,
            crypt(gen_random_uuid()::text, gen_salt('bf')),
            now(),
            jsonb_build_object('provider', 'magic_link', 'providers', array['magic_link']),
            jsonb_build_object('name', split_part(normalized_email, '@', 1)),
            now(),
            now(),
            'authenticated',
            'authenticated'
        );

        INSERT INTO public.user_profiles (user_id, unlocked_badges, badge_history, created, name)
        VALUES (target_user_id, '[]'::jsonb, '[]'::jsonb, now(), split_part(normalized_email, '@', 1))
        ON CONFLICT (user_id) DO NOTHING;
    END IF;

    expires_timestamp := now() + (expiry_seconds || ' seconds')::INTERVAL;

    DELETE FROM public.magic_login_tokens WHERE user_id = target_user_id;

    INSERT INTO public.magic_login_tokens (user_id, token, expires_at, session_id)
    VALUES (target_user_id, magic_token, expires_timestamp, p_session_id);

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Create verify_magic_login_token security definer function
CREATE OR REPLACE FUNCTION public.verify_magic_login_token(
    p_token TEXT,
    p_device_info TEXT
)
RETURNS TABLE (
    user_id UUID,
    user_email VARCHAR,
    user_name TEXT,
    session_id VARCHAR
) AS $$
DECLARE
    target_user_id UUID;
    token_expiry TIMESTAMP WITH TIME ZONE;
    ret_email VARCHAR;
    ret_name TEXT;
    ret_session_id VARCHAR;
    is_already_used BOOLEAN;
BEGIN
    -- Find and validate token
    SELECT t.user_id, t.expires_at, t.session_id, t.used INTO target_user_id, token_expiry, ret_session_id, is_already_used
    FROM public.magic_login_tokens t
    WHERE t.token = p_token;

    IF target_user_id IS NULL THEN
        RAISE EXCEPTION 'Invalid magic link';
    END IF;

    IF token_expiry < now() THEN
        -- Delete if expired
        DELETE FROM public.magic_login_tokens WHERE token = p_token;
        RAISE EXCEPTION 'Link expired';
    END IF;

    IF is_already_used THEN
        RAISE EXCEPTION 'Link already used';
    END IF;

    -- Update token as used and set verified_device
    UPDATE public.magic_login_tokens
    SET used = TRUE, verified_device = p_device_info
    WHERE token = p_token;

    -- Get user details
    SELECT email, (raw_user_meta_data->>'name') INTO ret_email, ret_name FROM auth.users WHERE id = target_user_id;

    RETURN QUERY SELECT target_user_id, ret_email, COALESCE(ret_name, ''), ret_session_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Create check_magic_login_session security definer function
CREATE OR REPLACE FUNCTION public.check_magic_login_session(
    p_session_id TEXT
)
RETURNS TABLE (
    verified BOOLEAN,
    user_id UUID,
    user_email VARCHAR,
    user_name TEXT
) AS $$
DECLARE
    target_user_id UUID;
    is_used BOOLEAN;
    token_expiry TIMESTAMP WITH TIME ZONE;
    ret_email VARCHAR;
    ret_name TEXT;
    matching_token TEXT;
BEGIN
    -- Find the token matching the session_id
    SELECT t.user_id, t.used, t.expires_at, t.token INTO target_user_id, is_used, token_expiry, matching_token
    FROM public.magic_login_tokens t
    WHERE t.session_id = p_session_id;

    IF target_user_id IS NULL THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, ''::VARCHAR, ''::TEXT;
        RETURN;
    END IF;

    IF token_expiry < now() THEN
        -- Delete if expired
        DELETE FROM public.magic_login_tokens WHERE token = matching_token;
        RETURN QUERY SELECT FALSE, NULL::UUID, ''::VARCHAR, ''::TEXT;
        RETURN;
    END IF;

    IF is_used THEN
        -- Verified! Get user details
        SELECT email, (raw_user_meta_data->>'name') INTO ret_email, ret_name FROM auth.users WHERE id = target_user_id;
        
        -- Delete the token now that it has been consumed by the PC session check
        DELETE FROM public.magic_login_tokens WHERE token = matching_token;
        
        RETURN QUERY SELECT TRUE, target_user_id, ret_email, COALESCE(ret_name, '');
    ELSE
        RETURN QUERY SELECT FALSE, NULL::UUID, ''::VARCHAR, ''::TEXT;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
