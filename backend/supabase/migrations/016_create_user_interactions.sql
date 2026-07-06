-- Create user_interactions table for clickstream and placeholder tracking
CREATE TABLE IF NOT EXISTS public.user_interactions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    event_type character varying NOT NULL, -- 'click', 'input_submit', 'navigation'
    element_id character varying,
    element_name character varying,
    page_path character varying NOT NULL,
    input_placeholder character varying,
    input_length integer DEFAULT 0,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.user_interactions ENABLE ROW LEVEL SECURITY;

-- Create policy for user interactions
CREATE POLICY "Users can manage their own interactions" ON public.user_interactions
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index for user_id
CREATE INDEX IF NOT EXISTS idx_user_interactions_user_id ON public.user_interactions(user_id);
