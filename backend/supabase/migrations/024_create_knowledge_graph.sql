-- ============================================================
-- 024: Compounding Intelligence Engine — Personal Knowledge Graph
-- ============================================================
-- Creates the 7-table PKG schema that allows ARIA to build an
-- increasingly accurate model of each individual user over time.
-- ============================================================

-- ── 1. user_knowledge_nodes ──────────────────────────────────────────────────
-- The atoms of ARIA's understanding. Each node is a concept, entity, theme,
-- habit, goal, emotion, or value that ARIA has detected about the user.

CREATE TABLE IF NOT EXISTS public.user_knowledge_nodes (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

    -- Identity
    label           text NOT NULL,
    node_type       text NOT NULL,
    canonical_label text,                   -- normalised/lowercased for dedup

    -- Intelligence scores
    confidence      float DEFAULT 0.5 NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    importance      int   DEFAULT 5   NOT NULL CHECK (importance >= 1 AND importance <= 10),
    valence         float DEFAULT 0.0 NOT NULL CHECK (valence >= -1 AND valence <= 1),

    -- Evidence tracking
    mention_count       int NOT NULL DEFAULT 1,
    first_seen_at       timestamptz NOT NULL DEFAULT now(),
    last_seen_at        timestamptz NOT NULL DEFAULT now(),

    -- Semantic search
    embedding       vector(1536),

    -- Provenance / transparency
    source_reason   text,
    is_confirmed    boolean NOT NULL DEFAULT false,
    is_archived     boolean NOT NULL DEFAULT false,

    metadata        jsonb NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT knowledge_node_type_check CHECK (node_type IN (
        'theme', 'entity', 'person', 'place', 'goal',
        'habit', 'emotion', 'value', 'stressor', 'coping', 'achievement'
    ))
);

ALTER TABLE public.user_knowledge_nodes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own knowledge nodes"
    ON public.user_knowledge_nodes
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_user_type
    ON public.user_knowledge_nodes (user_id, node_type, confidence DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_user_label
    ON public.user_knowledge_nodes (user_id, canonical_label);

CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_user_active
    ON public.user_knowledge_nodes (user_id, last_seen_at DESC)
    WHERE is_archived = false;

CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_embedding
    ON public.user_knowledge_nodes USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);


-- ── 2. user_knowledge_edges ──────────────────────────────────────────────────
-- Directed relationships between knowledge nodes.
-- "work stress" --[triggers]--> "Sunday dread"
-- "journaling" --[helps_with]--> "anxiety"

CREATE TABLE IF NOT EXISTS public.user_knowledge_edges (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    source_node_id  uuid REFERENCES public.user_knowledge_nodes(id) ON DELETE CASCADE NOT NULL,
    target_node_id  uuid REFERENCES public.user_knowledge_nodes(id) ON DELETE CASCADE NOT NULL,

    edge_type       text NOT NULL,
    weight          float NOT NULL DEFAULT 0.3 CHECK (weight >= 0 AND weight <= 1),
    evidence_count  int NOT NULL DEFAULT 1,
    last_reinforced_at timestamptz NOT NULL DEFAULT now(),

    metadata        jsonb NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now(),

    UNIQUE (user_id, source_node_id, target_node_id, edge_type),

    CONSTRAINT knowledge_edge_type_check CHECK (edge_type IN (
        'triggers', 'causes', 'correlates_with', 'part_of',
        'leads_to', 'contrasts_with', 'associated_with', 'helps_with', 'blocks'
    ))
);

