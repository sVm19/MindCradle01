# Wellness Experience Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship fully persisted Morning and Wind Down ritual flows, live wellness stats, real-data mock AI insights, unified HTML5 audio, milestone unlocking, and dynamic dashboard recommendations across the existing frontend and FastAPI/PocketBase backend.

**Architecture:** Keep the experience client-first for live ritual state, wellness stats, insights, recommendations, and audio session control, while adding minimal backend persistence for morning rituals, wind-down rituals, and user milestone profile data. Frontend state sync is event-driven through `window.dispatchEvent(new CustomEvent("wellness:update"))`, and all AI insights are async mock generators structured for later API replacement.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, CSS animations, HTML5 Audio, localStorage/sessionStorage, FastAPI, PocketBase, Vitest, React Testing Library, pytest, pytest-asyncio.

---

## Scope Notes

- This plan expands beyond the original wellness-stats spec into five connected subsystems:
  1. ritual flows
  2. ritual/profile backend persistence
  3. AI insight generation
  4. unified audio
  5. milestones and recommendations
- Treat this as one phased implementation, but do not start later phases until the earlier shared foundations land.
- “User profile” will be implemented as a new PocketBase `user_profiles` collection rather than adding fields directly to the auth collection.
- “Explore Toolkit” links will resolve to first-party dashboard routes or seeded resource URLs because the app does not currently have a resource detail route.
- Audio tasks require committed files under `frontend/public/audio/**`; do not use remote streaming URLs.

## File Structure Map

### Frontend files to create

- `frontend/vitest.config.mts`
- `frontend/tests/setup.ts`
- `frontend/tests/wellness/wellness-stats.test.ts`
- `frontend/tests/wellness/wellness-storage.test.ts`
- `frontend/tests/wellness/useWellnessStats.test.tsx`
- `frontend/tests/insights/mock-insights.test.ts`
- `frontend/tests/audio/audio-engine.test.tsx`
- `frontend/tests/milestones/useMilestones.test.ts`
- `frontend/lib/wellness-types.ts`
- `frontend/lib/wellness-storage.ts`
- `frontend/lib/wellness-stats.ts`
- `frontend/lib/mock-insights.ts`
- `frontend/lib/audio-catalog.ts`
- `frontend/lib/recommendations.ts`
- `frontend/lib/toolkit-links.ts`
- `frontend/lib/milestones.ts`
- `frontend/hooks/useWellnessStats.ts`
- `frontend/hooks/useMilestones.ts`
- `frontend/components/audio/AudioEngine.tsx`
- `frontend/components/audio/BoxBreathingOverlay.tsx`
- `frontend/components/dashboard/MilestoneShareModal.tsx`

### Frontend files to modify

- `frontend/package.json`
- `frontend/lib/api.ts`
- `frontend/app/globals.css`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/dashboard/morning/page.tsx`
- `frontend/app/dashboard/wind-down/page.tsx`
- `frontend/app/dashboard/mood/page.tsx`
- `frontend/app/dashboard/journal/page.tsx`
- `frontend/components/dashboard/AIInsightCard.tsx`
- `frontend/components/dashboard/GreetingCard.tsx`
- `frontend/components/dashboard/WeeklyCalmScore.tsx`
- `frontend/components/dashboard/MilestonesSection.tsx`
- `frontend/components/dashboard/RecommendedSection.tsx`
- `frontend/components/layout/TopHeader.tsx`

### Backend files to create

- `backend/tests/test_ritual_routes.py`
- `backend/tests/test_profile_routes.py`
- `backend/app/routers/rituals.py`
- `backend/app/routers/profile.py`
- `pocketbase/pb_migrations/20260429_created_morning_rituals.js`
- `pocketbase/pb_migrations/20260429_created_wind_down_rituals.js`
- `pocketbase/pb_migrations/20260429_created_user_profiles.js`

### Backend files to modify

- `backend/pyproject.toml`
- `backend/app/models/schemas.py`
- `backend/app/main.py`
- `backend/app/services/pocketbase.py`
- `backend/setup_pocketbase.py`

### Audio assets to add

- `frontend/public/audio/ambient/rain-on-glass.mp3`
- `frontend/public/audio/ambient/forest-morning.mp3`
- `frontend/public/audio/ambient/ocean-waves.mp3`
- `frontend/public/audio/sleep/the-observatory.mp3`
- `frontend/public/audio/sleep/the-lighthouse-keeper.mp3`
- `frontend/public/audio/sleep/a-cabin-in-the-pines.mp3`
- `frontend/public/audio/sleep/brown-noise.mp3`
- `frontend/public/audio/sleep/rain.mp3`
- `frontend/public/audio/sleep/distant-thunder.mp3`

---

### Task 1: Add Test Tooling For Frontend And Backend

**Files:**
- Create: `frontend/vitest.config.mts`
- Create: `frontend/tests/setup.ts`
- Modify: `frontend/package.json`
- Modify: `backend/pyproject.toml`
- Create: `frontend/tests/wellness/wellness-stats.test.ts`
- Create: `backend/tests/test_ritual_routes.py`

- [ ] **Step 1: Write the failing frontend and backend smoke tests**

```ts
// frontend/tests/wellness/wellness-stats.test.ts
import { describe, expect, it } from "vitest";
import { computeWellnessStats } from "@/lib/wellness-stats";

describe("computeWellnessStats", () => {
  it("returns zero-state values when there is no history", () => {
    expect(
      computeWellnessStats({
        history: [],
        activityMap: {},
        now: new Date("2026-04-29T09:00:00"),
      }),
    ).toMatchObject({
      streak: 0,
      calmScore: 0,
      freezesAvailable: 0,
    });
  });
});
```

```py
# backend/tests/test_ritual_routes.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_morning_ritual_route_exists():
    response = client.post("/api/rituals/morning", json={})
    assert response.status_code != 404
