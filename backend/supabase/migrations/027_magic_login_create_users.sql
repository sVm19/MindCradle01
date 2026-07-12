-- Allow magic-link sign-in to create a first-time passwordless account.
CREATE OR REPLACE FUNCTION public.create_magic_login_token_for_email(
    email_address TEXT,
    magic_token TEXT,
    expiry_seconds INTEGER
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

    INSERT INTO public.magic_login_tokens (user_id, token, expires_at)
    VALUES (target_user_id, magic_token, expires_timestamp);

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
