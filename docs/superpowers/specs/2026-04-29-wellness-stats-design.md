# Wellness Stats Design

- Date: 2026-04-29
- Product: MindCradle frontend
- Scope: Frontend-only wellness stats engine and live dashboard wiring
- Status: Approved for planning

## Summary

Build a client-side wellness stats engine that computes streaks, freeze awards, and a weekly calm score from local browser state. The engine will persist daily ritual history to `localStorage`, record non-ritual score events in a companion store, and keep dashboard stats live by dispatching `window.dispatchEvent(new CustomEvent("wellness:update"))` after every write. A shared hook, `useWellnessStats()`, will read those stores and expose the computed values needed by the dashboard and ritual completion screens.

This design intentionally keeps the feature in the frontend because the current app already relies heavily on client components and `localStorage`, and there is no existing backend contract for wellness stats. The implementation should preserve the existing visual language and use icons rather than emoji in all new or updated UI.

## Goals

- Compute a streak that increments on any day with Morning or Wind Down completed.
- Break streaks only after 24 hours pass with neither ritual completed, unless a freeze is consumed.
- Award 1 freeze for every 7-day streak milestone.
- Persist ritual history in the required array format:
  `[{ date, morningDone, windDownDone, usedFreeze }]`
- Compute a 0-100 weekly calm score from the last 7 calendar days including today.
- Expose a hook:
  `useWellnessStats(): { streak, calmScore, weeklyBreakdown, freezesAvailable }`
- Keep all dashboard stat surfaces live without prop drilling or a context provider.

## Non-Goals

- No new FastAPI routes or PocketBase schema changes.
- No auth-aware server synchronization for wellness stats in this iteration.
- No historical analytics beyond the last 7 days for calm score.
- No redesign of existing dashboard cards beyond wiring them to live data and replacing hardcoded values.

## Current Context

The frontend is a Next.js App Router app with a client-heavy dashboard. Existing mood, journal, morning, wind-down, and dashboard components already use client-side state and are the correct place to attach local persistence. The header and dashboard stats currently render hardcoded values, and no shared state layer exists for wellness metrics. Because the feature depends on `localStorage`, browser events, and custom hooks, the stats engine must live in client-only modules.

## Recommended Architecture

### 1. Pure wellness stats module

Create a pure utility layer responsible for:

- reading raw persisted wellness records
- normalizing malformed or missing data
- computing streak state
- computing freeze awards and freeze consumption
- computing weekly calm score and per-day breakdown

This module must not depend on React so it can be unit tested directly.

### 2. Local storage write helpers

Create a client-only persistence module responsible for:

- reading and writing the ritual history array
- reading and writing a companion activity map for score-only actions
- ensuring daily writes are idempotent
- dispatching `CustomEvent("wellness:update")` on `window` after every successful write

This module is the single write path for:

- Morning ritual completion
- Wind Down completion
- Mood saved
- Journal entry saved
- AI insight CTA clicked

### 3. Shared hook

Create `useWellnessStats()` as a client hook that:

- reads the computed stats on mount
- subscribes to `wellness:update`
- recomputes values whenever that event fires
- optionally also listens to the native `storage` event for cross-tab refresh

This replaces the need for prop drilling or a context provider.

## Data Model

### Required ritual history store

Key name should be centralized in one constants module.

```ts
type WellnessHistoryEntry = {
  date: string; // YYYY-MM-DD in local time
  morningDone: boolean;
  windDownDone: boolean;
  usedFreeze: boolean;
};
```

Persisted shape:

```ts
WellnessHistoryEntry[]
```

Rules:

- One entry per local calendar date.
- Repeated writes for the same date update the existing row instead of appending duplicates.
- `usedFreeze` is only set when a missed day is backfilled as freeze-consumed by the engine.

### Companion score activity store

The user requirement only fixes the ritual history shape, so score-only actions live in a second store.

```ts
type WellnessActivityEntry = {
  moodLogged?: boolean;
  journalEntry?: boolean;
  aiInsightRead?: boolean;
};

type WellnessActivityMap = Record<string, WellnessActivityEntry>;
```

Rules:

- Keys are `YYYY-MM-DD` in local time.
- Values are merged per day.
- Missing keys are treated as all-false.

## Event Contract

All local wellness writes must dispatch:

```ts
window.dispatchEvent(new CustomEvent("wellness:update"));
```

Dispatch occurs after:

- ritual history write success
- score activity write success
- any automatic freeze-consumption write performed by the engine

Listening contract:

- `useWellnessStats()` listens for `wellness:update` to refresh computed values immediately.
- The hook may also listen for native `storage` events so another tab can stay in sync.

## Streak Rules

### Day qualification

A day counts toward streak if either:

- `morningDone === true`
- `windDownDone === true`

If both are false, the day is a missed ritual day.

### Break window

The streak only breaks once 24 hours have passed since the last qualifying ritual activity without either ritual being completed in that window.

Interpretation for implementation:

- Use current local date/time when evaluating active streak state.
- If the user has not crossed a full 24-hour gap since the most recent qualifying day, preserve the current streak.
- If the gap crosses a missed calendar day and a freeze is available, consume exactly one freeze instead of breaking.
- If no freeze is available and the 24-hour miss condition is met, the streak resets.

### Freeze awards

- Award 1 freeze each time the user reaches another 7 qualifying streak days.
- Freeze awards are derived from the computed streak history, not manually entered.
- Freeze inventory is:
  total awarded freezes minus total consumed freezes

### Freeze consumption

- A freeze is consumed automatically only when a missed day would otherwise break the streak.
- Consuming a freeze marks the missed day in ritual history with:
  `morningDone: false`
  `windDownDone: false`
  `usedFreeze: true`
