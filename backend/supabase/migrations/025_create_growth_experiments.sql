-- ============================================================
-- 025: Product Growth & A/B Experimentation System
-- ============================================================
-- Creates the schema for managing, assigning, and measuring A/B
-- experiments and tracking funnel activation events.
-- ============================================================

-- ── 1. ab_experiments ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.ab_experiments (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL UNIQUE,
    description     text,
    variants        text[] NOT NULL,
    status          text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'paused', 'completed')),
    started_at      timestamptz,
    ended_at        timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.ab_experiments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read experiments" 
    ON public.ab_experiments FOR SELECT USING (true);


-- ── 2. ab_assignments ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.ab_assignments (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    experiment_id     uuid REFERENCES public.ab_experiments(id) ON DELETE CASCADE NOT NULL,
    assigned_variant  text NOT NULL,
    assigned_at       timestamptz NOT NULL DEFAULT now(),
    
    UNIQUE (user_id, experiment_id)
);

ALTER TABLE public.ab_assignments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own assignments"
    ON public.ab_assignments FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_ab_assignments_user_id ON public.ab_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_ab_assignments_experiment_id ON public.ab_assignments(experiment_id);


-- ── 3. growth_events ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.growth_events (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    event_name      text NOT NULL,
    properties      jsonb NOT NULL DEFAULT '{}'::jsonb,
    experiment_id   uuid REFERENCES public.ab_experiments(id) ON DELETE SET NULL,
    variant         text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.growth_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own growth events"
    ON public.growth_events FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_growth_events_user_id ON public.growth_events(user_id);
CREATE INDEX IF NOT EXISTS idx_growth_events_experiment_id ON public.growth_events(experiment_id);
CREATE INDEX IF NOT EXISTS idx_growth_events_name ON public.growth_events(event_name);


-- ── 4. Seed Initial Growth Experiments ───────────────────────────────────────
INSERT INTO public.ab_experiments (name, description, variants, status, started_at)
VALUES 
    ('morning_habit_layout', 'Test standard habits grid layout vs a visual card-based layout to increase engagement.', ARRAY['control', 'creative'], 'running', now()),
    ('onboarding_pricing_version', 'A/B test yearly subscription with a 7-day trial vs direct pricing card.', ARRAY['control', 'trial_pass'], 'running', now())
ON CONFLICT (name) DO NOTHING;
