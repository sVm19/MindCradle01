# Master Implementation Plan: MindCradle Behavioral Strategy & Daily Discovery Engine

This document serves as the master blueprint for MindCradle, unifying the high-level **Behavioral & Product Strategy** with the detailed **Technical Implementation Specifications** for engineering.

---

## 🎯 Part 1: Strategic Foundations

### The Crisp Promise
**"MindCradle remembers your personal growth."**

Every feature in the application—from morning rituals to nightly check-ins—exists solely to capture, interpret, and reflect the user's growth back to them, making it visible and compounding over years.

### Three Core Questions
1. **Why would someone recommend MindCradle after just seven days?**
   - *The Aha! Moment*: On Day 3, ARIA references an unconscious linguistic shift in their logs (e.g., *"In your journals, you transitioned from high-friction words like 'should' on Day 1 to gentle verbs like 'allow' today. Your language is already softening. Let's look at why..."*). The user feels noticed, understood, and validated, prompting them to share.
2. **What happens inside MindCradle that literally cannot happen anywhere else?**
   - *The Daily Loom*: An interconnected daily loop. Features are not siloed tools. A morning intention shapes their journal prompt; afternoon energy logs customize ARIA's chat greeting; and soundscape selections feed monthly wellness trends.
3. **If OpenAI launches a journaling app tomorrow, why would users stay with MindCradle?**
   - *The Relational Moat*: OpenAI has general intelligence, but they don't have the user's private, verified longitudinal history. Even if another app allows importing logs, they cannot replicate ARIA's interpretive context, historical comparisons, and customized personality calibrations.

### The Signature Experience: "The Personal Solstice"
Once every month or season, MindCradle compiles **The Solstice Letter**—a visual, narrative-style AI summary analyzing the user's mental seasons, recurring stressors, and personal breakthroughs. This serves as the "Spotify Wrapped" for mental clarity.

---

## 2. Daily Discovery Engine (Phase 2 Upgrade)

Every day, ARIA proactively generates ONE evidence-based observation before the user types anything.
- **Maximum one discovery every 24 hours**.
- **Only generate discoveries when confidence is high** (Score $\ge 65$ out of 100).
- **Never hallucinate**; must reference actual logged data points.
- **Never repeat** previous discoveries.

---

## 3. Technical Proposed Changes

### Database Component

#### [NEW] [018_create_daily_discoveries.sql](file:///d:/WorkSpace/mindcradle/backend/supabase/migrations/018_create_daily_discoveries.sql)
Create the PostgreSQL schema table for tracking daily discoveries and user interaction states.
```sql
CREATE TABLE IF NOT EXISTS public.daily_discoveries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    discovery_text text NOT NULL,
    confidence_score integer NOT NULL,
    supporting_evidence jsonb DEFAULT '{}'::jsonb,
    is_dismissed boolean DEFAULT false NOT NULL,
    is_shared boolean DEFAULT false NOT NULL,
    is_viewed boolean DEFAULT false NOT NULL,
    viewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.daily_discoveries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own discoveries" ON public.daily_discoveries
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_daily_discoveries_user_id ON public.daily_discoveries(user_id);
```

---

### Backend Component

#### [MODIFY] [schemas.py](file:///d:/WorkSpace/mindcradle/backend/app/models/schemas.py)
* Add `DailyDiscoveryResponse` and `DiscoveryFeedbackRequest` schemas.

#### [MODIFY] [ai.py](file:///d:/WorkSpace/mindcradle/backend/app/routers/ai.py)
* Add dynamic Discovery Engine generator logic (`_generate_daily_discovery_internal`).
* Endpoints:
  - `GET /api/ai/daily-discovery`
  - `GET /api/ai/daily-discovery/history`
  - `PATCH /api/ai/daily-discovery/{id}/feedback`

#### [MODIFY] [main.py](file:///d:/WorkSpace/mindcradle/backend/app/main.py)
* Configure midnight UTC scheduler to pre-generate discoveries.

---

### Frontend Component

#### [MODIFY] [api.ts](file:///d:/WorkSpace/mindcradle/frontend/src/lib/api.ts)
* Add API integration methods.

#### [MODIFY] [Dashboard.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Dashboard.tsx)
* Render the proactive card with dismiss, share, and link to discoveries history.

#### [MODIFY] [ARIA.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/ARIA.tsx)
* Render today's discovery as a welcoming prompt from ARIA.

#### [NEW] [Discoveries.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Discoveries.tsx)
* Discovery history timeline page.

#### [MODIFY] [App.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/app/App.tsx)
* Route registry for `/discoveries`.

---

## 4. Verification Plan

### Automated Tests
- Build verification check: `npm run build`
- Pytest backend tests.

### Manual Verification
1. Verify discovery is rendered as card on Dashboard.
2. Confirm dismiss and share actions track in database.
3. Access `/discoveries` to check timeline history.