- One freeze covers one missed day only.

## Calm Score Rules

### Window

Use the last 7 calendar days including today in the user’s local timezone.

### Scoring per day

- Morning ritual completed: `+10`
- Wind Down completed: `+10`
- Mood logged: `+5`
- Journal entry saved: `+5`
- AI insight CTA clicked: `+5`

### Category caps

- Morning max: `70`
- Wind Down max: `70`
- Mood max: `35`
- Journal max: `35`
- AI insight max: `35`

### Total and normalization

- Maximum raw weekly total: `245`
- Final score:
  `Math.round((rawScore / 245) * 100)`
- Clamp final output to `0..100`

## Weekly Breakdown Shape

`weeklyBreakdown` should represent the same 7-day window used by calm score, ordered from oldest to newest, and include enough information for the dashboard dots and progress card.

Recommended shape:

```ts
type WeeklyBreakdownDay = {
  date: string;
  label: string; // Mon, Tue, etc.
  isFuture: boolean;
  morningDone: boolean;
  windDownDone: boolean;
  moodLogged: boolean;
  journalEntry: boolean;
  aiInsightRead: boolean;
  usedFreeze: boolean;
  rawPoints: number;
  dotStatus: "green" | "yellow" | "red" | "gray";
};
```

Dot status rules:

- `green`: both rituals complete
- `yellow`: exactly one ritual complete
- `red`: neither ritual complete and day is not future
- `gray`: future day

Note:

- A freeze-used day still renders `red` because the requirement defines dots by ritual completion, not streak preservation.

## Hook Contract

Expose:

```ts
type UseWellnessStatsResult = {
  streak: number;
  calmScore: number;
  weeklyBreakdown: WeeklyBreakdownDay[];
  freezesAvailable: number;
};
```

Hook behavior:

- Safe in client components only.
- Returns default zero-state values before browser storage is available.
- Recomputes on mount and on every `wellness:update`.
- Must avoid throwing if `localStorage` is empty or malformed.

## Write APIs

The implementation should provide small dedicated write helpers instead of exposing raw storage mutation to pages.

Recommended write entry points:

- `markMorningComplete()`
- `markWindDownComplete()`
- `markMoodLogged()`
- `markJournalEntrySaved()`
- `markAiInsightRead()`

Behavior:

- Each helper updates the correct store for today.
- Each helper is idempotent for repeated clicks or repeated renders.
- Each helper dispatches `wellness:update` once after mutation.

## UI Integration Plan

### Dashboard header

Replace hardcoded streak and calm score values in the header with `useWellnessStats()`.

- Streak uses the fire icon.
- Calm score keeps an icon-based stat treatment.
- If desired in a later pass, freezes can be surfaced with the ice icon, but this is not required for the first UI wiring.

### Greeting card

Replace hardcoded Morning and Wind Down completion state with today’s ritual status from wellness storage.

Completion details should reflect:

- done or pending state
- icons only, no emoji

### Weekly calm score card

Replace hardcoded score and dots with live data from `weeklyBreakdown`.

- Progress bar remains blue-to-green gradient.
- Dots use the required green, yellow, red, and gray states.

### Morning page

When the ritual reaches its completion state, persist today’s morning completion through the write helper before or at transition to the done screen.

### Wind Down page

Persist Wind Down completion when the user meaningfully completes the flow. For this iteration, the completion moment should be the transition into the active sleep/player state, since that is the existing terminal action that indicates the ritual has been completed.

### Mood page

Persist mood activity when the user saves successfully.

### Journal page

Persist journal activity when the entry save completes successfully.

### AI insight card

Persist `aiInsightRead` only when the CTA is clicked.

This explicitly does not count passive visibility of the card.

## Error Handling

- Invalid or corrupt `localStorage` payloads should fail soft by resetting to empty in-memory defaults.
- The hook should never throw during server rendering; browser-only access must stay inside client modules and effects or guarded reads.
- Repeated writes for the same date must not double-count streak or calm score categories.

## Testing Strategy

Use test-first development for the pure engine and storage helpers.

### Unit tests

Add a lightweight unit test setup for the frontend and cover:

- empty state computation
- one ritual day increments streak
- missed day breaks streak after the 24-hour rule
- freeze awarded at 7-day streak
- freeze consumed on one missed day
- calm score normalization and caps
- weekly breakdown dot status mapping
- idempotent same-day writes
- `wellness:update` dispatch on every write helper

### Integration confidence checks

Add at least one component-level test or narrow hook test to verify:

- `useWellnessStats()` refreshes when `wellness:update` fires

## Risks and Decisions

### Timezone handling

All persisted dates should be generated in local calendar time, not UTC date strings, to avoid late-night rollover bugs in wellness tracking.

### 24-hour break interpretation

The requirement says "Break if 24h pass with neither." This design interprets that literally rather than breaking at local midnight. The implementation must compare the current time against the most recent qualifying ritual day and preserve streak until a full 24-hour miss window has elapsed.

### Freeze visibility

The hook exposes `freezesAvailable`, but the first wiring pass only needs to compute it and make it available to UI consumers. Surface treatment can stay minimal unless the current frontend already has a good slot for it.

## Definition of Done

- Wellness stats are computed from persisted local state, not hardcoded UI values.
- `useWellnessStats()` returns live `streak`, `calmScore`, `weeklyBreakdown`, and `freezesAvailable`.
- Morning, Wind Down, Mood, Journal, and AI insight CTA writes update storage through shared helpers.
- Every write dispatches `CustomEvent("wellness:update")`.
- Header and weekly calm score card update live without prop drilling or a context provider.
- All new UI changes use icons instead of emoji.
- Automated tests cover the core engine and event refresh behavior.