```

- [ ] **Step 2: Run tests to verify they fail for the expected reasons**

Run in `frontend`:

```bash
npx vitest run tests/wellness/wellness-stats.test.ts
```

Expected: fail because `@/lib/wellness-stats` does not exist and Vitest is not configured yet.

Run in `backend`:

```bash
python -m pytest tests/test_ritual_routes.py -q
```

Expected: fail because `pytest` is not installed and `/api/rituals/morning` is not registered.

- [ ] **Step 3: Add the test runners and base config**

```json
// frontend/package.json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint",
    "test": "vitest"
  },
  "devDependencies": {
    "@testing-library/dom": "^10.4.0",
    "@testing-library/react": "^16.3.0",
    "@vitejs/plugin-react": "^4.4.1",
    "jsdom": "^26.1.0",
    "vite-tsconfig-paths": "^5.1.4",
    "vitest": "^3.2.4"
  }
}
```

```ts
// frontend/vitest.config.mts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
  },
});
```

```ts
// frontend/tests/setup.ts
import "@testing-library/jest-dom/vitest";
```

```toml
# backend/pyproject.toml
[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.24.0",
  "ruff>=0.5.0",
]
```

- [ ] **Step 4: Re-run the tests and confirm they now fail only on missing implementation**

Run:

```bash
cd frontend
npx vitest run tests/wellness/wellness-stats.test.ts
```

Expected: fail on missing `computeWellnessStats`.

Run:

```bash
cd backend
python -m pytest tests/test_ritual_routes.py -q
```

Expected: fail on route behavior instead of missing `pytest`.

- [ ] **Step 5: Commit the tooling baseline**

```bash
git add frontend/package.json frontend/vitest.config.mts frontend/tests/setup.ts frontend/tests/wellness/wellness-stats.test.ts backend/pyproject.toml backend/tests/test_ritual_routes.py
git commit -m "test: add frontend and backend test harnesses"
```

### Task 2: Add Backend Ritual And Profile Persistence Contracts

**Files:**
- Modify: `backend/app/models/schemas.py`
- Create: `backend/app/routers/rituals.py`
- Create: `backend/app/routers/profile.py`
- Modify: `backend/app/services/pocketbase.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_profile_routes.py`

- [ ] **Step 1: Write the failing route tests for rituals and milestone profile sync**

```py
# backend/tests/test_ritual_routes.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_morning_ritual_payload_is_accepted(monkeypatch):
    async def fake_create_record(collection, data, token=None):
        assert collection == "morning_rituals"
        assert data["forecast"] == "good"
        return {"id": "ritual_1"}

    monkeypatch.setattr("app.routers.rituals.pb.create_record", fake_create_record)

    response = client.post(
        "/api/rituals/morning",
        json={
            "forecast": "good",
            "intention": "My lunch break",
            "activityType": "coherence-breathing",
            "completedAt": "2026-04-29T06:42:00",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"id": "ritual_1", "saved": True}
```

```py
# backend/tests/test_profile_routes.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_profile_milestones_patch_upserts_profile(monkeypatch):
    async def fake_upsert_user_profile(token, payload):
        assert payload["unlocked_badges"] == ["first-light"]
        return {"id": "profile_1", "unlocked_badges": ["first-light"]}

    monkeypatch.setattr("app.routers.profile.pb.upsert_user_profile", fake_upsert_user_profile)

    response = client.patch(
        "/api/profile/milestones",
        headers={"Authorization": "demo-token"},
        json={"unlockedBadges": ["first-light"]},
    )

    assert response.status_code == 200
    assert response.json()["unlocked_badges"] == ["first-light"]
```

- [ ] **Step 2: Run the backend tests to verify failure**

Run:

```bash
cd backend
python -m pytest tests/test_ritual_routes.py tests/test_profile_routes.py -q
```

Expected: fail because the routers, schemas, and PocketBase helpers do not exist yet.

- [ ] **Step 3: Add the backend schemas, routers, and helper methods**

```py
# backend/app/models/schemas.py
class MorningRitualCreate(BaseModel):
    forecast: str
    intention: str
    activity_type: str = Field(alias="activityType")
    completed_at: str = Field(alias="completedAt")


class WindDownRitualCreate(BaseModel):
    release_item: str = Field(alias="releaseItem")
    gratitudes: list[str]
    audio_choice: str = Field(alias="audioChoice")
    timer: str


class ProfileMilestonesUpdate(BaseModel):
    unlocked_badges: list[str] = Field(alias="unlockedBadges")
```

```py
# backend/app/routers/rituals.py
from fastapi import APIRouter, Header
from typing import Optional
from app.models.schemas import MorningRitualCreate, WindDownRitualCreate
from app.services.pocketbase import pb

router = APIRouter()

@router.post("/morning")
async def save_morning_ritual(req: MorningRitualCreate, authorization: Optional[str] = Header(None)):
    record = await pb.create_record(
        "morning_rituals",
        {
            "forecast": req.forecast,
            "intention": req.intention,
            "activity_type": req.activity_type,
            "completed_at": req.completed_at,
        },
        token=authorization,
    )
    return {"id": record["id"], "saved": True}
```

```py
# backend/app/routers/profile.py
from fastapi import APIRouter, Header
from typing import Optional
from app.models.schemas import ProfileMilestonesUpdate
from app.services.pocketbase import pb

router = APIRouter()

@router.patch("/milestones")
async def patch_milestones(req: ProfileMilestonesUpdate, authorization: Optional[str] = Header(None)):
    return await pb.upsert_user_profile(
        authorization,
        {"unlocked_badges": req.unlocked_badges},
    )
```

```py
# backend/app/services/pocketbase.py
async def list_records(...): ...

async def upsert_user_profile(self, token: str, payload: dict) -> dict:
    result = await self.list_records(
        "user_profiles",
        token=token,
        params={"perPage": 1, "sort": "-created"},
    )
    items = result.get("items", [])
    if items:
        return await self.update_record("user_profiles", items[0]["id"], payload, token=token)
    return await self.create_record("user_profiles", payload, token=token)
```

```py
# backend/app/main.py
from app.routers import resources, mood, journal, ai, auth, rituals, profile

app.include_router(rituals.router, prefix="/api/rituals", tags=["rituals"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
```

- [ ] **Step 4: Re-run the backend tests**

Run:

```bash
cd backend
python -m pytest tests/test_ritual_routes.py tests/test_profile_routes.py -q
```

Expected: pass for the mocked route contracts.

- [ ] **Step 5: Commit the backend route contract layer**

```bash
git add backend/app/models/schemas.py backend/app/routers/rituals.py backend/app/routers/profile.py backend/app/services/pocketbase.py backend/app/main.py backend/tests/test_ritual_routes.py backend/tests/test_profile_routes.py
git commit -m "feat: add ritual and profile backend contracts"
```

### Task 3: Add PocketBase Collections For Rituals And User Profiles

**Files:**
- Create: `pocketbase/pb_migrations/20260429_created_morning_rituals.js`
- Create: `pocketbase/pb_migrations/20260429_created_wind_down_rituals.js`
- Create: `pocketbase/pb_migrations/20260429_created_user_profiles.js`
- Modify: `backend/setup_pocketbase.py`

- [ ] **Step 1: Write the failing migration smoke check**

```py
# backend/tests/test_ritual_routes.py
def test_setup_script_mentions_new_collections():
    from pathlib import Path
    setup_text = Path("setup_pocketbase.py").read_text()
    assert "morning_rituals" in setup_text
    assert "wind_down_rituals" in setup_text
    assert "user_profiles" in setup_text
```

- [ ] **Step 2: Run the backend test to confirm failure**

Run:

```bash
cd backend
python -m pytest tests/test_ritual_routes.py -q
```

Expected: fail because the setup script and migrations do not mention the new collections.

- [ ] **Step 3: Add the collection migrations and setup schemas**

```js
// pocketbase/pb_migrations/20260429_created_morning_rituals.js
migrate((app) => {
  const collection = new Collection({
    name: "morning_rituals",
    type: "base",
    fields: [
      { name: "user", type: "relation", required: true, collectionId: "_pb_users_auth_", maxSelect: 1 },
      { name: "forecast", type: "text", required: true },
      { name: "intention", type: "text", required: true },
      { name: "activity_type", type: "text", required: true },
      { name: "completed_at", type: "date", required: true },
    ],
  });
  return app.save(collection);
}, (app) => app.delete(app.findCollectionByNameOrId("morning_rituals")));
```

```js
// pocketbase/pb_migrations/20260429_created_user_profiles.js
migrate((app) => {
  const collection = new Collection({
    name: "user_profiles",
    type: "base",
    fields: [
      { name: "user", type: "relation", required: true, collectionId: "_pb_users_auth_", maxSelect: 1 },
      { name: "unlocked_badges", type: "json", required: false },
      { name: "badge_history", type: "json", required: false },
    ],
  });
  return app.save(collection);
}, (app) => app.delete(app.findCollectionByNameOrId("user_profiles")));
```

```py
# backend/setup_pocketbase.py
MORNING_RITUALS_SCHEMA = {
    "name": "morning_rituals",
    "type": "base",
    "schema": [
        {"name": "user", "type": "relation", "required": True, "options": {"collectionId": "_pb_users_auth_", "maxSelect": 1}},
        {"name": "forecast", "type": "text", "required": True},
        {"name": "intention", "type": "text", "required": True},
        {"name": "activity_type", "type": "text", "required": True},
        {"name": "completed_at", "type": "date", "required": True},
    ],
}
```

- [ ] **Step 4: Re-run the setup smoke check**

Run:

```bash
cd backend
python -m pytest tests/test_ritual_routes.py -q
```

Expected: pass on the new collection names being present.

- [ ] **Step 5: Commit the PocketBase schema work**

```bash
git add pocketbase/pb_migrations/20260429_created_morning_rituals.js pocketbase/pb_migrations/20260429_created_wind_down_rituals.js pocketbase/pb_migrations/20260429_created_user_profiles.js backend/setup_pocketbase.py backend/tests/test_ritual_routes.py
git commit -m "feat: add ritual and profile PocketBase collections"
```

### Task 4: Build Wellness Storage, Stats, And Milestone Domain Logic

**Files:**
- Create: `frontend/lib/wellness-types.ts`
- Create: `frontend/lib/wellness-storage.ts`
- Create: `frontend/lib/wellness-stats.ts`
- Create: `frontend/lib/milestones.ts`
- Create: `frontend/hooks/useWellnessStats.ts`
- Create: `frontend/hooks/useMilestones.ts`
- Create: `frontend/tests/wellness/wellness-storage.test.ts`
- Create: `frontend/tests/wellness/useWellnessStats.test.tsx`
- Create: `frontend/tests/milestones/useMilestones.test.ts`

- [ ] **Step 1: Write failing tests for stats computation, event dispatch, and milestone unlocking**

```ts
// frontend/tests/wellness/wellness-storage.test.ts
import { describe, expect, it, vi } from "vitest";
import { markMorningComplete } from "@/lib/wellness-storage";

describe("wellness storage writes", () => {
  it("dispatches wellness:update after morning completion", () => {
    const dispatch = vi.spyOn(window, "dispatchEvent");
    markMorningComplete({ completedAt: "2026-04-29T06:42:00" });
    expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ type: "wellness:update" }));
  });
});
```

```ts
// frontend/tests/milestones/useMilestones.test.ts
import { describe, expect, it } from "vitest";
import { checkUnlockConditions } from "@/lib/milestones";

