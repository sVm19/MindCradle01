-- Create emotion_insights table
CREATE TABLE public.emotion_insights (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    emotion character varying NOT NULL,
    frequency integer DEFAULT 0 NOT NULL,
    last_appeared timestamp with time zone,
    trend character varying, -- e.g., 'up', 'down', 'stable'
    context_when_common text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on emotion_insights
ALTER TABLE public.emotion_insights ENABLE ROW LEVEL SECURITY;

-- Create policies for emotion_insights
CREATE POLICY "Users can manage their own emotion_insights" ON public.emotion_insights
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index for emotion_insights
CREATE INDEX idx_emotion_insights_user_id_emotion ON public.emotion_insights(user_id, emotion);


-- Create advice_effectiveness table
CREATE TABLE public.advice_effectiveness (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    conversation_id uuid REFERENCES public.ai_conversations(id) ON DELETE CASCADE NOT NULL,
    advice_given text NOT NULL,
    help_rating integer CHECK (help_rating >= 1 AND help_rating <= 3), -- 1=not helpful, 3=very helpful
    timestamp timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    follow_up_mood integer CHECK (follow_up_mood >= 1 AND follow_up_mood <= 10),
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on advice_effectiveness
ALTER TABLE public.advice_effectiveness ENABLE ROW LEVEL SECURITY;

-- Create policies for advice_effectiveness
CREATE POLICY "Users can manage their own advice_effectiveness" ON public.advice_effectiveness
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index for advice_effectiveness
CREATE INDEX idx_advice_effectiveness_user_id_convo_id ON public.advice_effectiveness(user_id, conversation_id);


-- Create conversation_themes table
CREATE TABLE public.conversation_themes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    conversation_id uuid REFERENCES public.ai_conversations(id) ON DELETE CASCADE NOT NULL,
    theme character varying NOT NULL,
    theme_category character varying,
    mentioned_emotions jsonb DEFAULT '[]'::jsonb NOT NULL,
    solutions_tried jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on conversation_themes
ALTER TABLE public.conversation_themes ENABLE ROW LEVEL SECURITY;

-- Create policies for conversation_themes
CREATE POLICY "Users can manage their own conversation_themes" ON public.conversation_themes
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index for conversation_themes
CREATE INDEX idx_conversation_themes_user_id_theme ON public.conversation_themes(user_id, theme);


-- Create user_personality table
CREATE TABLE public.user_personality (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    communication_style character varying,
    preference_advice_type character varying,
    response_length_preference character varying,
    emotional_openness character varying,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on user_personality
ALTER TABLE public.user_personality ENABLE ROW LEVEL SECURITY;

-- Create policies for user_personality
CREATE POLICY "Users can manage their own user_personality" ON public.user_personality
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index for user_personality
CREATE INDEX idx_user_personality_user_id ON public.user_personality(user_id);

-- Create trigger function for updated_at on user_personality
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_personality_updated_at
    BEFORE UPDATE ON public.user_personality
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();


-- Create proactive_checkins table
CREATE TABLE public.proactive_checkins (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    scheduled_time timestamp with time zone NOT NULL,
    reason character varying,
    suggested_message text,
    actual_response text,
    effectiveness integer CHECK (effectiveness >= 1 AND effectiveness <= 5),
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on proactive_checkins
ALTER TABLE public.proactive_checkins ENABLE ROW LEVEL SECURITY;

-- Create policies for proactive_checkins
CREATE POLICY "Users can manage their own proactive_checkins" ON public.proactive_checkins
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index for proactive_checkins
CREATE INDEX idx_proactive_checkins_user_id_sched ON public.proactive_checkins(user_id, scheduled_time);


-- Create recovery_data table
CREATE TABLE public.recovery_data (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    mood_dip_date timestamp with time zone NOT NULL,
    lowest_level integer CHECK (lowest_level >= 1 AND lowest_level <= 10) NOT NULL,
    recovery_date timestamp with time zone,
    recovery_days integer,
    catalyst character varying,
    severity character varying,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on recovery_data
ALTER TABLE public.recovery_data ENABLE ROW LEVEL SECURITY;

-- Create policies for recovery_data
CREATE POLICY "Users can manage their own recovery_data" ON public.recovery_data
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index for recovery_data
CREATE INDEX idx_recovery_data_user_id ON public.recovery_data(user_id);


-- Create engagement_metrics table
CREATE TABLE public.engagement_metrics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    conversation_id uuid REFERENCES public.ai_conversations(id) ON DELETE CASCADE NOT NULL,
    user_response_time integer, -- in seconds
    suggestion_followed boolean,
    return_time_hours integer,
    sentiment_shift integer CHECK (sentiment_shift >= -10 AND sentiment_shift <= 10),
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on engagement_metrics
ALTER TABLE public.engagement_metrics ENABLE ROW LEVEL SECURITY;

-- Create policies for engagement_metrics
CREATE POLICY "Users can manage their own engagement_metrics" ON public.engagement_metrics
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index for engagement_metrics
CREATE INDEX idx_engagement_metrics_user_id_convo_id ON public.engagement_metrics(user_id, conversation_id);


-- Create crisis_flags table
CREATE TABLE public.crisis_flags (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    conversation_id uuid REFERENCES public.ai_conversations(id) ON DELETE CASCADE NOT NULL,
    severity_level integer CHECK (severity_level >= 1 AND severity_level <= 4) NOT NULL, -- 1-4
    red_flags_detected jsonb DEFAULT '[]'::jsonb NOT NULL,
    action_taken text,
    admin_reviewed boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS on crisis_flags
ALTER TABLE public.crisis_flags ENABLE ROW LEVEL SECURITY;

-- Create policies for crisis_flags
CREATE POLICY "Users can manage their own crisis_flags" ON public.crisis_flags
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Create index for crisis_flags
CREATE INDEX idx_crisis_flags_user_id_severity ON public.crisis_flags(user_id, severity_level);
