-- ============================================================
-- 022: Enable Vector Search on Supabase via pgvector
-- ============================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to timeline_events (OpenAI/OpenRouter text-embedding-3-small uses 1536 dims)
ALTER TABLE public.timeline_events ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create semantic similarity search function
CREATE OR REPLACE FUNCTION match_timeline_events(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    p_user_id uuid
)
RETURNS TABLE (
    id uuid,
    user_id uuid,
    event_type text,
    source_id uuid,
    event_date date,
    event_ts timestamp with time zone,
    title text,
    summary text,
    emotion text,
    mood_level int,
    metadata jsonb,
    search_text text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        te.id,
        te.user_id,
        te.event_type,
        te.source_id,
        te.event_date,
        te.event_ts,
        te.title,
        te.summary,
        te.emotion,
        te.mood_level,
        te.metadata,
        te.search_text,
        (1 - (te.embedding <=> query_embedding))::float AS similarity
    FROM
        public.timeline_events te
    WHERE
        te.user_id = p_user_id
        AND te.embedding IS NOT NULL
        AND (1 - (te.embedding <=> query_embedding)) > match_threshold
    ORDER BY
        te.embedding <=> query_embedding
    LIMIT
        match_count;
END;
$$;