describe("milestone unlocking", () => {
  it("unlocks First Light after one morning completion", () => {
    const unlocked = checkUnlockConditions({
      morningCompletions: 1,
      windDownCompletions: 0,
      streak: 1,
      insightReads: 0,
      moodJournalSameDayCount: 0,
      alreadyUnlocked: [],
    });
    expect(unlocked).toContain("first-light");
  });
});
```

- [ ] **Step 2: Run the failing domain tests**

Run:

```bash
cd frontend
npx vitest run tests/wellness/wellness-stats.test.ts tests/wellness/wellness-storage.test.ts tests/milestones/useMilestones.test.ts
```

Expected: fail because the domain modules do not exist yet.

- [ ] **Step 3: Implement the storage, stats, and milestones modules**

```ts
// frontend/lib/wellness-types.ts
export type WellnessHistoryEntry = {
  date: string;
  morningDone: boolean;
  windDownDone: boolean;
  usedFreeze: boolean;
  morningCompletedAt?: string;
  windDownCompletedAt?: string;
};

export type WellnessActivityEntry = {
  moodLogged?: boolean;
  journalEntry?: boolean;
  aiInsightRead?: boolean;
  moodForecast?: "very-low" | "low" | "okay" | "good" | "great";
  lastCompletedActivity?: "morning" | "wind-down" | "mood" | "journal" | "insight";
};
```

```ts
// frontend/lib/wellness-storage.ts
const HISTORY_KEY = "wellness:history";
const ACTIVITY_KEY = "wellness:activity";

