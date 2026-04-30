# Project Context

## Status

- Intended task: read the workspace and save reusable context to Mem.
- Mem plugin is listed in the environment, but no usable MCP server or resource template is exposed in this session.
- Fallback used: this file stores the durable project summary locally.

## Workspace Overview

This workspace contains four main areas:

1. `backend/`
   FastAPI backend for "MindCradle".
2. `frontend/`
   Next.js App Router frontend for the same product.
3. `pocketbase/`
   PocketBase binary, migrations, and local data files.
4. `caveman/`
   A separate plugin/skill repository for terse agent communication and memory compression.

This means the folder is a multi-project workspace, not a single app-only repo.

## Product: MindCradle

The main product appears to be a mental wellness dashboard with:

- auth
- resource browsing
- mood tracking
- guided journaling
- an AI wellness assistant

The frontend talks to the FastAPI backend, which delegates persistence to PocketBase and AI generation to NVIDIA's OpenAI-compatible chat endpoint.

## Top-Level Runtime Flow

1. User opens the Next.js app in `frontend/`.
2. Client components call helper functions in `frontend/lib/api.ts`.
3. Those helpers hit FastAPI routes under `/api/*`.
4. FastAPI routers are thin and mostly forward work to:
   - PocketBase REST via `backend/app/services/pocketbase.py`
   - NVIDIA AI via `backend/app/services/nvidia_ai.py`
5. PocketBase stores users, resources, mood logs, journal entries, and AI conversation records.

## Backend

### Entry Points

- `backend/pyproject.toml`
  Python 3.11+, FastAPI, Uvicorn, httpx, pydantic, dotenv.
- `backend/app/main.py`
  Creates the FastAPI app, configures CORS, mounts routers, exposes `/api/health`.
- `backend/app/config.py`
  Loads env vars for PocketBase URL, NVIDIA API settings, and frontend URL.

### Data Contracts

`backend/app/models/schemas.py` defines:

- auth request/response models
- `ResourceCategory`
- mood payloads
- journal payloads
- AI chat/recommendation payloads

### Services

- `backend/app/services/pocketbase.py`
  Async HTTP wrapper around PocketBase REST endpoints.
  Handles auth, list/get/create/update/delete.
- `backend/app/services/nvidia_ai.py`
  Uses the OpenAI SDK against NVIDIA's API base URL.
  Sets a system prompt for a short, supportive assistant called "Calm Guide".
  Supports normal and streaming completions, plus recommendation generation.

### Routers

- `backend/app/routers/auth.py`
  Login and signup against PocketBase. `/me` is stubbed and says auth middleware is pending.
- `backend/app/routers/resources.py`
  Public list/detail endpoints for resources.
- `backend/app/routers/mood.py`
  Save and fetch mood logs. Uses auth header forwarding to PocketBase.
- `backend/app/routers/journal.py`
  Save and fetch journal entries. Also forwards auth header.
- `backend/app/routers/ai.py`
  Non-streaming chat, SSE streaming chat, and recommendations.

### Backend Observations

- Router layer is intentionally thin.
- No real backend auth middleware yet; the frontend stores raw auth token in `localStorage`.
- AI chat does not currently persist conversation history, even though PocketBase has an `ai_conversations` collection.
- `authorization` headers are accepted in several routes but not interpreted beyond forwarding.

## Frontend

### Stack

- Next.js `16.2.4`
- React `19.2.4`
- TypeScript
- Tailwind CSS v4
- React Compiler enabled in `frontend/next.config.ts`

### Core Files

- `frontend/app/layout.tsx`
  Global metadata, fonts, and Material Symbols include.
- `frontend/app/page.tsx`
  Landing page with particle background and CTA links.
- `frontend/app/dashboard/layout.tsx`
  Shared dashboard shell with persistent particle background and header.
- `frontend/app/dashboard/page.tsx`
  Composes the hero section and resource grid.
- `frontend/app/globals.css`
  Dark glassmorphism theme, animations, skeletons, scrollbar styling.

### API Layer

`frontend/lib/api.ts` is the main frontend integration point:

- reads `NEXT_PUBLIC_API_URL`
- attaches `Authorization` from `localStorage`
- exposes helpers for login, signup, resources, mood, journal, and AI chat

### Static Data

`frontend/lib/data.ts` includes:

- a 24-card fallback resource list
- dashboard navigation links

The resources list is intended as a fallback or seed-aligned client model, not the long-term source of truth.

### Main UI Areas

- `frontend/app/auth/login/page.tsx`
  Login form, writes auth token/name/email to `localStorage`, redirects to dashboard.
- `frontend/app/auth/signup/page.tsx`
  Signup form with the same client-side storage flow.
- `frontend/app/dashboard/mood/page.tsx`
  Client-side mood logger with optimistic local history and backend sync attempt.
