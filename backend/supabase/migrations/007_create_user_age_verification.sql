-- Create user_age_verification table
CREATE TABLE IF NOT EXISTS public.user_age_verification (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    age_verified boolean DEFAULT false NOT NULL,
    verified_at timestamp with time zone,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.user_age_verification ENABLE ROW LEVEL SECURITY;

-- Create policies for user_age_verification
CREATE POLICY "Users can manage their own age verification" ON public.user_age_verification
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