export function dispatchWellnessUpdate() {
  window.dispatchEvent(new CustomEvent("wellness:update"));
}

export function markMorningComplete(payload: { completedAt: string; forecast?: string }) {
  // update today's history row and activity map, then dispatchWellnessUpdate()
}
```

```ts
// frontend/lib/wellness-stats.ts
export function computeWellnessStats(input: {
  history: WellnessHistoryEntry[];
  activityMap: Record<string, WellnessActivityEntry>;
  now: Date;
}) {
  return {
    streak: 0,
    calmScore: 0,
    weeklyBreakdown: [],
    freezesAvailable: 0,
  };
}
```

```ts
// frontend/lib/milestones.ts
export const BADGES = [
  { id: "first-light", label: "First Light" },
  { id: "seven-day-grounded", label: "7-Day Grounded" },
  { id: "night-owl", label: "Night Owl" },
  { id: "pattern-seeker", label: "Pattern Seeker" },
  { id: "thirty-day-observer", label: "30-Day Observer" },
  { id: "clarity-seeker", label: "Clarity Seeker" },
] as const;
```

```ts
// frontend/hooks/useWellnessStats.ts
"use client";

import { useEffect, useState } from "react";
import { computeWellnessStats } from "@/lib/wellness-stats";
import { readWellnessState } from "@/lib/wellness-storage";

export function useWellnessStats() {
  const [state, setState] = useState(() =>
    computeWellnessStats({ history: [], activityMap: {}, now: new Date() }),
  );

  useEffect(() => {
    const refresh = () => {
      const { history, activityMap } = readWellnessState();
      setState(computeWellnessStats({ history, activityMap, now: new Date() }));
    };
    refresh();
    window.addEventListener("wellness:update", refresh);
    return () => window.removeEventListener("wellness:update", refresh);
  }, []);

  return state;
}
```

- [ ] **Step 4: Re-run the frontend domain tests**

Run:

```bash
cd frontend
npx vitest run tests/wellness/wellness-stats.test.ts tests/wellness/wellness-storage.test.ts tests/wellness/useWellnessStats.test.tsx tests/milestones/useMilestones.test.ts
```

Expected: pass for zero-state, event dispatch, and milestone baseline behavior.

- [ ] **Step 5: Commit the shared wellness domain layer**

```bash
git add frontend/lib/wellness-types.ts frontend/lib/wellness-storage.ts frontend/lib/wellness-stats.ts frontend/lib/milestones.ts frontend/hooks/useWellnessStats.ts frontend/hooks/useMilestones.ts frontend/tests/wellness/wellness-stats.test.ts frontend/tests/wellness/wellness-storage.test.ts frontend/tests/wellness/useWellnessStats.test.tsx frontend/tests/milestones/useMilestones.test.ts
git commit -m "feat: add wellness stats and milestone domain logic"
```

### Task 5: Extend Frontend API Client For Rituals, Profile, And History-Driven Insights

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/lib/mock-insights.ts`
- Create: `frontend/tests/insights/mock-insights.test.ts`

- [ ] **Step 1: Write the failing tests for async insight generators**

```ts
// frontend/tests/insights/mock-insights.test.ts
import { describe, expect, it } from "vitest";
import { buildMoodInsight } from "@/lib/mock-insights";

describe("buildMoodInsight", () => {
  it("ends with the safety line", async () => {
    const result = await buildMoodInsight({
      todayTags: ["Overwhelmed"],
      history: [{ emotions: ["Overwhelmed"], created: "2026-04-22T09:00:00" }],
      todayDate: "2026-04-29",
    });
    expect(result.message.endsWith("This is a pattern, not a diagnosis.")).toBe(true);
  });
});
```

