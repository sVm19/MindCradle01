-- ============================================================
-- 023: IVFFlat Approximate Nearest-Neighbor Index for Embeddings
-- ============================================================
-- This index dramatically speeds up vector similarity searches
-- at scale (O(√n) instead of O(n)).
-- The `lists` parameter should be ~sqrt(total_rows) for best
-- performance. 100 is suitable for up to ~1M rows.
-- ============================================================

-- IVFFlat index for fast cosine-similarity search on embeddings
CREATE INDEX IF NOT EXISTS idx_timeline_events_embedding
ON public.timeline_events
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Partial index: only index rows that have embeddings (avoids NULLs)
-- This keeps the index small and fast
CREATE INDEX IF NOT EXISTS idx_timeline_events_has_embedding
ON public.timeline_events (user_id, event_ts DESC)
WHERE embedding IS NOT NULL;
