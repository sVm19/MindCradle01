# MindCradle — Developer & AI Bot Reference (BRAIN.md)

This document contains a structured breakdown of the MindCradle application architecture, database schemas, router mappings, frontend pages, and core services. It is designed to help AI coding assistants quickly locate files and understand the boundaries of the codebase.

---

## 🎯 1. Project Metadata
*   **Aesthetic Vibe**: Earthy & Grounding (Forest Mist background `#070c09` + Amber/Gold highlights `#fbbf24`).
*   **Payment Model**: Freemium (Free vs. Premium at $9.99/month, gated by `is_premium` status).
*   **Database Engine**: PostgreSQL (managed via Supabase) with RLS enabled.
*   **Primary AI Engine**: OpenRouter using Gemini 3.5 Flash Lite (`google/gemini-3.5-flash-lite`) + OpenAI `text-embedding-3-small` embeddings.

---

## 📂 2. Directory Mappings
This section lists where key source code layers live:

```text
d:\WorkSpace\mindcradle\
├── backend/
│   ├── app/
│   │   ├── main.py              # Backend entrypoint (FastAPI app setup & CORS)
│   │   ├── config.py            # Environment settings & credentials fallbacks
│   │   ├── models/
│   │   │   └── schemas.py       # SQLModel/SQLAlchemy schemas & validation models
│   │   ├── routers/             # API Router endpoints
│   │   └── services/            # CIE engines, OpenRouter client, database handlers
│   └── scripts/                 # Utility scripts & migrations
└── frontend/
    ├── src/
    │   ├── main.tsx             # Frontend entrypoint
    │   ├── app/
    │   │   ├── App.tsx          # React Router definition & layouts
    │   │   ├── components/      # Shared components (Sidebar, SEO, AriaTerminalCard)
    │   │   └── pages/           # Page components
    │   ├── lib/
    │   │   ├── api.ts           # Unified API wrapper client (Pocketbase/Supabase fallback)
    │   │   ├── auth.tsx         # Auth contexts & session validation hooks
    │   │   └── mixpanel.ts      # Mixpanel event tracking wrappers
    │   └── styles/
    │       ├── theme.css        # Visual styles (Forest Mist & Amber CSS tokens)
    │       └── index.css        # Global CSS imports
```

---

