DOCS_PAGES = [
    {
        "slug": "introduction",
        "title": "Introduction to MindCradle",
        "category": "Getting Started",
        "order": 1,
        "content": """
# Introduction to MindCradle

Welcome to MindCradle, a premium self-awareness and wellness companion designed to help you track your emotional well-being, establish mindful habits, and reflect on your days with a secure, relational AI companion named ARIA.

## What makes MindCradle different?

Unlike generic wellness applications that track isolated metrics (like counting steps or logging mood levels on a flat list), MindCradle is powered by a custom **Compounding Intelligence Engine (CIE)**. 

The CIE is designed to become smarter and more contextually aware about one specific person: **you**.

## Key Features

- **The Personal Knowledge Graph (PKG)**: A secure database that structures your emotional triggers, stressors, and coping strategies over time.
- **Relational AI Companion (ARIA)**: A warm, validating companion with longitudinal relational memory who notices patterns in your reflections.
- **Guided Daily Routines**: Integrated morning focus and evening wind-down rituals to anchor your day.
- **Hybrid Semantic Search**: A pgvector-based search engine allowing you to query all your history using natural language.

## Navigating the Docs

To understand how MindCradle works under the hood, explore the following sections:
- Learn about our core data structure in the [Memory Protocol](/docs/memory-protocol).
- Explore the API schemas and requests in the [API Reference](/docs/api).
- Learn how we safeguard your personal data in [Security & Privacy](/docs/security).
- Understand our multi-layered backend setup in [System Architecture](/docs/architecture).
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

Large Language Models (LLMs) are stateless. To simulate memory, standard applications typically send your entire chat history with every prompt. However, this is token-heavy, costly, and lacks cognitive structure.

The Memory Protocol solves this by parsing your daily reflections into a **Personal Knowledge Graph (PKG)**.

## How it works

The pipeline runs in four stages:

1. **Entity Extraction**: When you save a journal entry or mood check-in, the system parses the text for entities (e.g. `Work`, `Sleep`, `Yoga`) and emotional states.
2. **Relationship Mapping**: The system draws links (edges) between these entities (e.g., `Yoga` -> `improves` -> `Sleep Quality`).
3. **Graph De-duplication**: The new nodes are merged with your existing graph to avoid duplicates, updating the weight of active nodes.
4. **Context Synthesis**: When you chat with ARIA, the system fetches your active graph nodes and summarizes your current "life chapter" in the prompt, allowing ARIA to reference your habits naturally.

For more details on how these services are hosted, see [System Architecture](/docs/architecture).
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

All authenticated routes require forwarding the Supabase access token in the headers:

```http
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### 1. Mood Check-ins
- **POST `/api/mood`**: Submit a new mood level and energy reflection.
- **GET `/api/mood/history`**: Retrieve your historical mood logs.

### 2. Search Suggestions
- **GET `/api/ai/search/suggestions`**: Returns a list of default or personalized example queries to run against your history. (This is a public endpoint).

### 3. AI Insights
- **POST `/api/ai/chat`**: Send a message to ARIA and receive a relational response grounded in your knowledge graph.
- **GET `/api/ai/insight`**: Get a brief daily summary of your self-awareness patterns.

For more details on how these endpoints verify user identities, check out [Security & Privacy](/docs/security).
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
- The token contains your user UUID (`sub` claim).
- Every database query is isolated by your user ID, preventing cross-tenant data leaks.
- We never log raw token payloads.

## AI Data Safeguards

When we send context to our language models via the OpenRouter API:
- We do not send your email, real name, or billing details.
- Context is structured as anonymized nodes (e.g. "User experiences work fatigue").
- Data transmitted is subject to zero data retention policies of the endpoint providers, meaning your reflections are never used to train global AI models.

## User Control

We support full GDPR compliance:
- **Data Export**: Export your complete timeline, mood logs, and knowledge graph in JSON format.
- **Account Deletion**: Delete your account in one click. Doing so triggers a database cascade that completely wipes your user history, credentials, and knowledge graph.
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

MindCradle is built on a modern, decoupled, and stateless cloud architecture.

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
- **Routing**: Relative `/api` requests rewrote to Cloud Run dynamically via Vercel configurations.

## Backend
- **Framework**: FastAPI (Python 3.11) served by Uvicorn.
- **Hosting**: Google Cloud Run (stateless container instance).
- **AI Engine**: Connects to OpenRouter for model execution and OpenAI for text embeddings.

## Database
- **Provider**: Supabase PostgreSQL.
- **Extensions**: `pgvector` for storing and performing cosine similarity searches on journal embeddings.
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
Your streak represents the number of unique calendar days you have interacted with the application (mood checks, journal entries, or daily routines) in the last week.

### Can I run MindCradle offline?
Yes! MindCradle is configured as a **Progressive Web App (PWA)**. Once installed on your phone or desktop, it caches essential page layouts and operates offline, syncing your logs once connection is restored.
""" ,
        "modified_at": "2026-07-06T14:00:00Z"
    }
]
