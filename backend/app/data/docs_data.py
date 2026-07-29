DOCS_PAGES = [
    {
        "slug": "introduction",
        "title": "Introduction to MindCradle",
        "category": "Getting Started",
        "order": 1,
        "content": """
# Introduction to MindCradle

Welcome to MindCradle, a premium self-awareness and wellness companion designed to help you track your emotional well-being, establish mindful habits, and reflect on your days with a secure, relational AI companion named ARIA. 

MindCradle provides a holistic ecosystem that combines quantitative metric tracking (mood score, sleep duration, energy level) with qualitative self-reflection (guided journals and chat logs). This system helps users cultivate emotional awareness and establish consistent wellness rituals.

## What makes MindCradle different?

Unlike generic wellness applications that track isolated metrics (like counting steps or logging mood levels on a flat list), MindCradle is powered by a custom **Compounding Intelligence Engine (CIE)**. 

The CIE is designed to become smarter and more contextually aware about one specific person: **you**. By parsing your text reflections into a graph structure, MindCradle connects different areas of your life—such as how work stress affects sleep quality, or which specific grounding exercises improve emotional recovery scores. This creates a deeply personalized wellness environment.

## Key Features

- **The Personal Knowledge Graph (PKG)**: A secure database that structures your emotional triggers, stressors, and coping strategies over time. Rather than storing flat text logs, the system creates structured relationships.
- **Relational AI Companion (ARIA)**: A warm, validating companion with longitudinal relational memory who notices patterns in your reflections. ARIA leverages your active PKG to ground conversations in your lived experiences.
- **Guided Daily Rituals**: Integrated morning focus and evening wind-down rituals to anchor your day. These rituals help build daily habits and track consistency streaks.
- **Hybrid Semantic Search**: A pgvector-based search engine allowing you to query all your history using natural language. Ask questions like *"When was the last time I felt calm at work?"* or *"What did I do to manage anxiety last month?"*

## Navigating the Docs

To understand how MindCradle works under the hood, explore the following sections:
- Learn about our core data structure in the [Memory Protocol](/docs/memory-protocol).
- Explore the API schemas and requests in the [API Reference](/docs/api).
- Learn how we safeguard your personal data in [Security & Privacy](/docs/security).
- Understand our multi-layered backend setup in [System Architecture](/docs/architecture).
- Find answers to common technical queries in the [Frequently Asked Questions](/docs/faq).
""",
        "modified_at": "2026-07-01T09:00:00Z"
    },
    {
        "slug": "memory-protocol",
        "title": "The Memory Protocol",
        "category": "Core Concepts",
        "order": 2,
        "content": """
# The Memory Protocol

The **Memory Protocol** is our proprietary data pipeline that extracts, structures, and prunes long-term context from your logs to feed our relational AI companion, ARIA.

## Why a Memory Protocol?

Large Language Models (LLMs) are stateless. To simulate memory, standard applications typically send your entire chat history with every prompt. However, this is token-heavy, costly, and lacks cognitive structure. It leads to context drift and makes it impossible for an AI companion to recall patterns over months or years.

The Memory Protocol solves this by parsing your daily reflections into a **Personal Knowledge Graph (PKG)**. This structures your experiences as nodes (e.g. entities, events, habits) and edges (relationships).

## How it works

The pipeline runs in four stages:

1. **Entity Extraction**: When you save a journal entry or mood check-in, the system parses the text for entities (e.g. `Work`, `Sleep`, `Yoga`) and emotional states.
2. **Relationship Mapping**: The system draws links (edges) between these entities (e.g., `Yoga` -> `mitigates` -> `Anxiety`).
3. **Graph De-duplication**: The new nodes are merged with your existing graph to avoid duplicates, updating the weight of active nodes.
4. **Context Synthesis**: When you chat with ARIA, the system fetches your active graph nodes and summarizes your current "life chapter" in the prompt, allowing ARIA to reference your habits naturally.

```
 [User Log] ──> (Entity Extraction) ──> [New Nodes: Sleep, Stress]
                                                 │
                                                 ▼
 [Updated Graph] <── (De-duplication) <── (Relationship Mapping)
       │
       ▼
 [Context Synthesizer] ──> (Injects Life Chapter) ──> [ARIA Chat Model]
```

## Node Weighting & Decaying

To prevent the graph from becoming cluttered, every edge and node has a weight from 1 to 10. Every time a relationship is confirmed or logged, its weight increases. Conversely, we apply a time-based decay formula:

$$W_{new} = W_{old} \\times e^{-\\lambda t}$$

Where:
- $W$ is the node/relationship weight.
- $\\lambda$ is the decay constant (defaults to $0.05$ per day).
- $t$ is the elapsed time in days since the last reference.

Nodes with weights falling below a threshold of $1.5$ are pruned from the active prompt context, ensuring ARIA focuses on your active life themes while archiving older chapters.
""",
        "modified_at": "2026-07-02T10:00:00Z"
    },
    {
        "slug": "api",
        "title": "API Reference",
        "category": "Developers",
        "order": 3,
        "content": """
# API Reference

MindCradle provides a secure REST API for clients to perform authentication, log reflections, retrieve daily insights, and query personal knowledge graphs.

## Authentication

All authenticated routes require forwarding the Supabase access token in the authorization headers. Requests without a valid JWT will receive a 401 Unauthorized status.

```http
Authorization: Bearer <your_supabase_jwt_token>
```

---

## Endpoints

### 1. Mood Check-ins
- **POST `/api/mood`**: Submit a new mood level and energy reflection.
- **GET `/api/mood/history`**: Retrieve your historical mood logs.

#### Sample Request Payload (POST `/api/mood`)
```json
{
  "mood_score": 8,
  "energy_level": 7,
  "triggers": ["sleep", "work-completed"],
  "note": "Felt very productive today after getting 8 hours of solid sleep."
}
```

#### Sample Response Payload
```json
{
  "id": "e94c92a2-83b1-417d-8153-73932e6a3281",
  "user_id": "8b7cf8a2-d9d1-4e4b-9fb2-371de2e76f5b",
  "mood_score": 8,
  "energy_level": 7,
  "created_at": "2026-07-30T00:52:10Z"
}
```

---

### 2. Search Suggestions
- **GET `/api/ai/search/suggestions`**: Returns a list of default or personalized example queries to run against your history. (This is a public endpoint).

---

### 3. AI Insights
- **POST `/api/ai/chat`**: Send a message to ARIA and receive a relational response grounded in your knowledge graph context.

#### Sample Request Payload
```json
{
  "message": "I'm feeling really anxious about my team presentation tomorrow."
}
```

#### Sample Response Payload
```json
{
  "reply": "I remember you felt similar anxiety before the marketing launch on June 12, but you noted it resolved within 24 hours. Would you like to try the mindfulness breathing exercise that helped you then?",
  "detected_entities": ["presentation", "anxiety"],
  "updated_nodes": 1
}
```

- **GET `/api/ai/insight`**: Get a brief daily summary of your self-awareness patterns and recurring themes.

---

### 4. User Settings & Exports
- **GET `/api/user/export`**: Requests a complete download of your personal knowledge graph and timeline records in JSON format.
- **DELETE `/api/user/account`**: Permanently deletes your account and cascades all associated data.

#### Sample Export Response Payload
```json
{
  "export_date": "2026-07-30T00:52:10Z",
  "user_id": "8b7cf8a2-d9d1-4e4b-9fb2-371de2e76f5b",
  "mood_logs_count": 47,
  "journal_entries_count": 28,
  "graph_nodes_count": 12
}
```
""",
        "modified_at": "2026-07-03T11:00:00Z"
    },
    {
        "slug": "security",
        "title": "Security & Privacy",
        "category": "Core Concepts",
        "order": 4,
        "content": """
# Security & Privacy

Privacy is the foundation of MindCradle. Because you trust our application with your daily thoughts and reflections, we design our database and AI architecture around data segregation and cryptographic validation.

## Supabase JWT Verification

All requests are validated in the backend using the project's **Supabase JWT Secret**.
- The token contains your user UUID (`sub` claim) along with expiry and audience constraints.
- Every database query in our FastAPI router enforces strict isolation by filtering queries using this verified user UUID, preventing cross-tenant data leaks.
- We never log raw token payloads or store credentials in cleartext.

## Row Level Security (RLS)

Our PostgreSQL database on Supabase enforces Row Level Security at the database level. Even if a backend query is written incorrectly, the database itself rejects operations that attempt to read or write rows belonging to other users.

```sql
CREATE POLICY "Users can manage their own journal entries" 
ON public.journal_entries
FOR ALL USING (auth.uid() = user_id) 
WITH CHECK (auth.uid() = user_id);
```

## AI Data Safeguards

When we send context to our language models via the OpenRouter API:
- We do not transmit your email, real name, or billing details.
- Context is structured as anonymized nodes (e.g. "User experiences work fatigue").
- Data transmitted is subject to zero data retention policies of the endpoint providers. Your reflections are never stored on external AI servers and are never used to train public language models.

## User Control & GDPR Compliance

We support full GDPR compliance and data sovereignty:
- **Data Export**: Export your complete timeline, mood logs, and knowledge graph in a structured JSON format at any time.
- **Account Deletion**: Delete your account in one click. Doing so triggers a database cascade that completely wipes your user history, credentials, vector embeddings, and knowledge graph nodes from our database.
""",
        "modified_at": "2026-07-04T12:00:00Z"
    },
    {
        "slug": "architecture",
        "title": "System Architecture",
        "category": "Core Concepts",
        "order": 5,
        "content": """
# System Architecture

MindCradle is built on a modern, decoupled, and stateless cloud architecture. The system is split into three independent layers to ensure high availability, fast response times, and robust security.

```
+--------------------+        Vercel Reverse Proxy        +--------------------+
|  Vite React SPA    | ─────────────────────────────────> |   FastAPI Server   |
| (www.mindcradle)   | <─ (HTTPS / CORS / SameSite=None)  | (Google Cloud Run) |
+--------------------+                                    +--------------------+
                                                                    │
                                                                    ▼
                                                          +--------------------+
                                                          |  Supabase Database |
                                                          |    (PostgreSQL)    |
                                                          +--------------------+
```

## Frontend

- **Framework**: React 18, Vite, Tailwind CSS v4, and React Router.
- **Hosting**: Vercel Edge.
- **Routing**: Client-side routing is handled via React Router. Relative `/api` requests are proxied dynamically to Cloud Run backend servers via Vercel configuration routes, preventing CORS issues.

## Backend

- **Framework**: FastAPI (Python 3.11) served by Uvicorn.
- **Hosting**: Google Cloud Run (stateless container instance) with automatic scaling policies.
- **AI Engine**: Connects to OpenRouter for model execution and OpenAI for generating text embeddings. We implement asynchronous request queueing to keep response latencies minimal during peak traffic.

## Database

- **Provider**: Supabase PostgreSQL.
- **Extensions**: `pgvector` for storing and performing cosine similarity searches on journal embeddings.
- **Vector Search**: Journal entries are processed using the text-embedding-3-small model. The resulting 1536-dimension vectors are indexed using HNSW indexes to allow sub-millisecond semantic search queries over years of text history.

### Connection Pooling & Routing
We utilize connection pooling via Supabase connection pools to manage database connections efficiently, handling hundreds of concurrent users without query latency spikes. FastAPI maintains an active pool targeting our Supabase PostgreSQL instance. This design prevents database scaling limits and ensures optimal latency profiles for read and write queries. Our API router invokes OpenRouter with strict request timeouts. Conversations are processed asynchronously to ensure that temporary downstream latency from language models does not block the core API event loops.
""",
        "modified_at": "2026-07-05T13:00:00Z"
    },
    {
        "slug": "faq",
        "title": "Frequently Asked Questions",
        "category": "Getting Started",
        "order": 6,
        "content": """
# Frequently Asked Questions

Find answers to common technical and wellness questions about MindCradle.

### Is ARIA a licensed therapist?

No. ARIA is a supportive, validating AI companion. She is designed to encourage self-reflection and help you identify daily rhythm patterns. She is not a replacement for clinical therapy, psychiatric treatment, or crisis counseling. If you are in distress, please refer to our crisis support resources or call 988.

### How does the streak counter work?

Your streak represents the number of unique calendar days you have interacted with the application (mood checks, journal entries, or daily routines) in the last week. The counter resets if there is a gap of more than 3 days of total inactivity, encouraging users to maintain consistent micro-routines.

### Can I run MindCradle offline?

Yes! MindCradle is configured as a **Progressive Web App (PWA)**. Once installed on your phone or desktop, it caches essential page layouts and operates offline, storing your journal logs locally in IndexedDB. Once your connection is restored, the client automatically synchronizes your logs with the cloud database.

### What data format is used for export?

When you export your data, you receive a ZIP file containing your complete history in JSON format. This includes your mood entries, journal logs, and structured relationship graphs. The schemas are fully documented, allowing you to import your personal knowledge graph into other semantic desktop database systems like Obsidian or logseq.

### How does rate limiting work?

To maintain API stability, we implement a Token Bucket rate limiting algorithm. Free users are limited to 60 API requests per hour and 5 ARIA chat messages per day. Premium users have elevated thresholds of 600 requests per hour and unlimited ARIA chat messages.

### Is there a desktop or mobile application available?

Yes. While we host the platform at mindcradle.online, the frontend is built entirely as a Progressive Web App (PWA). You can install it on iOS via 'Add to Home Screen' in Safari, or on Android and Desktop via the browser install prompt. This runs the app in a standalone window, enables offline database features, and ensures smooth performance.
""" ,
        "modified_at": "2026-07-06T14:00:00Z"
    }
]
