-- Create user_privacy_acceptance table
CREATE TABLE IF NOT EXISTS public.user_privacy_acceptance (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    privacy_accepted boolean DEFAULT false NOT NULL,
    accepted_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.user_privacy_acceptance ENABLE ROW LEVEL SECURITY;

-- Create policies for user_privacy_acceptance
CREATE POLICY "Users can manage their own privacy acceptance" ON public.user_privacy_acceptance
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
