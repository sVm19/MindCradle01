import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from fastapi import APIRouter, Header, HTTPException

from app.services.supabase import pb, extract_user_id
from app.core.security import verify_user_premium

router = APIRouter()
logger = logging.getLogger(__name__)

# Server-side cache to control AI API costs and network overhead
# Key: user_id, Value: (expiry_timestamp, widget_payload_dict)
WIDGET_CACHE: Dict[str, Tuple[datetime, dict]] = {}
CACHE_DURATION_HOURS = 4

# Curated daily reflective questions (fallback/randomized pool)
REFLECTIVE_QUESTIONS = [
    "What deserves less of your attention today?",
    "What is one small thing that brought you peace recently?",
    "Who is someone you appreciate having in your life right now?",
    "What boundary did you set or need to set this week?",
    "How does your body feel in this current moment?",
    "What is a personal quality you've been proud of lately?",
    "What is one thing you can let go of to make today lighter?",
    "What does success look like for you today?",
    "What made you smile in the last 24 hours?",
    "What is a goal you're working toward, and what's the next tiny step?",
    "How can you show yourself kindness in the next hour?",
    "What are you looking forward to about tomorrow?",
    "What is a lesson a recent challenge taught you?",
    "What distraction did you overcome today?",
    "What was the highlight of your morning?"
]

