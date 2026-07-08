-- Create user_relationship_memories table
CREATE TABLE IF NOT EXISTS public.user_relationship_memories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title text NOT NULL,
    type text NOT NULL, -- 'growth', 'stressor', 'breakthrough', 'ritual_habit', 'mood_trigger'
    importance integer DEFAULT 5 NOT NULL CHECK (importance >= 1 AND importance <= 10),
    emotion text,
    confidence integer DEFAULT 50 NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    related_journal uuid REFERENCES public.journal_entries(id) ON DELETE SET NULL,
    related_mood uuid REFERENCES public.mood_logs(id) ON DELETE SET NULL,
    first_occurrence timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    last_occurrence timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    times_referenced integer DEFAULT 0 NOT NULL CHECK (times_referenced >= 0),
    supporting_evidence jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT user_relationship_memories_type_check
        CHECK (type IN ('growth', 'stressor', 'breakthrough', 'ritual_habit', 'mood_trigger', 'relationship_pattern', 'coping_pattern'))
);

-- Enable RLS on user_relationship_memories
ALTER TABLE public.user_relationship_memories ENABLE ROW LEVEL SECURITY;

-- Create policies for user_relationship_memories
CREATE POLICY "Users can manage their own memories" ON public.user_relationship_memories
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index on user_id for faster retrieval
CREATE INDEX IF NOT EXISTS idx_user_relationship_memories_user_id ON public.user_relationship_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_user_relationship_memories_rank
    ON public.user_relationship_memories(user_id, importance DESC, last_occurrence DESC, times_referenced DESC);
CREATE INDEX IF NOT EXISTS idx_user_relationship_memories_type
    ON public.user_relationship_memories(user_id, type);

DROP TRIGGER IF EXISTS trigger_update_user_relationship_memories_updated ON public.user_relationship_memories;
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_relationship_memories_updated
    BEFORE UPDATE ON public.user_relationship_memories
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
