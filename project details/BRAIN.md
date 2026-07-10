# MindCradle - Project Brain

## 🎯 Project Overview
Mental wellness app with mood tracking, daily rituals, journaling, and a compounding personal AI companion (ARIA).
Freemium model: Free + Premium ($9.99/month).
Target: Anyone managing stress/anxiety seeking self-discovery.

---

## 🏗️ Tech Stack
- **Frontend**: React (TypeScript) + Vite + Tailwind CSS + Framer Motion
- **Backend**: FastAPI + Python (Uvicorn)
- **Database**: PostgreSQL (Supabase) + pgvector
- **Auth**: JWT + Supabase Auth
- **AI**: OpenRouter (Google Gemma-4-31b-it + openai/text-embedding-3-small)
- **Notifications**: Firebase Cloud Messaging
- **Emails**: Resend
- **Payments**: Creem
- **Deployment**: Google Cloud Run (backend), Vercel (frontend)

---

## 🗄️ Database Tables (26 total)

### Core Tables (6)
- **users**: user records (`id`, `email`, `hashed_password`, `created_at`, `privacy_accepted`, `age_verified`)
- **mood_logs**: daily emotional check-ins (`id`, `user_id`, `level` (1-10), `notes`, `created_at`)
- **journal_entries**: writing logs (`id`, `user_id`, `content`, `created_at`)
- **ai_conversations**: chat threads (`id`, `user_id`, `messages` (JSONB), `memory` (JSONB), `summary`, `created_at`)
- **morning_rituals**: checklist status (`id`, `user_id`, `completed`, `created_at`)
- **wind_down_rituals**: checklist status (`id`, `user_id`, `completed`, `created_at`)

### Phase 2 Tables (10)
- **emotion_insights**: tracking aggregated trends (`id`, `user_id`, `emotion`, `frequency`, `trend`, `last_appeared`)
- **advice_effectiveness**: feedback metrics (`id`, `user_id`, `conversation_id`, `advice_given`, `help_rating` (1-3))
- **conversation_themes**: theme tagging (`id`, `user_id`, `conversation_id`, `theme`, `mentioned_emotions` (JSONB))
- **user_personality**: learned characteristics (`id`, `user_id`, `communication_style`, `preference_advice_type`)
- **proactive_checkins**: automated prompts (`id`, `user_id`, `scheduled_time`, `reason`, `actual_response`)
- **recovery_data**: mood dips and recovery tracking (`id`, `user_id`, `mood_dip_date`, `lowest_level`, `recovery_days`)
- **engagement_metrics**: usability tracking (`id`, `user_id`, `conversation_id`, `user_response_time`, `suggestion_followed`)
- **crisis_flags**: safety metrics (`id`, `user_id`, `conversation_id`, `severity_level` (1-4), `red_flags_detected` (JSONB))
- **push_notification_tokens**: FCM credentials (`id`, `user_id`, `device_token`, `is_active`)
- **password_reset_tokens**: password reset tracking (`id`, `user_id`, `token`, `expires_at`)

### Phase 3 & 4 (CIE / PKG) Tables (10)
- **daily_discoveries**: daily AI insights (`id`, `user_id`, `insight`, `category`, `confidence`, `created_at`)
- **relationship_memories**: entities & patterns extracted (`id`, `user_id`, `title`, `type`, `importance`, `confidence`, `related_journal`, `related_mood`, `first_occurrence`, `last_occurrence`, `times_referenced`, `supporting_evidence` (JSONB))
- **timeline_events**: search cache (`id`, `user_id`, `event_type`, `source_id`, `event_date`, `event_ts`, `title`, `summary`, `emotion`, `mood_level`, `search_text`, `embedding` (vector(1536)), `metadata` (JSONB))
- **user_predictions**: behavioral predictions (`id`, `user_id`, `type`, `prediction_text`, `target_date`, `probability`, `is_correct`, `feedback_text`, `created_at`)
- **user_knowledge_nodes**: personal knowledge atoms (`id`, `user_id`, `label`, `node_type`, `canonical_label`, `confidence`, `importance`, `valence`, `mention_count`, `first_seen_at`, `last_seen_at`, `embedding` (vector(1536)), `source_reason`, `is_confirmed`, `is_archived`, `metadata` (JSONB))
- **user_knowledge_edges**: PKG semantic connections (`id`, `user_id`, `source_node_id`, `target_node_id`, `edge_type`, `weight`, `evidence_count`, `last_reinforced_at`, `metadata` (JSONB))
- **user_life_chapters**: chronological user eras (`id`, `user_id`, `title`, `chapter_number`, `start_date`, `end_date`, `is_current`, `theme_summary`, `dominant_emotion`, `mood_average`, `growth_score`, `key_events` (JSONB), `dominant_themes`, `goals_started`, `goals_achieved`, `node_ids`)
- **user_behavioral_patterns**: detected cycles (`id`, `user_id`, `pattern_type`, `confidence`, `strength`, `occurrence_stats` (JSONB), `last_detected_at`)
- **user_goal_threads**: goal status (`id`, `user_id`, `target_node_label`, `status`, `started_at`, `completed_at`, `linked_node_ids`)
- **user_growth_metrics**: 10-dimensional metric logs (`id`, `user_id`, `dimension`, `score`, `growth_rate`, `evidence_count`, `updated_at`)