## 🗄️ 3. Database Schema Mappings
MindCradle uses 26 database tables. Here is their semantic division and corresponding model representations in [`backend/app/models/schemas.py`](file:///d:/WorkSpace/mindcradle/backend/app/models/schemas.py):

| Table Name | Schema class / Representation | Key Fields & Purpose |
| :--- | :--- | :--- |
| **users** | `User` | Main identity tracker: `id`, `email`, `privacy_accepted`, `age_verified`, `is_premium`. |
| **mood_logs** | `MoodLog` | Daily wellness check-in scores: `level` (1-10), `notes`. |
| **journal_entries** | `JournalEntry` | Reflective user journal texts: `content`. |
| **morning_rituals** | `MorningRitual` | Morning checklist status tracker. |
| **wind_down_rituals** | `WindDownRitual` | Wind down evening checklist status tracker. |
| **ai_conversations** | `AIConversation` | Chat threads with ARIA companion: `messages` (JSONB), `summary`. |
| **daily_discoveries** | `DailyDiscovery` | Generated daily patterns and wellness advice. |
| **user_knowledge_nodes** | `UserKnowledgeNode` | Personal Knowledge Graph atoms: `label`, `canonical_label`, `valence`. |
| **user_knowledge_edges** | `UserKnowledgeEdge` | Semantic connections between nodes: `source_node_id`, `target_node_id`, `weight`. |
| **user_life_chapters** | `UserLifeChapter` | Chronological wellness eras: `title`, `theme_summary`, `mood_average`. |
| **user_behavioral_patterns**| `UserBehavioralPattern` | Detected cycles (e.g. Sunday dread): `pattern_type`, `strength`. |
| **user_predictions** | `UserPrediction` | Behavioral predictions: `prediction_text`, `probability`. |
| **user_goal_threads** | `UserGoalThread` | Habits and wellness goals: `status`, `linked_node_ids`. |
| **user_growth_metrics** | `UserGrowthMetric` | 10-dimensional metric scores. |
| **push_notification_tokens**| `PushNotificationToken` | FCM credentials tracker. |

---

## 🔌 4. API Endpoints & Routers Mappings
All API routes are prefixed by `/api`. The endpoint logic is mapped as follows:

### Auth Endpoints &rarr; [`app/routers/auth.py`](file:///d:/WorkSpace/mindcradle/backend/app/routers/auth.py)
*   `POST /api/auth/signup` &bull; `POST /api/auth/login` &bull; `POST /api/auth/forgot-password` &bull; `POST /api/auth/reset-password`
*   `POST /api/auth/verify-age` &bull; `POST /api/auth/privacy-accepted` &bull; `GET /api/auth/check-age-verified`

### Mood & Journal Endpoints &rarr; [`app/routers/mood.py`](file:///d:/WorkSpace/mindcradle/backend/app/routers/mood.py) & [`app/routers/journal.py`](file:///d:/WorkSpace/mindcradle/backend/app/routers/journal.py)
*   `POST /api/mood` (Create mood) &bull; `GET /api/mood` (Get mood history logs) &bull; `GET /api/mood/trends` (Trends)
*   `POST /api/journal` (Create journal) &bull; `GET /api/journal` (Get user's journals)

### Rituals Endpoints &rarr; [`app/routers/rituals.py`](file:///d:/WorkSpace/mindcradle/backend/app/routers/rituals.py)
*   `POST /api/rituals/morning` &bull; `POST /api/rituals/winddown`
*   `GET /api/rituals/morning/prompt` (Dynamic anchor prompt) &bull; `GET /api/rituals/winddown/prompt` (Dynamic release prompt)

### ARIA Companion & CIE Endpoints &rarr; [`app/routers/ai.py`](file:///d:/WorkSpace/mindcradle/backend/app/routers/ai.py) & [`app/routers/growth.py`](file:///d:/WorkSpace/mindcradle/backend/app/routers/growth.py)
*   `POST /api/ai/chat` (Send message to ARIA)
*   `POST /api/ai/journal-reflection` (Aria reflection on journal entry)
*   `GET /api/ai/timeline` (Interactive historical timeline) &bull; `GET /api/ai/search` (Hybrid semantic search)
*   `GET /api/aria/knowledge/graph` (PKG nodes/edges) &bull; `GET /api/aria/knowledge/chapters` (Life chapters list)
*   `GET /api/aria/knowledge/growth` (Growth scores) &bull; `PATCH /api/aria/knowledge/nodes/{node_id}` (Archive node)

### User & Payments Endpoints &rarr; [`app/routers/user.py`](file:///d:/WorkSpace/mindcradle/backend/app/routers/user.py) & [`app/routers/payments.py`](file:///d:/WorkSpace/mindcradle/backend/app/routers/payments.py)
*   `GET /api/user/me` &bull; `GET /api/user/export-data` (GDPR GDPR) &bull; `DELETE /api/user/delete-account`
*   `POST /api/payments/create-subscription` (Start Creem checkout session)

---

## 🎨 5. Frontend Pages & Page Component Mappings
React Router routes are defined inside [`frontend/src/app/App.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/App.tsx).

*   `/login` &rarr; [`Login.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Login.tsx) (Email login / magic links)
*   `/signup` &rarr; [`MagicLinkRequest.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/MagicLinkRequest.tsx) (Signup request flow)
*   `/dashboard` &rarr; [`Dashboard.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Dashboard.tsx) (Personal wellness hub feed & quick journaling)
*   `/morning` &rarr; [`Morning.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Morning.tsx) (Guided morning routine anchor checklist)
*   `/mood` &rarr; [`Mood.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Mood.tsx) (Emotion tracker logs & insights comparison)
*   `/journal` &rarr; [`Journal.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Journal.tsx) (Rich-text prompt guided journaling)
*   `/aria` &rarr; [`ARIA.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/ARIA.tsx) (Direct chat thread companion UI)
*   `/timeline` &rarr; [`Timeline.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Timeline.tsx) (Interactive hybrid wellness feed history)
*   `/understanding` &rarr; [`Understanding.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Understanding.tsx) (PKG node-link map & life chapters timeline view)
*   `/settings` &rarr; [`Settings.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Settings.tsx) (Preferences configuration, disabled widget gating)
*   `/settings/widgets` &rarr; [`WidgetGallery.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/WidgetGallery.tsx) (Gated Home Screen Widgets selection & instructions)
*   `/pricing` &rarr; [`Pricing.tsx`](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Pricing.tsx) (Subscription tier comparison, lists home-screen widgets)

---

## 🛠️ 6. Core Business Services
Key logic components in backend services directory [`backend/app/services/`](file:///d:/WorkSpace/mindcradle/backend/app/services/):

*   **Supabase Database Operations & RLS** &rarr; [`supabase.py`](file:///d:/WorkSpace/mindcradle/backend/app/services/supabase.py)
    *   Handles all client DB connections, queries, writes, and RLS contexts.
*   **OpenRouter AI client configuration** &rarr; [`openrouter_ai.py`](file:///d:/WorkSpace/mindcradle/backend/app/services/openrouter_ai.py)
    *   Builds prompt completions using the configured Gemma-4 model.
*   **Embeddings Generation** &rarr; [`embeddings.py`](file:///d:/WorkSpace/mindcradle/backend/app/services/embeddings.py)
    *   Generates 1536-dimensional vectors for semantic search index queries.
*   **Knowledge Graph Extraction Engine** &rarr; [`knowledge_graph.py`](file:///d:/WorkSpace/mindcradle/backend/app/services/knowledge_graph.py)
    *   Extracts knowledge graph entities (nodes) and connections (edges) from user text reflections.
*   **Personal Growth Engine** &rarr; [`growth_engine.py`](file:///d:/WorkSpace/mindcradle/backend/app/services/growth_engine.py)
    *   Aggregates timeline events, chapters, comparison metrics, and growth scores.

---

## 🚫 7. Key App Guardrails
*   **Age-Verification Guard**: Requires age verified state check before enabling ARIA companion chat capabilities.
*   **Crisis Keywords Safety Hook**: Text messages matching critical self-harm flags automatically trigger emergency contact resources.
*   **Off-Topic Conversation filter**: ARIA filters and rejects requests that diverge significantly from personal wellness context.
