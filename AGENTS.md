# Analytics Tracking — Mixpanel

This project uses **Mixpanel** for all product analytics. Mixpanel is the single source of truth for event tracking, user identification, and behavioral data. Do not introduce any other analytics tools, SDKs, or tracking libraries without explicit instruction from a user.

---

## Before You Add or Modify Any Tracking

⛔ **Do not write Mixpanel tracking code without reading this file first.**

Wrong assumptions about platform, identity, or consent will produce broken Mixpanel data that requires manual cleanup or data deletion requests.

### Mandatory checklist before writing any Mixpanel code

- [x] Confirm you are using the correct Mixpanel SDK for this project's platform (see Tech Stack below)
- [x] Check if this project routes data through a CDP — if yes, send Mixpanel events through the CDP, not the Mixpanel SDK directly
- [x] Check if consent gating is required — if this project serves EU or California users, no Mixpanel events may fire before user consent
- [x] Review the existing Mixpanel tracking plan below before adding new events

---

## Tech Stack

| Detail | Value |
|---|---|
| **Platform** | React Web (Vite + TypeScript) |
| **Mixpanel SDK** | `mixpanel-browser` |
| **SDK version** | `^2.82.0` |
| **Tracking method** | Client-side web |
| **CDP (if any)** | None |
| **Consent required** | Yes (gated until privacy policy modal agreement) |
| **Mixpanel project token location** | `import.meta.env.VITE_MIXPANEL_TOKEN` (Default: `40463eebaef314c16e491842f0a591ae`) |

---

## Mixpanel Initialization

Mixpanel is initialized in:

**File:** [mixpanel.ts](file:///d:/WorkSpace/mindcradle/frontend/src/lib/mixpanel.ts)

```typescript
import mixpanel from 'mixpanel-browser';

const MIXPANEL_TOKEN = import.meta.env.VITE_MIXPANEL_TOKEN || '40463eebaef314c16e491842f0a591ae';

export const initMixpanel = (consentRequired: boolean) => {
  mixpanel.init(MIXPANEL_TOKEN, {
    debug: import.meta.env.DEV,
    track_pageview: false,
    opt_out_tracking_by_default: consentRequired,
  });
};

export { mixpanel };
```

**Do not:**
- Initialize Mixpanel in multiple places
- Create separate Mixpanel instances per component or module
- Import Mixpanel directly in feature files — use the shared initialization or `useGrowth().trackEvent`

---

## Mixpanel Identity

Mixpanel identity is managed through two calls:

| Action | When to call | Code location |
|---|---|---|
| `mixpanel.identify(user_id)` | On login or session restore | [auth.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/lib/auth.tsx) |
| `mixpanel.reset()` | On logout | [auth.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/lib/auth.tsx) |

**Rules:**
- Call `mixpanel.identify()` with a stable, internal user ID (database ID or UUID) — never use email addresses as the Mixpanel distinct_id
- Call `mixpanel.identify()` **after** the user record is confirmed (after DB write or on session restore)
- Call `mixpanel.reset()` on every logout path — this clears the Mixpanel distinct_id and generates a new anonymous ID
- Never call `mixpanel.identify()` with a different user ID without calling `mixpanel.reset()` first

---

## Mixpanel Tracking Plan

These are the Mixpanel events currently tracked in this project. **All new Mixpanel events must follow the same conventions.**

### Naming conventions

- Mixpanel event names: `snake_case`, past tense verb + noun (e.g., `morning_ritual_completed`, `journal_entry_created`)
- Mixpanel property names: `snake_case` (e.g., `sign_up_method`, `plan_type`)
- No abbreviations in Mixpanel event or property names — use full words
- Boolean Mixpanel properties: use `is_` prefix (e.g., `is_first_time`)

### Current Mixpanel events

| Mixpanel Event | Trigger | Key Properties | File |
|---|---|---|---|
| `page_view` | Route change in layout context | `path`, `url`, `referrer` | [App.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/app/App.tsx) |
| `morning_habit_click` | User clicks an activity card during morning focus | `activity_id`, `layout_variant` | [Morning.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Morning.tsx) |
| `morning_ritual_completed` | User completes the morning routine flow | `activity_id`, `layout_variant` | [Morning.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Morning.tsx) |
| `mood_checkin_completed` | User completes state of calm and emotion check-in | `mood_level`, `emotions_count`, `note_length` | [Mood.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Mood.tsx) |
| `journal_entry_created` | User saves journal entry with or without AI reflection | `word_count`, `has_reflection`, `char_length` | [Journal.tsx](file:///d:/WorkSpace/mindcradle/frontend/src/app/pages/Journal.tsx) |

---

## How to Add a New Mixpanel Event

1. **Check the tracking plan above** — if the Mixpanel event already exists, use it. Do not create duplicate Mixpanel events.
2. **Name the Mixpanel event** using the conventions above: `snake_case`, past tense, descriptive.
3. **Define Mixpanel properties** — only include properties available at the moment the event fires. Do not fetch additional data just for Mixpanel tracking.
4. **Place the Mixpanel tracking call** at the right moment:
   - Track Mixpanel events via `useGrowth().trackEvent(eventName, properties)` so it routes through standard contexts
   - Track Mixpanel events **after** the action succeeds (after DB write, after API response)
5. **Update this file** — add the new Mixpanel event to the tracking plan table above.
6. **Verify in Mixpanel Live View** — confirm the event appears in Mixpanel with correct properties before considering it done.

### Mixpanel event template

```typescript
const { trackEvent } = useGrowth();

// Track event in Mixpanel
trackEvent('[event_name]', {
  property_name: value,
  property_name: value,
});
```

---

## What Not to Do

- **Do not introduce other analytics tools.** This project uses Mixpanel. All tracking goes through Mixpanel.
- **Do not track Mixpanel events on page load** unless explicitly measuring page views. Mixpanel events represent user actions, not navigation.
- **Do not track PII as Mixpanel properties** — no emails, full names, phone numbers, IP addresses, or payment details in Mixpanel event properties.
- **Do not fire Mixpanel events inside loops** — each Mixpanel event call is a network request.
- **Do not hardcode the Mixpanel project token** — read it from environment config.
- **Do not skip `mixpanel.reset()` on logout** — failing to reset causes Mixpanel to merge the next user's events with the previous user's profile.
- **Do not call `mixpanel.identify()` before the user is authenticated** — premature identification creates orphaned Mixpanel profiles.
