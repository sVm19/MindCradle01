-- Create user_password_history table
CREATE TABLE IF NOT EXISTS public.user_password_history (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    password_hash text NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.user_password_history ENABLE ROW LEVEL SECURITY;

-- Create access policies for user_password_history
CREATE POLICY "Users can manage their own password history" ON public.user_password_history
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
