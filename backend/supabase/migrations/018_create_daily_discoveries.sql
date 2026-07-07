-- Create daily_discoveries table
CREATE TABLE IF NOT EXISTS public.daily_discoveries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    discovery_text text NOT NULL,
    confidence_score integer NOT NULL,
    supporting_evidence jsonb DEFAULT '{}'::jsonb,
    is_dismissed boolean DEFAULT false NOT NULL,
    is_shared boolean DEFAULT false NOT NULL,
    is_viewed boolean DEFAULT false NOT NULL,
    viewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.daily_discoveries ENABLE ROW LEVEL SECURITY;

-- Create policy for users to manage their own discoveries
CREATE POLICY "Users can manage their own discoveries" ON public.daily_discoveries
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index on user_id
CREATE INDEX IF NOT EXISTS idx_daily_discoveries_user_id ON public.daily_discoveries(user_id);
