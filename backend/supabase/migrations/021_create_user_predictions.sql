-- ============================================================
-- 021: Personal Growth Predictive Intelligence Table
-- ============================================================

CREATE TABLE IF NOT EXISTS public.user_predictions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Identifies which model type this prediction is from
    prediction_type text NOT NULL, -- 'wind_down_skip_friday' | 'challenging_tomorrow' | 'activity_mood_boost'
    
    -- The prediction text presented to the user
    prediction_text text NOT NULL,
    
    -- The target date this prediction applies to (YYYY-MM-DD)
    target_date date NOT NULL,
    
    -- Confidence score between 0 and 100
    confidence_score integer CHECK (confidence_score >= 0 AND confidence_score <= 100) NOT NULL,
    
    -- Verification results: NULL (pending), true (correct), false (incorrect)
    is_correct boolean,
    evaluated_at timestamp with time zone,
    
    -- Dynamic metadata
    metadata jsonb DEFAULT '{}'::jsonb,
    
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    -- Prevent duplicate prediction of same type for the same target date
    UNIQUE (user_id, prediction_type, target_date)
);

-- Enable RLS
ALTER TABLE public.user_predictions ENABLE ROW LEVEL SECURITY;

-- Policies for RLS
CREATE POLICY "Users can manage their own predictions"
    ON public.user_predictions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_predictions_user_id ON public.user_predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_predictions_evaluation ON public.user_predictions(user_id, is_correct, target_date);