---

## 🔌 API Endpoints

### Auth Routes
- `POST /api/auth/signup`: Register user
- `POST /api/auth/login`: Login user
- `POST /api/auth/forgot-password`: Send reset email
- `POST /api/auth/reset-password`: Reset password with token
- `POST /api/auth/verify-age`: Age verification (18+)
- `POST /api/auth/privacy-accepted`: Privacy policy acceptance
- `GET /api/auth/check-age-verified`: Check if user is 18+
- `GET /health`: Health check endpoint

### Mood Routes
- `POST /api/mood`: Create mood log
- `GET /api/mood?range=7d|30d`: Get mood logs
- `GET /api/mood/trends`: Get emotion trends

### Journal Routes
- `POST /api/journal`: Create journal entry
- `GET /api/journal`: Get user's journals

### Ritual Routes
- `POST /api/rituals/morning`: Complete morning ritual
- `POST /api/rituals/winddown`: Complete wind down ritual
- `GET /api/rituals`: Get ritual status
- `GET /api/rituals/morning/prompt`: Get dynamic personalized morning routine anchor focus
- `GET /api/rituals/winddown/prompt`: Get dynamic personalized evening release focus

### ARIA / Search Routes
- `POST /api/ai/chat`: Send message to ARIA
- `POST /api/ai/journal-reflection`: Get reflection on journal
- `POST /api/ai/mood-analysis`: Analyze mood trends
- `POST /api/ai/remember-context`: Store memory
- `GET /api/ai/memory`: Retrieve memory
- `POST /api/ai/timeline/rebuild`: Rebuild timeline events cache for user
- `GET /api/ai/timeline`: Retrieve paginated timeline events for user
- `GET /api/ai/search`: Hybrid semantic + keyword + recency search
- `GET /api/ai/search/suggestions`: Get 6 dynamic example search queries
- `POST /api/ai/embeddings/generate`: Trigger bulk embedding generation

### Compounding Intelligence Engine (CIE) Routes
- `POST /api/aria/knowledge/process`: Process and extract nodes/edges from text
- `GET /api/aria/knowledge/graph`: Get full PKG (nodes and edges) for user
- `GET /api/aria/knowledge/context`: Get formatted context packet for LLM injection
- `GET /api/aria/knowledge/growth`: Get 10-dimensional user growth metrics
- `DELETE /api/aria/knowledge/nodes/{node_id}`: Delete node from PKG
- `GET /api/aria/knowledge/chapters`: Get list of detected life chapters
- `PATCH /api/aria/knowledge/nodes/{node_id}`: Update knowledge node fields (archive, label, valence)
- `GET /api/aria/knowledge/comparison`: Get chapter-over-chapter growth comparison

### Notification Routes
- `POST /api/notifications/register-device`: Register FCM token
- `POST /api/notifications/test`: Test notification

### User Routes
- `GET /api/user/me`: Get current user
- `GET /api/user/export-data`: Download all user data (GDPR)
- `DELETE /api/user/delete-account`: Delete account permanently

### Payment Routes
- `POST /api/payments/create-subscription`: Start subscription

---

## 🎨 Frontend Pages
- `/login`: Login page
- `/signup`: Signup page
- `/reset?token=xxx`: Password reset
- `/dashboard`: Main dashboard (protected, includes redesigned hero section)
- `/morning`: Morning ritual
- `/mood`: Mood tracker
- `/journal`: Guided journal
- `/aria`: ARIA chat
- `/wind-down`: Evening ritual
- `/settings`: User settings
- `/privacy`: Privacy policy
- `/timeline`: Interactive historical timeline with hybrid search
- `/understanding`: CIE growth dashboard (life chapters, PKG graph view, cross-chapter comparison metrics)

---

## 🤖 Compounding Intelligence Engine (CIE) Summary
MindCradle is built on a custom **Compounding Intelligence Engine** that builds a **Personal Knowledge Graph (PKG)** for each user based on their journals, mood logs, and interactions.
1. **Extract**: A background pipeline extracts nodes (coping strategies, goals, stressors) and edges (triggers, causes) from user data.
2. **Synthesize**: Evaluates life chapters (periods of life like "Finding My Rhythm") and behavioral patterns (e.g. Sunday dread).
3. **Personalize**:
   - Dynamic focus prompts in morning rituals.
   - Dynamic let-go prompts in wind-down rituals.
   - Chronological life chapters forming the narrative of solstice review letters.
   - Pattern-aware notification hours.
   - PKG-integrated predictions (alerting users of impending dread cycles).
   - Cross-chapter growth comparisons.

---

## ⚠️ Key Guardrails
- **Age verification**: 18+ gate before ARIA access.
- **Crisis detection**: Keywords trigger escalation to 988/Crisis Text Line.
- **Off-topic blocking**: Non-wellness questions rejected.
- **Privacy**: GDPR compliance, data export, account deletion, and strict PostgreSQL Row Level Security (RLS).
- **Medical disclaimer**: Not a replacement for therapy.