ALTER TABLE public.user_knowledge_edges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own knowledge edges"
    ON public.user_knowledge_edges
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_edges_user_source
    ON public.user_knowledge_edges (user_id, source_node_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_edges_user_target
    ON public.user_knowledge_edges (user_id, target_node_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_edges_weight
    ON public.user_knowledge_edges (user_id, weight DESC);


-- ── 3. user_life_chapters ────────────────────────────────────────────────────
-- Detected periods in the user's life, each with a narrative title.
-- "The Startup Grind" → "The Rebuilding" → "Finding My Rhythm"

CREATE TABLE IF NOT EXISTS public.user_life_chapters (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

    title               text NOT NULL,
    chapter_number      int  NOT NULL,
    start_date          date NOT NULL,
    end_date            date,           -- NULL = current chapter
    is_current          boolean NOT NULL DEFAULT false,

    theme_summary       text,
    dominant_emotion    text,
    mood_average        float,
    growth_score        float,

    key_events          jsonb NOT NULL DEFAULT '[]',
    dominant_themes     text[],
    goals_started       text[],
    goals_achieved      text[],
    node_ids            uuid[],

    detected_by         text NOT NULL DEFAULT 'system',
    confidence          float NOT NULL DEFAULT 0.7,

    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.user_life_chapters ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own life chapters"
    ON public.user_life_chapters
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_life_chapters_user_current
    ON public.user_life_chapters (user_id, is_current, start_date DESC);


-- ── 4. user_behavioral_patterns ─────────────────────────────────────────────
-- Detected habits, routines, cycles, and trigger-response patterns.

CREATE TABLE IF NOT EXISTS public.user_behavioral_patterns (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

    pattern_type    text NOT NULL,
    label           text NOT NULL,
    description     text,

    -- Temporal profile
    frequency               text,
    days_of_week            int[],
    hour_range              int[],
    is_consistent           boolean NOT NULL DEFAULT false,

    -- Impact
    is_positive             boolean,
    mood_impact             float,
    confidence              float NOT NULL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),

    -- Streak tracking
    streak_current          int NOT NULL DEFAULT 0,
    streak_best             int NOT NULL DEFAULT 0,
    last_occurrence         timestamptz,
    detected_at             timestamptz NOT NULL DEFAULT now(),
    last_confirmed_at       timestamptz,

    related_node_ids        uuid[],
    metadata                jsonb NOT NULL DEFAULT '{}',
    created_at              timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT behavioral_pattern_type_check CHECK (pattern_type IN (
        'habit', 'routine', 'cycle', 'trigger_response'
    ))
);

ALTER TABLE public.user_behavioral_patterns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own behavioral patterns"
    ON public.user_behavioral_patterns
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_behavioral_patterns_user
    ON public.user_behavioral_patterns (user_id, confidence DESC);


-- ── 5. user_growth_metrics ───────────────────────────────────────────────────
-- Weekly snapshots of 10 measurable growth dimensions.

CREATE TABLE IF NOT EXISTS public.user_growth_metrics (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

    metric_type     text NOT NULL,
    period          text NOT NULL,
    value           float NOT NULL,
    previous_value  float,
    delta           float,
    percentile      float,

    computed_at     timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT growth_metric_type_check CHECK (metric_type IN (
        'mood_average', 'emotional_regulation', 'self_awareness',
        'consistency_index', 'stress_resilience', 'positive_momentum',
        'goal_clarity', 'linguistic_growth', 'journal_depth', 'pattern_awareness'
    )),

    CONSTRAINT growth_period_check CHECK (period IN ('7d', '30d', '90d'))
);

ALTER TABLE public.user_growth_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view their own growth metrics"
    ON public.user_growth_metrics
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_growth_metrics_user_type
    ON public.user_growth_metrics (user_id, metric_type, period, computed_at DESC);


-- ── 6. user_entity_mentions ──────────────────────────────────────────────────
-- Raw log of every time a knowledge node is mentioned in a source document.
-- Used to compute confidence, importance, and reinforcement signals.

CREATE TABLE IF NOT EXISTS public.user_entity_mentions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    node_id         uuid REFERENCES public.user_knowledge_nodes(id) ON DELETE CASCADE NOT NULL,

    source_type     text NOT NULL,
    source_id       uuid NOT NULL,
    context_snippet text,
    sentiment       float CHECK (sentiment >= -1 AND sentiment <= 1),

    extracted_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT entity_mention_source_check CHECK (source_type IN (
        'journal', 'mood', 'morning', 'wind_down', 'aria', 'discovery'
    ))
);

ALTER TABLE public.user_entity_mentions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view their own entity mentions"
    ON public.user_entity_mentions
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_entity_mentions_user_node
    ON public.user_entity_mentions (user_id, node_id, extracted_at DESC);

CREATE INDEX IF NOT EXISTS idx_entity_mentions_source
    ON public.user_entity_mentions (user_id, source_type, source_id);


-- ── 7. user_goal_threads ─────────────────────────────────────────────────────
-- Longitudinal tracking of user goals across all content.

CREATE TABLE IF NOT EXISTS public.user_goal_threads (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

    goal_label          text NOT NULL,
    description         text,
    first_mentioned_at  timestamptz NOT NULL,
    last_mentioned_at   timestamptz NOT NULL,
    mention_count       int NOT NULL DEFAULT 1,

    progress_signal     text NOT NULL DEFAULT 'unknown',
    progress_notes      text,
    evidence            jsonb NOT NULL DEFAULT '[]',

    related_node_ids    uuid[],
    chapter_ids         uuid[],

    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT goal_progress_check CHECK (progress_signal IN (
        'growing', 'stalled', 'achieved', 'abandoned', 'unknown'
    ))
);

ALTER TABLE public.user_goal_threads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own goal threads"
    ON public.user_goal_threads
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_goal_threads_user
    ON public.user_goal_threads (user_id, last_mentioned_at DESC);

CREATE INDEX IF NOT EXISTS idx_goal_threads_progress
    ON public.user_goal_threads (user_id, progress_signal);


-- ── Shared updated_at trigger ────────────────────────────────────────────────
-- Reuse the handle_updated_at() function from migration 019

CREATE OR REPLACE TRIGGER trg_knowledge_nodes_updated
    BEFORE UPDATE ON public.user_knowledge_nodes
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE OR REPLACE TRIGGER trg_life_chapters_updated
    BEFORE UPDATE ON public.user_life_chapters
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE OR REPLACE TRIGGER trg_goal_threads_updated
    BEFORE UPDATE ON public.user_goal_threads
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
