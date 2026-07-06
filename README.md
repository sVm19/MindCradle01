# MindCradle — Mental Health & Well-being Dashboard

**MindCradle** is a modern, premium, and calming mental health dashboard designed to help users track their emotional well-being, establish mindful habits, and reflect on their days with a gentle, non-clinical AI companion named ARIA.

---

## Key Features

* **🧘 Guided Journaling**: Document your thoughts in response to daily prompts with an integrated ambient layer (play calming audio like Rain on Glass, Forest Morning, or Ocean Waves while writing).
* **✦ ARIA (AI Companion)**: A validating companion powered by OpenRouter (`google/gemma-4-31b-it:free`). ARIA notices themes, offers gentle reflections, and recommends resources without diagnosing or prescribing.
* **📈 Mood Logging & Calm Score**: Record daily mood levels (1-10) and specific emotions. Observe emotional trends with check-in streaks and a dynamic weekly **Calm Score** (out of 100).
* **☀ Morning Rituals**: Prepare for your day by forecasting your mood, setting daily intentions, and completing small breathing or stretching activities.
* **☽ Evening Wind Down**: Release stress by writing down items to let go of, listing things you are grateful for, selecting a wind-down audio track, and setting a relaxation timer.
* **🏅 Habit Milestones**: Unlock milestones (e.g., *First Light*, *7-Day Grounded*) to celebrate consistent self-care routines.
* **📚 Curated Resources**: Access mental health tools categorized by crisis support, mindfulness, therapy, self-care, physical health, and creative outlets.

---

## 🛠 Tech Stack

### Frontend

* **Core**: React (TypeScript) + Vite
* **Styling**: Modern CSS (featuring responsive layouts, dark glassmorphic aesthetics, and smooth animations)
* **Routing**: React Router

### Backend

* **Core**: Python + FastAPI
* **Database**: Supabase (PostgreSQL)
* **Database Client**: Supabase-py + PostgREST (stateless JWT handling)
* **AI Integration**: OpenRouter API (OpenAI client wrapper)

---

## ⚙️ Setup & Installation

### 1. Database Setup (Supabase)

1. Create a new project on [Supabase](https://supabase.com).
2. Go to the **SQL Editor** in the Supabase Dashboard.
3. Paste and run the SQL migration script located in `backend/supabase/migrations/001_initial_schema.sql` to create all the database tables, triggers, and Row Level Security (RLS) policies.

### 2. Backend Setup

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -e .
   ```

4. Copy the environment template and fill in your credentials in `.env`:

   ```bash
   cp .env.example .env
   ```

   * *Required Env Variables:* `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
5. Run the server:

   ```bash
   uvicorn app.main:app --reload
   ```

### 3. Frontend Setup

1. Navigate to the frontend directory:

   ```bash
   cd ../frontend
   ```

2. Install npm packages:

   ```bash
   npm install
   ```

3. Start the dev server (Vite proxies api calls to the FastAPI server running on `http://localhost:8000`):

   ```bash
   npm run dev
   ```

---

## 📁 Repository Structure

```text
├── backend/
│   ├── app/
│   │   ├── models/        # Pydantic validation schemas
│   │   ├── routers/       # API endpoints (auth, ai, journal, mood, rituals)
│   │   ├── services/      # Supabase & OpenRouter AI connectors
│   │   ├── config.py      # App configurations & settings
│   │   └── main.py        # FastAPI entrypoint & middleware
│   ├── supabase/          # Database SQL migration scripts
│   ├── .env               # Private environment configurations
│   └── pyproject.toml     # Backend dependencies list
│
├── frontend/
│   ├── src/
│   │   ├── app/pages/     # React pages (Dashboard, ARIA, Journal, Rituals, Login)
│   │   ├── lib/           # Fetch API wrappers and auth context providers
│   │   ├── styles/        # Global typography, color variables & themes
│   │   └── main.tsx       # Vite render entrypoint
│   └── vite.config.ts     # Dev proxy and asset resolvers
```
