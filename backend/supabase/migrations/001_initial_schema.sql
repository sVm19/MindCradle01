-- Create resources table
CREATE TABLE public.resources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    description text NOT NULL,
    icon text NOT NULL,
    color_class text NOT NULL,
    category text NOT NULL,
    "order" integer NOT NULL,
    url text,
    is_active boolean DEFAULT true,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on resources
ALTER TABLE public.resources ENABLE ROW LEVEL SECURITY;

-- Allow public read access to resources
CREATE POLICY "Allow public read access to resources" ON public.resources
    FOR SELECT USING (true);

-- Create mood_logs table
CREATE TABLE public.mood_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    level integer NOT NULL CHECK (level >= 1 AND level <= 10),
    emotions jsonb DEFAULT '[]'::jsonb,
    note text,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on mood_logs
ALTER TABLE public.mood_logs ENABLE ROW LEVEL SECURITY;

-- Create policies for mood_logs
CREATE POLICY "Users can manage their own mood_logs" ON public.mood_logs
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create journal_entries table
CREATE TABLE public.journal_entries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    prompt text NOT NULL,
    content text NOT NULL,
    ai_reflection text,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on journal_entries
ALTER TABLE public.journal_entries ENABLE ROW LEVEL SECURITY;

-- Create policies for journal_entries
CREATE POLICY "Users can manage their own journal_entries" ON public.journal_entries
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create morning_rituals table
CREATE TABLE public.morning_rituals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    forecast text NOT NULL,
    intention text NOT NULL,
    activity_type text NOT NULL,
    completed_at timestamp with time zone NOT NULL,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on morning_rituals
ALTER TABLE public.morning_rituals ENABLE ROW LEVEL SECURITY;

-- Create policies for morning_rituals
CREATE POLICY "Users can manage their own morning_rituals" ON public.morning_rituals
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create wind_down_rituals table
CREATE TABLE public.wind_down_rituals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    release_item text NOT NULL,
    gratitudes jsonb DEFAULT '[]'::jsonb,
    audio_choice text NOT NULL,
    timer text NOT NULL,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on wind_down_rituals
ALTER TABLE public.wind_down_rituals ENABLE ROW LEVEL SECURITY;

-- Create policies for wind_down_rituals
CREATE POLICY "Users can manage their own wind_down_rituals" ON public.wind_down_rituals
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create ai_conversations table
CREATE TABLE public.ai_conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    messages jsonb DEFAULT '[]'::jsonb,
    summary text,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on ai_conversations
ALTER TABLE public.ai_conversations ENABLE ROW LEVEL SECURITY;

-- Create policies for ai_conversations
CREATE POLICY "Users can manage their own ai_conversations" ON public.ai_conversations
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create function to update updated on ai_conversations
CREATE OR REPLACE FUNCTION public.handle_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_ai_conversations_updated
    BEFORE UPDATE ON public.ai_conversations
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated();

-- Create user_profiles table
CREATE TABLE public.user_profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    unlocked_badges jsonb DEFAULT '[]'::jsonb,
    badge_history jsonb DEFAULT '[]'::jsonb,
    created timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on user_profiles
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Create policies for user_profiles
CREATE POLICY "Users can manage their own user_profiles" ON public.user_profiles
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
