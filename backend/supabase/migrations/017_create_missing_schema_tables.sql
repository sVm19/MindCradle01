-- Create user_memory_insights table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.user_memory_insights (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    conversation_id uuid REFERENCES public.ai_conversations(id) ON DELETE SET NULL,
    situation text,
    what_happened text,
    emotion text,
    what_helped text,
    follow_up text,
    context_type text,
    date text,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on user_memory_insights
ALTER TABLE public.user_memory_insights ENABLE ROW LEVEL SECURITY;

-- Create policies for user_memory_insights
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'user_memory_insights' AND policyname = 'Users can manage their own user_memory_insights'
    ) THEN
        CREATE POLICY "Users can manage their own user_memory_insights" ON public.user_memory_insights
            FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;


-- Create push_notification_tokens table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.push_notification_tokens (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    push_token text NOT NULL,
    platform text NOT NULL,
    device_id text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE (user_id, device_id)
);

-- Enable RLS on push_notification_tokens
ALTER TABLE public.push_notification_tokens ENABLE ROW LEVEL SECURITY;

-- Create policies for push_notification_tokens
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'push_notification_tokens' AND policyname = 'Users can manage their own push_notification_tokens'
    ) THEN
        CREATE POLICY "Users can manage their own push_notification_tokens" ON public.push_notification_tokens
            FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;
