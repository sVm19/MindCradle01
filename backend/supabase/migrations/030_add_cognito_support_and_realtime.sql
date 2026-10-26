-- ============================================================
-- 030: Amazon Cognito JIT Sync & Realtime Replication Support
-- ============================================================
-- 1. Adds cognito_sub and email columns to public.user_profiles
-- 2. Creates get_or_create_cognito_user RPC function
-- 3. Enables Supabase Realtime on public.user_profiles
-- ============================================================

-- 1. Add cognito_sub and email to user_profiles
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS cognito_sub VARCHAR UNIQUE;
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS email VARCHAR;

-- Create index on cognito_sub for fast JIT lookup
CREATE INDEX IF NOT EXISTS idx_user_profiles_cognito_sub ON public.user_profiles(cognito_sub);

-- 2. RPC function to get or create Cognito user atomically in auth.users and user_profiles
CREATE OR REPLACE FUNCTION public.get_or_create_cognito_user(
    p_cognito_sub UUID,
    p_email_address TEXT,
    p_user_name TEXT DEFAULT ''
)
RETURNS TABLE (
    user_id UUID,
    user_email VARCHAR,
    user_name TEXT
) AS $$
#variable_conflict use_column
DECLARE
    target_user_id UUID;
    ret_email VARCHAR;
    ret_name TEXT;
BEGIN
    -- 1. Check if user already linked via cognito_sub in user_profiles
    SELECT up.user_id, COALESCE(up.email, p_email_address), COALESCE(up.name, p_user_name)
    INTO target_user_id, ret_email, ret_name
    FROM public.user_profiles up
    WHERE up.cognito_sub = p_cognito_sub::text;

    -- 2. If not found by cognito_sub, check if user exists by email in auth.users
    IF target_user_id IS NULL THEN
        SELECT id, email, COALESCE((raw_user_meta_data->>'name'), p_email_address)
        INTO target_user_id, ret_email, ret_name
        FROM auth.users
        WHERE email = p_email_address;
    END IF;

    -- 3. If still not found, create new user in auth.users using Cognito sub UUID
    IF target_user_id IS NULL THEN
        target_user_id := p_cognito_sub;
        ret_email := p_email_address;
        ret_name := p_user_name;

        INSERT INTO auth.users (
            id,
            instance_id,
            email,
            encrypted_password,
            email_confirmed_at,
            created_at,
            updated_at,
            raw_app_meta_data,
            raw_user_meta_data,
            is_super_admin,
            role,
            aud
        ) VALUES (
            target_user_id,
            '00000000-0000-0000-0000-000000000000',
            ret_email,
            '',
            timezone('utc'::text, now()),
            timezone('utc'::text, now()),
            timezone('utc'::text, now()),
            '{"provider":"cognito","providers":["cognito"]}'::jsonb,
            jsonb_build_object('name', ret_name),
            false,
            'authenticated',
            'authenticated'
        );
    END IF;

    -- 4. Ensure public.user_profiles record exists and is linked
    INSERT INTO public.user_profiles (
        user_id,
        cognito_sub,
        email,
        name,
        unlocked_badges,
        badge_history,
        created
    ) VALUES (
        target_user_id,
        p_cognito_sub::text,
        ret_email,
        ret_name,
        '[]'::jsonb,
        '[]'::jsonb,
        timezone('utc'::text, now())
    )
    ON CONFLICT (user_id) DO UPDATE
    SET 
        cognito_sub = COALESCE(public.user_profiles.cognito_sub, EXCLUDED.cognito_sub),
        email = COALESCE(public.user_profiles.email, EXCLUDED.email),
        name = COALESCE(public.user_profiles.name, EXCLUDED.name);

    RETURN QUERY SELECT target_user_id, ret_email, ret_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Enable Supabase Realtime Replication on public.user_profiles
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' AND tablename = 'user_profiles'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.user_profiles;
    END IF;
END $$;
