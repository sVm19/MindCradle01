-- ============================================================
-- 026: Google OAuth Database Support
-- ============================================================
-- Adds support for Google-only signup and Google OAuth logins.
-- ============================================================

-- Add google_id and name columns to public.user_profiles (which we own)
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS google_id VARCHAR;
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS name VARCHAR;

-- RPC to securely verify/retrieve/create Google user accounts in auth.users
CREATE OR REPLACE FUNCTION public.get_or_create_google_user(
    p_email_address TEXT,
    p_user_name TEXT,
    p_google_sub TEXT
)
RETURNS TABLE (
    user_id UUID,
    user_email VARCHAR,
    user_name TEXT
) AS $$
DECLARE
    target_user_id UUID;
    ret_email VARCHAR;
    ret_name TEXT;
BEGIN
    -- 1. Try to find user by email in auth.users
    SELECT id, email, COALESCE((raw_user_meta_data->>'name'), p_email_address) INTO target_user_id, ret_email, ret_name
    FROM auth.users
    WHERE email = p_email_address;
    
    -- 2. If not found, create a new user record
    IF target_user_id IS NULL THEN
        target_user_id := gen_random_uuid();
        ret_email := p_email_address;
        ret_name := p_user_name;
        
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
            p_email_address,
            -- Hashed dummy password since they log in via Google
            crypt(gen_random_uuid()::text, gen_salt('bf')),
            now(),
            jsonb_build_object('provider', 'google', 'providers', array['google']),
            jsonb_build_object('name', p_user_name, 'google_id', p_google_sub),
            now(),
            now(),
            'authenticated',
            'authenticated'
        );
        
        -- Create corresponding public user_profile
        INSERT INTO public.user_profiles (user_id, unlocked_badges, badge_history, created, google_id, name)
        VALUES (target_user_id, '[]'::jsonb, '[]'::jsonb, now(), p_google_sub, p_user_name)
        ON CONFLICT (user_id) DO UPDATE
        SET google_id = p_google_sub, name = p_user_name;
    ELSE
        -- If user exists, update details in auth.users' JSON metadata
        UPDATE auth.users
        SET 
            raw_user_meta_data = jsonb_set(
                jsonb_set(COALESCE(raw_user_meta_data, '{}'::jsonb), '{google_id}', to_jsonb(p_google_sub)),
                '{name}',
                to_jsonb(COALESCE(raw_user_meta_data->>'name', p_user_name))
            )
        WHERE id = target_user_id;
        
        -- Also update details in user_profiles
        INSERT INTO public.user_profiles (user_id, unlocked_badges, badge_history, created, google_id, name)
        VALUES (target_user_id, '[]'::jsonb, '[]'::jsonb, now(), p_google_sub, p_user_name)
        ON CONFLICT (user_id) DO UPDATE
        SET google_id = p_google_sub, name = COALESCE(public.user_profiles.name, p_user_name);
    END IF;
    
    RETURN QUERY SELECT target_user_id, ret_email, COALESCE(ret_name, '');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
