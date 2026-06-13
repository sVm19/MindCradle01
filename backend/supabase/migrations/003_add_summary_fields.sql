-- Add summary and tracking fields to ai_conversations
ALTER TABLE public.ai_conversations
ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS key_points jsonb DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS follow_up_needed boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS follow_up_date date,
ADD COLUMN IF NOT EXISTS emotional_journey text;
