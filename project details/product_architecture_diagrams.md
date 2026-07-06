# MindCradle Product Architecture & Flows

This document visualizes how users interact with the MindCradle platform, how pages are structured, and how data flows through the system.

````carousel
### 1. User Flow Diagram
Describes how both guest and authenticated users move through the main paths of the application.

```mermaid
graph TD
    Start([Guest User]) --> Land[Landing / Dashboard Guest Hero]
    Land --> AuthChoice{Has Account?}
    AuthChoice -- No --> SignUp[Sign Up Form]
    AuthChoice -- Yes --> Login[Login / Magic Token Verification]
    SignUp --> VerifyEmail[Email Verification / Onboarding]
    Login --> AuthDash[Authenticated Dashboard]
    VerifyEmail --> AuthDash
    AuthDash --> Action{User Action}
    Action --> Mood[Mood Logger]
    Action --> Ritual[Rituals morning/evening]
    Action --> Journal[Journal writing]
    Action --> ARIA[ARIA Chat / Reflection]
    Action --> Billing[Billing / Premium Trial]
```
<!-- slide -->
### 2. Site Map
Outlines every page/route in the application and its core purpose.

```mermaid
graph LR
    Root[MindCradle app] --> Dashboard["/dashboard: Main Wellness hub"]
    Root --> Morning["/morning: Morning & Evening Rituals"]
    Root --> Mood["/mood: Mood tracking & logging"]
    Root --> Journal["/journal: Daily reflections logger"]
    Root --> ARIA["/aria: AI chat companion"]
    Root --> Settings["/settings: Profile, notifications & account management"]
    Root --> Billing["/billing: Checkout, Success, Cancel redirects"]
    Root --> Info["Static Pages: /pricing, /about, /privacy, /terms, /refund"]
```
<!-- slide -->
### 3. Feature Flow
Shows the technical data paths for the main interaction loops in the application.

```mermaid
graph TD
    subgraph ARIA Chat Flow
        A[User writes message] --> B[FastAPI decrypts context]
        B --> C[Fetch past mood/ritual context from database]
        C --> D[Secure AI completion with ARIA persona]
        D --> E[Log response & return reflections to User]
    end
    subgraph Ritual Log Flow
        F[Select morning/evening activity] --> G[Complete exercises breathing/reflection]
        G --> H[Update streak counter]
        H --> I[Save log to DB]
    end
```
<!-- slide -->
### 4. Onboarding Flow
First-time user experience when activating an account for the first time.

```mermaid
graph TD
    Start[User registers] --> Welcome["Welcome prompt (Serene style)"]
    Welcome --> InitialMood["Log current emotional state"]
    InitialMood --> FirstRitual["Guided 1-minute breathing exercise"]
    FirstRitual --> DashboardIntroduction["Interactive feature highlight overlay"]
    DashboardIntroduction --> End([Activated Dashboard])
```
<!-- slide -->
### 5. Subscription/Checkout Flow
Tracks the journey through free trial activation, expiration, and premium checkout.

```mermaid
graph TD
    Start[User goes to /billing] --> CheckTrial{Trial Used?}
    CheckTrial -- No --> StartTrial[Start 7-Day Free Trial]
    StartTrial --> ActiveTrial[Premium access active for 7 days]
    ActiveTrial --> ExpiryCheck{7 days passed?}
    ExpiryCheck -- Yes --> Deactivate[Trial expired & lock features]
    Deactivate --> PayButton[Show 'Pay with Creem' button]
    CheckTrial -- Yes --> PayButton
    PayButton --> CreemCheckout[Redirect to Creem Checkout Portal]
    CreemCheckout --> Webhook[Creem Webhook verifies payment]
    Webhook --> SubActive[Subscription active & Premium unlocked]
```
<!-- slide -->
### 6. Information Architecture
Structural taxonomy and hierarchy of elements inside MindCradle.

```mermaid
graph TD
    IA[Content Organization] --> CoreModules[Core Modules]
    IA --> StaticPages[Static Pages]
    IA --> UserAccounts[User Profiles & System]
    
    CoreModules --> M1["Dashboard: Calm index, Streaks"]
    CoreModules --> M2["Daily Rituals: Breathing, Affirmations"]
    CoreModules --> M3["Mood & Journal: Emotion tags, Rich text logs"]
    CoreModules --> M4["ARIA Companion: AI prompts, Analysis logs"]
    
    StaticPages --> S1["Pricing plans"]
    StaticPages --> S2["Privacy, Terms & Refund policies"]
    
    UserAccounts --> U1["Supabase Auth & Session tokens"]
    UserAccounts --> U2["Premium/Trial subscription status"]
```
<!-- slide -->
### 7. Database & System Architecture
A high-level view of how frontend, backend services, database schema, and payment APIs connect.

```mermaid
graph TD
    Client[React/TS Frontend] -->|HTTPS Requests| Backend[FastAPI Backend]
    Client -->|Auth / Direct queries| DB[(Supabase Database)]
    Backend -->|RPC Actions| DB
    Backend -->|Background tasks| Scheduler[AsyncIOScheduler]
    Scheduler -->|check_expired_trials| DB
    Backend -->|Create checkout| Creem[Creem API]
    Creem -->|Send webhooks| Backend
```
<!-- slide -->
### 8. Analytics & Event Map
Actions and metrics tracked for insight and recovery patterns.

```mermaid
graph TD
    Track[Telemetry events] --> E1["mood_logged: level, tags"]
    Track --> E2["ritual_completed: type, streak_updated"]
    Track --> E3["aria_message_sent: user_id, length"]
    Track --> E4["trial_started: user_id, timestamp"]
    Track --> E5["checkout_completed: user_id, creem_id"]
```
````