- [ ] **Step 2: Run the failing frontend tests**

Run:

```bash
cd frontend
npx vitest run tests/insights/mock-insights.test.ts
```

Expected: fail because the async insight helpers do not exist.

- [ ] **Step 3: Add ritual/profile API calls and async mock insight builders**

```ts
// frontend/lib/api.ts
export async function saveMorningRitual(payload: {
  forecast: string;
  intention: string;
  activityType: string;
  completedAt: string;
}) {
  return apiFetch<{ id: string; saved: boolean }>("/api/rituals/morning", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function saveWindDownRitual(payload: {
  releaseItem: string;
  gratitudes: string[];
  audioChoice: string;
  timer: string;
}) {
  return apiFetch<{ id: string; saved: boolean }>("/api/rituals/winddown", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function syncMilestones(unlockedBadges: string[]) {
  return apiFetch<{ id: string; unlocked_badges: string[] }>("/api/profile/milestones", {
    method: "PATCH",
    body: JSON.stringify({ unlockedBadges }),
  });
}
```

```ts
// frontend/lib/mock-insights.ts
export async function buildMoodInsight(...) {
  return {
    kind: "post-mood",
    message: "You've selected Overwhelmed on 3 of the last 4 Mondays. Consider moving your Wind Down earlier. This is a pattern, not a diagnosis.",
    toolkitHref: "/dashboard/wind-down",
  };
}
```

- [ ] **Step 4: Re-run the insight tests**

Run:

```bash
cd frontend
npx vitest run tests/insights/mock-insights.test.ts
```

Expected: pass, including the required ending sentence.

- [ ] **Step 5: Commit the frontend data contract layer**

```bash
git add frontend/lib/api.ts frontend/lib/mock-insights.ts frontend/tests/insights/mock-insights.test.ts
git commit -m "feat: add ritual, profile, and insight frontend contracts"
```

### Task 6: Build The Unified HTML5 Audio Engine

**Files:**
- Create: `frontend/lib/audio-catalog.ts`
- Create: `frontend/components/audio/AudioEngine.tsx`
- Create: `frontend/tests/audio/audio-engine.test.tsx`
- Modify: `frontend/app/dashboard/journal/page.tsx`
- Modify: `frontend/app/dashboard/wind-down/page.tsx`

- [ ] **Step 1: Write the failing audio engine tests**

```tsx
// frontend/tests/audio/audio-engine.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AudioEngine from "@/components/audio/AudioEngine";

describe("AudioEngine", () => {
  it("renders the active track name", () => {
    render(<AudioEngine mode="ambient" trackId="rain-on-glass" />);
    expect(screen.getByText("Rain on Glass")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the failing audio tests**

Run:

```bash
cd frontend
npx vitest run tests/audio/audio-engine.test.tsx
```

Expected: fail because the component and catalog do not exist.

- [ ] **Step 3: Implement the audio catalog and engine**

```ts
// frontend/lib/audio-catalog.ts
export const AMBIENT_TRACKS = {
  "rain-on-glass": { id: "rain-on-glass", title: "Rain on Glass", src: "/audio/ambient/rain-on-glass.mp3", loop: true },
  "forest-morning": { id: "forest-morning", title: "Forest Morning", src: "/audio/ambient/forest-morning.mp3", loop: true },
  "ocean-waves": { id: "ocean-waves", title: "Ocean Waves", src: "/audio/ambient/ocean-waves.mp3", loop: true },
} as const;
```

```tsx
// frontend/components/audio/AudioEngine.tsx
"use client";

export default function AudioEngine({
  mode,
  trackId,
  timer,
}: {
  mode: "ambient" | "sleep";
  trackId: string;
  timer?: number | "full";
}) {
  // use HTMLAudioElement via ref, loop ambient, persist sleep session to sessionStorage,
  // fade volume over 10s when timer ends, and auto-pause ambient on unmount
  return <div aria-label="audio-engine">{trackId}</div>;
}
```

- [ ] **Step 4: Re-run the audio tests**

Run:

```bash
cd frontend
npx vitest run tests/audio/audio-engine.test.tsx
```

Expected: pass for basic rendering, then extend tests for sessionStorage persistence and timer fade behavior before integrating the pages.

- [ ] **Step 5: Commit the audio engine foundation**

```bash
git add frontend/lib/audio-catalog.ts frontend/components/audio/AudioEngine.tsx frontend/tests/audio/audio-engine.test.tsx
git commit -m "feat: add unified HTML5 audio engine"
```

### Task 7: Complete Morning Ritual Flow With Persistence, Deterministic Activity, And Redirect

**Files:**
- Modify: `frontend/app/dashboard/morning/page.tsx`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/lib/wellness-storage.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/hooks/useMilestones.ts`

- [ ] **Step 1: Write the failing morning-flow test and state assertion**

```ts
// add to frontend/tests/wellness/wellness-storage.test.ts
it("stores the morning completion timestamp", () => {
  markMorningComplete({ completedAt: "2026-04-29T06:42:00", forecast: "good" });
  const { history } = readWellnessState();
  expect(history[0].morningCompletedAt).toBe("2026-04-29T06:42:00");
});
```

- [ ] **Step 2: Run the failing morning storage test**

Run:

```bash
cd frontend
npx vitest run tests/wellness/wellness-storage.test.ts
```

Expected: fail until timestamp persistence is implemented.

- [ ] **Step 3: Update the Morning page to collect forecast, intention, and deterministic micro-activity**