- `frontend/app/dashboard/journal/page.tsx`
  Guided journaling UI with random prompt selection and local history fallback.
- `frontend/app/dashboard/assistant/page.tsx`
  Simple chat UI that calls backend AI chat and renders assistant replies.

### Shared Components

- `frontend/components/layout/TopHeader.tsx`
  Desktop/mobile navigation.
- `frontend/components/hero/HeroSection.tsx`
  Intro text, start button, and typewriter greeting using auth state.
- `frontend/components/resources/ResourceGrid.tsx`
  Tries live API first, falls back to local resource cards if backend is unavailable.
- `frontend/components/resources/ResourceCard.tsx`
  Card renderer for resource items.
- `frontend/components/ui/ParticleCanvas.tsx`
  Full-screen animated particle background.

### Frontend Observations

- The app is heavily client-side and uses `localStorage` as the auth/session layer.
- Resource browsing degrades gracefully if backend/API is down.
- Mood and journal screens keep in-memory local history for the current session only.
- Assistant page currently uses non-streaming chat helper even though the backend exposes a streaming endpoint.

## PocketBase

### Role

PocketBase is the persistence layer for the MindCradle app.

### Workspace Contents

- `pocketbase/pocketbase.exe`
  Local PocketBase binary.
- `pocketbase/pb_migrations/`
  Collection creation/update migrations.
- `pocketbase/pb_data/`
  Local database files and generated TypeScript typings.

### Collections Seen

From migrations and setup scripts, the intended collections are:

- `resources`
- `mood_logs`
- `journal_entries`
- `ai_conversations`

### Migration Shape

- Early migration creates `resources` with only the system id field.
- Later migration adds resource fields:
  - `title`
  - `description`
  - `icon`
  - `color_class`
  - `category`
  - `order`
  - `url`
  - `is_active`

### Setup and Repair Scripts

- `backend/setup_pocketbase.py`
  One-time collection creation and seeding script.
- `backend/fix_pocketbase.py`
  Repair script for PocketBase v0.37+ field format differences.
- `backend/reseed.py`
  Deletes and recreates seeded resource records.
- `backend/debug_pb.py`
  Prints collection and sample record diagnostics.

### PocketBase Observations

- Setup evolved over time; there are repair/reseed scripts because earlier schema attempts were incomplete.
- PocketBase rules are intended to enforce per-user access for mood/journal/AI data.
- The current app architecture assumes PocketBase is already running locally on `127.0.0.1:8090`.

## Caveman Repo

`caveman/` looks like a separate embedded repo, not part of the MindCradle product runtime.

### Purpose

It provides skills/plugins for:

- terse "caveman" response style
- memory-file compression
- evals and benchmarks for token savings
- plugin packaging for several agent ecosystems

### Important Files Read

- `caveman/README.md`
  Main project overview and install docs.
- `caveman/caveman/SKILL.md`
  Defines terse caveman response rules.
- `caveman/caveman-compress/SKILL.md`
  Defines memory-file compression workflow.

### Interpretation

The `caveman` directory is likely co-located for experimentation, plugin development, or reuse, but it is logically separate from the MindCradle app.

## Important Caveats and Risks

### Hardcoded Secrets in Utility Scripts

Some backend utility scripts contain hardcoded PocketBase superuser credentials. They were not copied into this file on purpose, but they are present in the repo and should be treated as exposed secrets.

Affected scripts:

- `backend/reseed.py`
- `backend/fix_pocketbase.py`
- `backend/debug_pb.py`

### Mood Scale Mismatch

- Backend schema allows mood `level` from 1 to 10.
- Frontend mood UI only offers 5 discrete choices.

This is not fatal, but it is a contract mismatch worth remembering.

### Auth Is Incomplete

- `/api/auth/me` is a placeholder.
- There is no real backend session/auth middleware yet.
- Client stores token directly in `localStorage`.

### AI Persistence Not Wired Through

`ai_conversations` exists conceptually in PocketBase, but the current backend/frontend chat flow does not appear to save or reload conversation history.

## Fast Mental Model

Think of the workspace like this:

- `frontend/` = UI and user interaction
- `backend/` = thin API and integration layer
- `pocketbase/` = local database + auth source
- `caveman/` = separate plugin/skill project

For the main app, the critical path is:

`frontend/lib/api.ts` -> FastAPI routers -> PocketBase/NVIDIA services

## What Was Actually Inspected

I scanned the whole workspace structure and read the main root/core files for:

- backend entry/config/models/services/routers
- frontend entry/layout/pages/components/lib files
- PocketBase setup and key migrations
- Caveman README and skill definitions

I did not linearly read every generated or vendor file in full, especially large generated artifacts like `frontend/node_modules/**` and the full PocketBase generated type surface. The summary here is based on the app-defining files rather than vendored dependencies.