@router.get("/home")
async def get_widgets_consolidated(
    authorization: Optional[str] = Header(None)
):
    """
    Get consolidated native home-screen widget payload.
    Supports in-memory caching to save AI API call costs and database requests.
    Respects user privacy settings from user_profiles.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    now = datetime.now(timezone.utc)

    # 1. Check cache
    if user_id in WIDGET_CACHE:
        expiry, cached_payload = WIDGET_CACHE[user_id]
        if now < expiry:
            return cached_payload

    try:
        # 2. Fetch User Profile & Preferences
        profile_res = await pb.list_records("user_profiles", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
        profile_items = profile_res.get("items") or []
        profile = profile_items[0] if profile_items else {}

        # Extract preferences with default fallbacks
        personalized_enabled = profile.get("widget_personalized_enabled", True)
        memories_enabled = profile.get("widget_memories_enabled", True)
        aria_personalized_enabled = profile.get("widget_aria_personalized_enabled", True)
        sensitive_enabled = profile.get("widget_sensitive_enabled", False)

        is_premium, _ = verify_user_premium(profile, user_id)

        # 3. Retrieve database items for calculations
        since_30d = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        filter_user = f'user_id="{user_id}" && created >= "{since_30d}"'

        async def fetch_records(collection: str, filter_str: str):
            try:
                res = await pb.list_records(collection, token=token, params={"filter": filter_str, "perPage": 100})
                return res.get("items") or []
            except Exception as exc:
                logger.warning("Widgets API: failed to fetch %s: %s", collection, exc)
                return []

        moods = await fetch_records("mood_logs", filter_user)
        journals = await fetch_records("journal_entries", filter_user)
        mornings = await fetch_records("morning_rituals", filter_user)
        winddowns = await fetch_records("wind_down_rituals", filter_user)

        # 4. Calculate Streak
        engagement_dates = set()
        for m in moods:
            if m.get("created"):
                engagement_dates.add(m["created"][:10])
        for j in journals:
            if j.get("created"):
                engagement_dates.add(j["created"][:10])
        for mr in mornings:
            if mr.get("created"):
                engagement_dates.add(mr["created"][:10])
        for wd in winddowns:
            if wd.get("created"):
                engagement_dates.add(wd["created"][:10])

        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        streak_count = 0
        if yesterday_str in engagement_dates or today_str in engagement_dates:
            start_date = now
            if today_str not in engagement_dates:
                start_date = now - timedelta(days=1)
            while True:
                date_str = start_date.strftime("%Y-%m-%d")
                if date_str in engagement_dates:
                    streak_count += 1
                    start_date = start_date - timedelta(days=1)
                else:
                    break

        did_mood_today = today_str in {m["created"][:10] for m in moods if m.get("created")}

        # 5. Compile Widgets Payload
        payload = {
            "version": 1,
            "generatedAt": now.isoformat(),
            "expiresAt": (now + timedelta(hours=CACHE_DURATION_HOURS)).isoformat(),
            "user": {
                "id": user_id,
                "isPremium": is_premium
            },
            "preferences": {
                "personalizedEnabled": personalized_enabled,
                "memoriesEnabled": memories_enabled,
                "ariaPersonalizedEnabled": aria_personalized_enabled,
                "sensitiveEnabled": sensitive_enabled
            }
        }

        # --- ARIA WIDGET ---
        aria_msg = "How are you feeling today?"
        if personalized_enabled and aria_personalized_enabled:
            # Look at recent mood/life chapters to tailor ARIA message
            recent_moods = sorted(moods, key=lambda x: x.get("created", ""), reverse=True)
            if recent_moods and not sensitive_enabled:
                latest_level = int(recent_moods[0].get("level") or 5)
                if latest_level >= 8:
                    aria_msg = "You seemed more energized yesterday. How are you feeling today?"
                elif latest_level <= 4:
                    aria_msg = "I'm here for you. How are you feeling right now?"
            else:
                aria_msg = "Before your day gets busy, what's one thing you'd like to make space for today?"
        payload["aria"] = {
            "message": aria_msg,
            "action": "open_aria"
        }

        # --- QUICK JOURNAL WIDGET ---
        payload["journal"] = {
            "prompt": "What's on your mind?",
            "action": "open_journal"
        }

        # --- DAILY INSIGHT WIDGET ---
        insight_text = "Keep journaling. MindCradle will begin discovering patterns as your history grows."
        insight_available = False
        if personalized_enabled:
            try:
                # Try loading daily discovery
                since_24h = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
                disc_res = await pb.list_records(
                    "daily_discoveries",
                    token=token,
                    params={"filter": f'user_id="{user_id}" && created_at >= "{since_24h}"', "sort": "-created_at", "perPage": 1}
                )
                items = disc_res.get("items") or []
                if items and not sensitive_enabled:
                    insight_text = items[0].get("discovery_text") or insight_text
                    insight_available = True
            except Exception as e:
                logger.warning("Widgets API: failed to fetch daily discovery: %s", e)
        payload["insight"] = {
            "text": insight_text,
            "available": insight_available,
            "action": "open_insight"
        }

        # --- MEMORY WIDGET ---
        memory_text = "Keep reflecting. MindCradle will preserve your meaningful moments here as your history grows."
        memory_available = False
        if personalized_enabled and memories_enabled and not sensitive_enabled:
            try:
                # Retrieve from user_relationship_memories
                mem_res = await pb.list_records(
                    "user_relationship_memories",
                    token=token,
                    params={"filter": f'user_id="{user_id}"', "sort": "-importance,-last_occurrence", "perPage": 5}
                )
                memories = mem_res.get("items") or []
                
                # Retrieve from user_memory_insights as fallback
                ins_res = await pb.list_records(
                    "user_memory_insights",
                    token=token,
                    params={"filter": f'user_id="{user_id}"', "sort": "-created", "perPage": 5}
                )
                insights = ins_res.get("items") or []

                if memories:
                    title = memories[0].get("title")
                    m_type = memories[0].get("type")
                    memory_text = f"Remember when you noticed this {m_type}: '{title}'?"
                    memory_available = True
                elif insights:
                    situation = insights[0].get("situation") or insights[0].get("what_happened")
                    if situation:
                        memory_text = f"A while ago you wrote: '{situation}'"
                        memory_available = True
            except Exception as e:
                logger.warning("Widgets API: failed to fetch memories: %s", e)
        payload["memory"] = {
            "text": memory_text,
            "available": memory_available,
            "action": "open_memory"
        }

        # --- DAILY QUESTION WIDGET ---
        # Select daily question deterministically based on date to maintain stability during the day
        day_of_year = now.timetuple().tm_yday
        q_idx = day_of_year % len(REFLECTIVE_QUESTIONS)
        payload["dailyQuestion"] = {
            "text": REFLECTIVE_QUESTIONS[q_idx],
            "action": "open_reflection"
        }

        # --- MOOD CHECK-IN WIDGET ---
        payload["mood"] = {
            "completed": did_mood_today,
            "action": "open_mood"
        }

        # --- HABIT PULSE WIDGET ---
        morning_completed = len([m for m in mornings if m.get("created", "")[:10] == today_str]) > 0
        winddown_completed = len([w for w in winddowns if w.get("created", "")[:10] == today_str]) > 0
        
        payload["habit"] = {
            "morningCompleted": morning_completed,
            "winddownCompleted": winddown_completed,
            "moodCompleted": did_mood_today,
            "action": "open_home"
        }

        # --- STREAK WIDGET ---
        payload["streak"] = {
            "days": streak_count,
            "message": "Start again today." if streak_count == 0 else f"You've checked in {streak_count} days in a row.",
            "action": "open_home"
        }

        # --- SOLSTICE WIDGET ---
        solstice_msg = "You don't need to solve everything today. Some things become clearer when you give them space."
        payload["solstice"] = {
            "message": solstice_msg,
            "available": is_premium,
            "action": "open_solstice"
        }

        # 6. Save cache
        expiry_time = now + timedelta(hours=CACHE_DURATION_HOURS)
        WIDGET_CACHE[user_id] = (expiry_time, payload)

        return payload

    except Exception as e:
        logger.error("Widgets API error: %s", e)
        # Safe fallback payload in case of errors
        return {
            "version": 1,
            "generatedAt": now.isoformat(),
            "expiresAt": (now + timedelta(minutes=15)).isoformat(),
            "user": {"id": user_id, "isPremium": False},
            "aria": {"message": "How are you feeling today?", "action": "open_aria"},
            "journal": {"prompt": "What's on your mind?", "action": "open_journal"},
            "insight": {"text": "Connect online to retrieve daily insights.", "available": False, "action": "open_insight"},
            "memory": {"text": "Connect online to retrieve your memories.", "available": False, "action": "open_memory"},
            "dailyQuestion": {"text": "What deserves less of your attention today?", "action": "open_reflection"},
            "mood": {"completed": False, "action": "open_mood"},
            "habit": {"morningCompleted": False, "winddownCompleted": False, "moodCompleted": False, "action": "open_home"},
            "streak": {"days": 0, "message": "Ready for another day?", "action": "open_home"},
            "solstice": {"message": "Give yourself space to reflect today.", "available": False, "action": "open_solstice"}
        }
