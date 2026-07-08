-- ============================================================
-- 020: Personal Growth Timeline Events Cache Table
-- ============================================================
-- This table acts as a denormalized cache aggregating events
-- from mood_logs, journal_entries, morning_rituals,
-- wind_down_rituals, daily_discoveries, and user_profiles
-- (milestones). It enables fast full-text search and filtering
-- without expensive multi-table JOINs on every request.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.timeline_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

    -- Identifies which source table this event came from
    event_type text NOT NULL,   -- 'morning' | 'mood' | 'journal' | 'discovery' | 'milestone' | 'wind_down' | 'letter'

    -- FK back to the originating record (nullable for synthetic events like milestones)
    source_id uuid,

    -- Primary sort key — date only for grouping
    event_date date NOT NULL,

    -- Full timestamp for precise ordering within a day
    event_ts timestamp with time zone NOT NULL,

    -- Human-readable fields for display
    title text,
    summary text,
    emotion text,
    mood_level integer,     -- for mood events (1–10)

    -- Denormalised content for full-text search (GIN index)
    search_text text,

    -- Arbitrary event-type-specific payload
    metadata jsonb DEFAULT '{}'::jsonb,

    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,

    -- Prevent duplicate caching of the same source record
    UNIQUE (user_id, event_type, source_id)
);

-- Row Level Security
ALTER TABLE public.timeline_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their own timeline events"
    ON public.timeline_events
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Composite index: user's events sorted newest-first
CREATE INDEX IF NOT EXISTS idx_timeline_events_user_date
    ON public.timeline_events (user_id, event_ts DESC);

-- GIN index for full-text keyword search
CREATE INDEX IF NOT EXISTS idx_timeline_events_fts
    ON public.timeline_events
    USING gin(to_tsvector('english', COALESCE(search_text, '')));

-- Index on event_type for type-filter queries
CREATE INDEX IF NOT EXISTS idx_timeline_events_type
    ON public.timeline_events (user_id, event_type);