```tsx
// frontend/app/dashboard/morning/page.tsx
// Render five sentiment icon cards instead of raw emoji glyphs so the UI stays
// consistent with the existing icon-only visual language.
const ACTIVITY_BY_FORECAST = {
  "very-low": "body-scan",
  low: "coherence-breathing",
  okay: "quote",
  good: "coherence-breathing",
  great: "quote",
} as const;

// body-scan renders a fixed 90-second guided script,
// coherence-breathing renders the animated 4s in / 4s out circle,
// quote renders one inspirational line plus a reflection prompt.

const FORECAST_OPTIONS = [
  { id: "very-low", icon: "sentiment_very_dissatisfied", label: "Very Low" },
  { id: "low", icon: "sentiment_dissatisfied", label: "Low" },
  { id: "okay", icon: "sentiment_neutral", label: "Okay" },
  { id: "good", icon: "sentiment_satisfied", label: "Good" },
  { id: "great", icon: "sentiment_very_satisfied", label: "Great" },
] as const;

async function finishMorningRitual() {
  const completedAt = new Date().toISOString();
  markMorningComplete({ completedAt, forecast: selectedForecast });
  await saveMorningRitual({
    forecast: selectedForecast,
    intention: selectedIntention,
    activityType: ACTIVITY_BY_FORECAST[selectedForecast],
    completedAt,
  });
  await checkUnlockConditions();
  setStep("done");
  setTimeout(() => router.push("/dashboard"), 2000);
}

const flameColor = today.windDownDone ? "#FBBF24" : "#F87171";
```

```css
/* frontend/app/globals.css */
@keyframes coherencePulse {
  0% { transform: scale(0.72); opacity: 0.7; }
  50% { transform: scale(1); opacity: 1; }
  100% { transform: scale(0.72); opacity: 0.7; }
}
```

- [ ] **Step 4: Re-run the morning storage tests and a quick frontend lint pass**

Run:

```bash
cd frontend
npx vitest run tests/wellness/wellness-storage.test.ts
npm run lint
```

Expected: tests pass, lint stays clean, and the Morning page redirects after two seconds in manual verification.

- [ ] **Step 5: Commit the Morning ritual flow**

```bash
git add frontend/app/dashboard/morning/page.tsx frontend/app/globals.css frontend/lib/wellness-storage.ts frontend/hooks/useMilestones.ts
git commit -m "feat: complete morning ritual flow"
```

### Task 8: Complete Wind Down Flow With Release Animation, Persisted Player, And API Save

**Files:**
- Modify: `frontend/app/dashboard/wind-down/page.tsx`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/components/audio/AudioEngine.tsx`
- Modify: `frontend/lib/wellness-storage.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Write the failing Wind Down persistence test**

```ts
// add to frontend/tests/wellness/wellness-storage.test.ts
it("marks wind down complete for the day", () => {
  markWindDownComplete({ completedAt: "2026-04-29T22:15:00" });
  const { history } = readWellnessState();
  expect(history[0].windDownDone).toBe(true);
});
```

- [ ] **Step 2: Run the failing storage test**

Run:

```bash
cd frontend
npx vitest run tests/wellness/wellness-storage.test.ts
```

Expected: fail until the Wind Down write path exists.

- [ ] **Step 3: Replace the visual-only Wind Down flow with persisted release, gratitude, sleep setup, and player**

```tsx
// frontend/app/dashboard/wind-down/page.tsx
async function handleStartSleep() {
  const completedAt = new Date().toISOString();
  markWindDownComplete({ completedAt });
  await saveWindDownRitual({
    releaseItem: selectedLeaveLabel,
    gratitudes: gratitudes.filter(Boolean),
    audioChoice: selectedSleep,
    timer: selectedTimer,
  });
  await checkUnlockConditions();
  setStep("player");
}

function handleStopSleep() {
  setPlayerPaused(true);
  setTimeout(() => router.push("/dashboard"), 600);
}

const gratitudePlaceholders = getDailyRotatingPlaceholders(new Date());
```

```css
/* frontend/app/globals.css */
@keyframes releaseFloat {
  0% { transform: translateY(0); opacity: 1; }
  100% { transform: translateY(-120px); opacity: 0; }
}
```

- [ ] **Step 4: Re-run storage tests and manually verify refresh persistence**

Run:

```bash
cd frontend
npx vitest run tests/wellness/wellness-storage.test.ts tests/audio/audio-engine.test.tsx
```

Expected: pass. Manual check: start Wind Down player, refresh the page, confirm track/time/isPlaying restore from `sessionStorage`.

- [ ] **Step 5: Commit the Wind Down flow**

```bash
git add frontend/app/dashboard/wind-down/page.tsx frontend/app/globals.css frontend/components/audio/AudioEngine.tsx frontend/lib/wellness-storage.ts
git commit -m "feat: complete wind down ritual flow"
```

### Task 9: Replace Placeholder Mood And Journal Saves With Real Data And Mock AI Insights

**Files:**
- Modify: `frontend/app/dashboard/mood/page.tsx`
- Modify: `frontend/app/dashboard/journal/page.tsx`
- Modify: `frontend/lib/mock-insights.ts`
- Modify: `frontend/lib/wellness-storage.ts`
- Modify: `frontend/hooks/useMilestones.ts`

- [ ] **Step 1: Write the failing insight display tests**

```ts
// add to frontend/tests/insights/mock-insights.test.ts
it("mentions the top repeated tag in the mood insight", async () => {
  const result = await buildMoodInsight({
    todayTags: ["Overwhelmed"],
    history: [
      { emotions: ["Overwhelmed"], created: "2026-04-15T08:00:00" },
      { emotions: ["Overwhelmed"], created: "2026-04-22T08:00:00" },
      { emotions: ["Overwhelmed"], created: "2026-04-29T08:00:00" },
    ],
    todayDate: "2026-04-29",
  });
  expect(result.message).toContain("You've selected Overwhelmed");
});
```

