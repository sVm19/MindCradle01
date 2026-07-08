# Master Implementation Plan: ARIA Relationship Memory System

This document serves as the master blueprint for ARIA's **Relationship Memory System**, replacing raw message logs with long-term, structured relationship memories.

---

## 🎯 Part 1: Strategic Foundations

### The Crisp Promise
**"MindCradle remembers your personal growth."**

ARIA should stop remembering simple text messages. She should remember the relationship. This is achieved by creating structured **Memory Objects** (growth breakthroughs, triggers, stressors) with importance scales, emotional tags, and linkage to actual journal entries.

---

## 2. Technical Proposed Changes

### Database Component

#### [NEW] [019_create_relationship_memories.sql](file:///d:/WorkSpace/mindcradle/backend/supabase/migrations/019_create_relationship_memories.sql)
Create the PostgreSQL schema table for tracking user memories.
```sql
CREATE TABLE IF NOT EXISTS public.user_relationship_memories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title text NOT NULL,
    type text NOT NULL, -- 'growth', 'stressor', 'breakthrough', 'ritual_habit', 'mood_trigger'
    importance integer DEFAULT 5 NOT NULL, -- 1 to 10
    emotion text,
    confidence integer DEFAULT 50 NOT NULL, -- 0 to 100
    related_journal uuid REFERENCES public.journal_entries(id) ON DELETE SET NULL,
    related_mood uuid REFERENCES public.mood_logs(id) ON DELETE SET NULL,
    first_occurrence timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    last_occurrence timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    times_referenced integer DEFAULT 0 NOT NULL,
    supporting_evidence jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.user_relationship_memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own memories" ON public.user_relationship_memories
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_user_relationship_memories_user_id ON public.user_relationship_memories(user_id);
```

---

### Backend Component

#### [MODIFY] [schemas.py](file:///d:/WorkSpace/mindcradle/backend/app/models/schemas.py)
* Add `RelationshipMemoryResponse` schema.

#### [MODIFY] [ai.py](file:///d:/WorkSpace/mindcradle/backend/app/routers/ai.py)
* Add relevance ranking logic (`_retrieve_relationship_memories`).
* Add memory consolidation engine (`consolidate_relationship_memories`).
* Integrate memory contexts into `/chat` endpoint.

---

## 3. Verification Plan

### Automated Tests
- Build verification check: `npm run build`
- Unit tests verifying ranking and retrieval logic:
  ```powershell
  .venv\Scripts\pytest backend/tests/test_relationship_memories.py
  ```
