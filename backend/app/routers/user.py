import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.services.supabase import pb, extract_user_id, _get_client
from app.utils.security import get_deterministic_hash

router = APIRouter()
logger = logging.getLogger(__name__)

class DeleteAccountRequest(BaseModel):
    password: Optional[str] = None


@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Return the authenticated user's id and email.
    Used by the frontend AuthProvider to verify that an access token
    stored in-memory (restored via refresh cookie) is still valid.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        client = _get_client(token)
        user_res = client.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=401, detail="User not found")

        return {
            "id": str(user_res.user.id),
            "email": user_res.user.email,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch current user: %s", e)
        raise HTTPException(status_code=401, detail="Could not verify token")

@router.get("/streak")
async def get_user_streak(authorization: Optional[str] = Header(None)):
    """
    Calculate and return the user's active streak based on consecutive days of engagement.
    Engagement includes: mood logs, journal entries, morning rituals, and wind down rituals.
    Also returns whether mood check-in is complete for today and yesterday.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        # Retrieve all user's engagement items from the last 30 days to build a robust streak
        since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        filter_user = f'user_id="{user_id}" && created >= "{since_30d}"'
        
        # Helper to fetch records
        async def fetch_records(collection: str, filter_str: str):
            try:
                res = await pb.list_records(collection, token=token, params={"filter": filter_str, "perPage": 100})
                return res.get("items") or []
            except Exception as e:
                logger.warning("Failed to fetch %s for streak: %s", collection, e)
                return []

        moods = await fetch_records("mood_logs", filter_user)
        journals = await fetch_records("journal_entries", filter_user)
        mornings = await fetch_records("morning_rituals", filter_user)
        wind_downs = await fetch_records("wind_down_rituals", filter_user)

        # Collect all engagement dates (YYYY-MM-DD in UTC)
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
        for wd in wind_downs:
            if wd.get("created"):
                engagement_dates.add(wd["created"][:10])

        now_utc = datetime.now(timezone.utc)
        today_str = now_utc.strftime("%Y-%m-%d")
        yesterday_str = (now_utc - timedelta(days=1)).strftime("%Y-%m-%d")
        
        streak_count = 0
        if yesterday_str in engagement_dates or today_str in engagement_dates:
            start_date = now_utc
            if today_str not in engagement_dates:
                start_date = start_date - timedelta(days=1)
            while True:
                date_str = start_date.strftime("%Y-%m-%d")
                if date_str in engagement_dates:
                    streak_count += 1
                    start_date = start_date - timedelta(days=1)
                else:
                    break
        
        # Calculate also the 7d active days (unique days with activity in last 7 days)
        since_7d = (now_utc - timedelta(days=7)).strftime("%Y-%m-%d")
        unique_dates_7d = {d for d in engagement_dates if d >= since_7d}
        
        # Check if mood check-in is complete for today and yesterday
        mood_dates = {m["created"][:10] for m in moods if m.get("created")}
        did_mood_checkin_today = today_str in mood_dates
        did_mood_checkin_yesterday = yesterday_str in mood_dates
        
        return {
            "streak": streak_count,
            "unique_days_7d": len(unique_dates_7d),
            "did_mood_checkin_today": did_mood_checkin_today,
            "did_mood_checkin_yesterday": did_mood_checkin_yesterday,
            "dates": sorted(list(engagement_dates))
        }
    except Exception as e:
        logger.error("Failed to calculate user streak: %s", e)
        raise HTTPException(status_code=500, detail="Could not calculate streak")

@router.get("/export-data")
async def export_user_data(authorization: Optional[str] = Header(None)):
    """
    Allow user to download ALL their data as JSON
    GDPR compliance: User right to access their data
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        # 1. Fetch user authentication details from Supabase Auth
        client = _get_client(token)
        user_res = client.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_info = {
            "id": user_res.user.id,
            "email": user_res.user.email,
            "created_at": user_res.user.created_at,
        }

        # Helper to safely fetch all items for a collection
        async def fetch_all(collection: str):
            try:
                res = await pb.list_records(
                    collection,
                    token=token,
                    params={"filter": f'user_id="{user_id}"', "perPage": 1000}
                )
                return res.get("items") or []
            except Exception as e:
                logger.warning("Could not fetch %s for export: %s", collection, e)
                return []

        # Fetch all user data across all tables
        mood_logs = await fetch_all("mood_logs")
        journal_entries = await fetch_all("journal_entries")
        ai_conversations = await fetch_all("ai_conversations")
        morning_rituals = await fetch_all("morning_rituals")
        wind_down_rituals = await fetch_all("wind_down_rituals")
        user_profiles = await fetch_all("user_profiles")
        user_memory_insights = await fetch_all("user_memory_insights")
        emotion_insights = await fetch_all("emotion_insights")
        advice_effectiveness = await fetch_all("advice_effectiveness")
        conversation_themes = await fetch_all("conversation_themes")
        user_personality = await fetch_all("user_personality")
        proactive_checkins = await fetch_all("proactive_checkins")
        recovery_data = await fetch_all("recovery_data")
        engagement_metrics = await fetch_all("engagement_metrics")
        crisis_flags = await fetch_all("crisis_flags")

        # Personal Knowledge Graph / CIE tables
        knowledge_nodes = await fetch_all("user_knowledge_nodes")
        knowledge_edges = await fetch_all("user_knowledge_edges")
        life_chapters = await fetch_all("user_life_chapters")
        behavioral_patterns = await fetch_all("user_behavioral_patterns")
        growth_metrics = await fetch_all("user_growth_metrics")
        entity_mentions = await fetch_all("user_entity_mentions")
        goal_threads = await fetch_all("user_goal_threads")

        data = {
            "user": user_info,
            "mood_logs": [
                {
                    "id": m.get("id"),
                    "level": m.get("level"),
                    "emotions": m.get("emotions", []),
                    "note": m.get("note"),
                    "created": m.get("created")
                }
                for m in mood_logs
            ],
            "journals": [
                {
                    "id": j.get("id"),
                    "prompt": j.get("prompt"),
                    "content": j.get("content"),
                    "ai_reflection": j.get("ai_reflection"),
                    "created": j.get("created")
                }
                for j in journal_entries
            ],
            "conversations": [
                {
                    "id": c.get("id"),
                    "messages": c.get("messages", []),
                    "summary": c.get("summary"),
                    "type": c.get("type"),
                    "created": c.get("created")
                }
                for c in ai_conversations
            ],
            "morning_rituals": morning_rituals,
            "wind_down_rituals": wind_down_rituals,
            "user_profile": user_profiles[0] if user_profiles else {},
            "user_memory_insights": user_memory_insights,
            "emotion_insights": emotion_insights,
            "advice_effectiveness": advice_effectiveness,
            "conversation_themes": conversation_themes,
            "user_personality": user_personality[0] if user_personality else {},
            "proactive_checkins": proactive_checkins,
            "recovery_data": recovery_data,
            "engagement_metrics": engagement_metrics,
            "crisis_flags": crisis_flags,
            "personal_knowledge_graph": {
                "nodes": knowledge_nodes,
                "edges": knowledge_edges,
                "chapters": life_chapters,
                "behavioral_patterns": behavioral_patterns,
                "growth_metrics": growth_metrics,
                "entity_mentions": entity_mentions,
                "goal_threads": goal_threads
            }
        }

        return {
            "data": data,
            "exported_at": datetime.utcnow().isoformat(),
            "note": "This file contains all your personal data exported from MindCradle"
        }
    except Exception as e:
        logger.error("Failed to export user data: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to export user data: {str(e)}")

@router.delete("/delete-account")
async def delete_account(
    req: DeleteAccountRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Delete user account and ALL associated data
    GDPR compliance: User right to be forgotten
    Requires password confirmation for safety
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 1. Fetch user email
    try:
        email = await pb.get_user_email(token)
    except Exception as e:
        logger.error("Failed to resolve email for delete account: %s", e)
        raise HTTPException(status_code=400, detail="Could not resolve email for active user session.")

    # 2. Verify password (only for legacy email/password users)
    try:
        client = _get_client(token)
        user_res = client.auth.get_user(token)
        is_google = False
        if user_res and user_res.user:
            app_metadata = getattr(user_res.user, "app_metadata", {}) or {}
            providers = app_metadata.get("providers", [])
            if "google" in providers or app_metadata.get("provider") == "google":
                is_google = True

        if not is_google:
            if not req.password:
                raise HTTPException(status_code=400, detail="Password is required for legacy accounts.")
            await pb.auth_with_password(email, get_deterministic_hash(req.password))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Incorrect password. Account deletion aborted.")

    # 3. Delete user account (cascading deletes wipe all data from DB tables)
    try:
        await pb.delete_user_account(token)
        logger.warning(
            f"USER_DELETED: {user_id} deleted their account at {datetime.utcnow().isoformat()}"
        )
        return {"message": "Account deleted. All data has been removed."}
    except Exception as e:
        logger.error("Failed to delete account: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")