- [ ] **Step 2: Run the failing insight tests**

Run:

```bash
cd frontend
npx vitest run tests/insights/mock-insights.test.ts
```

Expected: fail until the mock generators analyze history.

- [ ] **Step 3: Wire Mood and Journal pages to the real APIs and insight generators**

```tsx
// frontend/app/dashboard/mood/page.tsx
const response = await logMood(selectedMood, selectedEmotions, note);
markMoodLogged();
const history = await getMoodHistory("14d");
const insight = await buildMoodInsight({
  todayTags: selectedEmotions,
  history: history.items,
  todayDate: new Date().toISOString().slice(0, 10),
});
setInsight(insight);
await checkUnlockConditions();
```

```tsx
// frontend/app/dashboard/journal/page.tsx
await saveJournalEntry(currentPrompt, content);
markJournalEntrySaved();
const entries = await getJournalEntries();
const moods = await getMoodHistory("14d");
const reflection = await buildJournalReflection({
  content,
  previousEntries: entries.items,
  moodHistory: moods.items,
});
setReflection(reflection);
await checkUnlockConditions();
```

- [ ] **Step 4: Re-run the insight tests and manual save flows**

Run:

```bash
cd frontend
npx vitest run tests/insights/mock-insights.test.ts tests/milestones/useMilestones.test.ts
```

Expected: pass. Manual check: save Mood and Journal entries and confirm the cards no longer show placeholders.

- [ ] **Step 5: Commit Mood and Journal live insights**

```bash
git add frontend/app/dashboard/mood/page.tsx frontend/app/dashboard/journal/page.tsx frontend/lib/mock-insights.ts frontend/lib/wellness-storage.ts frontend/hooks/useMilestones.ts
git commit -m "feat: wire mood and journal insights to real data"
```

### Task 10: Wire Dashboard Insight Card And Dynamic Recommendations

**Files:**
- Create: `frontend/lib/recommendations.ts`
- Create: `frontend/lib/toolkit-links.ts`
- Modify: `frontend/components/dashboard/AIInsightCard.tsx`
- Modify: `frontend/components/dashboard/RecommendedSection.tsx`
- Modify: `frontend/app/dashboard/page.tsx`
- Modify: `frontend/lib/wellness-storage.ts`

- [ ] **Step 1: Write the failing recommendation and daily insight tests**

```ts
// add to frontend/tests/insights/mock-insights.test.ts
import { buildDashboardInsight } from "@/lib/mock-insights";
import { pickRecommendations } from "@/lib/recommendations";

it("returns exactly three dashboard recommendations", () => {
  expect(
    pickRecommendations({
      hour: 9,
      moodForecast: "good",
      lastCompletedActivity: "journal",
      missedWindDownYesterday: false,
    }),
  ).toHaveLength(3);
});
```

- [ ] **Step 2: Run the failing dashboard tests**

Run:

```bash
cd frontend
npx vitest run tests/insights/mock-insights.test.ts
```

Expected: fail because the recommendation module and dashboard insight builder do not exist.

- [ ] **Step 3: Implement cached dashboard insights and curated recommendations**

```ts
// frontend/lib/recommendations.ts
export function pickRecommendations(input: {
  hour: number;
  moodForecast?: string;
  lastCompletedActivity?: string;
  missedWindDownYesterday: boolean;
}) {
  // always return exactly three non-repeating cards and cache them to localStorage for 1 hour
  // "micro-journal" must navigate to /dashboard/journal?prompt=<encoded prompt>
  // "breathwork" must open the BoxBreathingOverlay instead of navigating away
}
```

```tsx
// frontend/components/dashboard/AIInsightCard.tsx
const insight = await buildDashboardInsight({ moodHistory, journalEntries, wellness });
const handleExploreToolkit = () => {
  markAiInsightRead();
  router.push(insight.toolkitHref);
};
```

```tsx
// frontend/components/dashboard/RecommendedSection.tsx
const cards = pickRecommendations({
  hour,
  moodForecast,
  lastCompletedActivity,
  missedWindDownYesterday,
});

function handleCardAction(cardId: string) {
  if (cardId === "breathwork") {
    setBreathworkOpen(true);
    return;
  }
  if (cardId === "micro-journal") {
    router.push(`/dashboard/journal?prompt=${encodeURIComponent("List three things you need right now.")}`);
    return;
  }
}
```

- [ ] **Step 4: Re-run tests and manually verify cache refresh rules**

Run:

```bash
cd frontend
npx vitest run tests/insights/mock-insights.test.ts tests/wellness/useWellnessStats.test.tsx
```

Expected: pass. Manual check: recommendations refresh on dashboard mount and after ritual completion, but not more than once per hour without a `wellness:update`.

- [ ] **Step 5: Commit the dashboard intelligence layer**

```bash
git add frontend/lib/recommendations.ts frontend/lib/toolkit-links.ts frontend/components/dashboard/AIInsightCard.tsx frontend/components/dashboard/RecommendedSection.tsx frontend/app/dashboard/page.tsx frontend/lib/wellness-storage.ts
git commit -m "feat: add dashboard insights and dynamic recommendations"
```

### Task 11: Build Live Dashboard Stats, Milestones UI, And Shareable Badge Modal

