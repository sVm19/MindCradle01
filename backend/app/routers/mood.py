from fastapi import APIRouter, Header, Query
from typing import Optional
from app.models.schemas import MoodCreate, MoodOut
from app.services.pocketbase import pb

router = APIRouter()


@router.post("")
async def log_mood(
    req: MoodCreate,
    authorization: Optional[str] = Header(None),
):
    """Save a mood entry for the authenticated user."""
    record = await pb.create_record(
        "mood_logs",
        {
            "level": req.level,
            "emotions": req.emotions,
            "note": req.note,
        },
        token=authorization,
    )
    return {"id": record["id"], "saved": True}


@router.get("")
async def get_mood_history(
    range: str = Query("7d", regex="^(7d|30d|90d|all)$"),
    authorization: Optional[str] = Header(None),
):
    """Get mood history for the authenticated user."""
    result = await pb.list_records(
        "mood_logs",
        token=authorization,
        params={"sort": "-created", "perPage": 100},
    )
    return {"items": result.get("items", []), "total": result.get("totalItems", 0)}
