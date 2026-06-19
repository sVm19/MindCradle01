import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.services.supabase import pb, extract_user_id, _get_client
from app.utils.security import get_deterministic_hash

router = APIRouter()
logger = logging.getLogger(__name__)

class DeleteAccountRequest(BaseModel):
    password: str

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

    # 2. Verify password by logging in
    try:
        await pb.auth_with_password(email, get_deterministic_hash(req.password))
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