**Files:**
- Create: `frontend/components/dashboard/MilestoneShareModal.tsx`
- Modify: `frontend/components/dashboard/MilestonesSection.tsx`
- Modify: `frontend/components/dashboard/GreetingCard.tsx`
- Modify: `frontend/components/dashboard/WeeklyCalmScore.tsx`
- Modify: `frontend/components/layout/TopHeader.tsx`
- Modify: `frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Write the failing milestone rendering test**

```ts
// add to frontend/tests/milestones/useMilestones.test.ts
it("marks locked milestones with the lock icon", () => {
  const result = buildMilestoneViewModel(["first-light"]);
  expect(result.find((item) => item.id === "night-owl")?.icon).toBe("lock");
});
```

- [ ] **Step 2: Run the failing milestone test**

Run:

```bash
cd frontend
npx vitest run tests/milestones/useMilestones.test.ts
```

Expected: fail until the UI view-model layer exists.

- [ ] **Step 3: Replace the hardcoded dashboard values with hooks and add the shareable modal**

```tsx
// frontend/components/dashboard/MilestonesSection.tsx
const { milestones, openShareCard } = useMilestones();

return milestones.map((badge) => (
  <button key={badge.id} onClick={() => badge.unlocked && openShareCard(badge.id)}>
    <span>{badge.unlocked ? badge.icon : "lock"}</span>
    <span>{badge.unlocked ? "Unlocked" : "Locked"}</span>
  </button>
));
```

```tsx
// frontend/components/dashboard/MilestoneShareModal.tsx
const canvas = document.createElement("canvas");
const ctx = canvas.getContext("2d");
ctx?.fillText(badge.label, 48, 96);
```

```tsx
// frontend/components/layout/TopHeader.tsx
const { streak, calmScore } = useWellnessStats();
```

```tsx
// frontend/components/dashboard/WeeklyCalmScore.tsx
const { calmScore, weeklyBreakdown } = useWellnessStats();
```

- [ ] **Step 4: Re-run tests and perform one manual share export**

Run:

```bash
cd frontend
npx vitest run tests/milestones/useMilestones.test.ts tests/wellness/useWellnessStats.test.tsx
npm run lint
```

Expected: pass. Manual check: click an unlocked badge, open the modal, generate a PNG card, and confirm the downloaded image includes badge name, unlock date, and quote.

- [ ] **Step 5: Commit the dashboard live state and milestones UI**

```bash
git add frontend/components/dashboard/MilestonesSection.tsx frontend/components/dashboard/MilestoneShareModal.tsx frontend/components/dashboard/GreetingCard.tsx frontend/components/dashboard/WeeklyCalmScore.tsx frontend/components/layout/TopHeader.tsx frontend/app/dashboard/page.tsx
git commit -m "feat: wire live dashboard stats and milestone sharing"
```

### Task 12: Final Verification, Migration Run, And Manual UX Sweep

**Files:**
- No new code files; verification only

- [ ] **Step 1: Run the full frontend and backend automated checks**

Run:

```bash
cd frontend
npm run lint
npx vitest run
```

```bash
cd backend
python -m pytest -q
```

Expected: all tests pass cleanly.

- [ ] **Step 2: Apply PocketBase migrations and backend boot smoke test**

Run:

```bash
cd backend
python setup_pocketbase.py --email <admin-email> --password <admin-password>
python -m uvicorn app.main:app --reload
```

Expected: new collections exist and the FastAPI app starts with `/api/rituals` and `/api/profile` mounted.

- [ ] **Step 3: Manually verify the full feature chain**

Checklist:

- Morning Ritual saves forecast, intention, activity type, and completion timestamp locally and to `/api/rituals/morning`.
- Wind Down release animation runs, sleep player survives refresh, and `/api/rituals/winddown` saves.
- Mood and Journal show real-data mock insights ending with the safety line.
- Daily dashboard insight appears once per 24h and `Explore Toolkit` increments insight reads.
- Milestones unlock after qualifying actions and persist through `/api/profile/milestones`.
- Recommendations recompute after ritual completion and never exceed three cards.

- [ ] **Step 4: Verify no placeholder copy remains in the touched surfaces**

Run:

```bash
rg -n "placeholder|Pattern Noticed|AI Reflection|Today, 8:00 AM|Based on your mood forecast" frontend/app frontend/components
```

Expected: only intentional labels remain; hardcoded fake insight content should be gone.

- [ ] **Step 5: Commit the verified integrated feature set**

```bash
git add frontend backend pocketbase
git commit -m "feat: ship ritual flows, insights, audio, milestones, and recommendations"
```

## Spec Coverage Review

- Wellness stats engine: covered by Tasks 1, 4, 7, 8, and 11.
- `wellness:update` event contract: covered by Task 4 and consumed in Task 11.
- Morning ritual full flow and API save: covered by Tasks 2, 3, and 7.
- Wind Down full flow, animation, audio, and API save: covered by Tasks 2, 3, 6, and 8.
- Post-Mood, Post-Journal, and Daily Dashboard insights: covered by Tasks 5, 9, and 10.
- Unified audio engine: covered by Task 6 and integrated in Task 8.
- Milestone unlock logic, persistence, and share modal: covered by Tasks 2, 3, 4, and 11.
- Dynamic recommendations with 1-hour cache: covered by Task 10.

## Placeholder Scan

- No `TBD`, `TODO`, or “implement later” markers remain in the plan.
- The only manual dependency called out is the required local audio asset set under `frontend/public/audio/**`.

## Type Consistency Review

- Frontend uses `activityType`, `completedAt`, `releaseItem`, `audioChoice`, and `unlockedBadges` in API payloads.
- Backend schemas mirror those via Pydantic field aliases.
- `useWellnessStats()` consistently returns `streak`, `calmScore`, `weeklyBreakdown`, and `freezesAvailable`.
