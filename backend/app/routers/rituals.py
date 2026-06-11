from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import MorningRitualCreate, WindDownRitualCreate
from app.services.supabase import pb, extract_user_id

router = APIRouter()


@router.post("/morning")
async def save_morning_ritual(
    req: MorningRitualCreate,
    authorization: Optional[str] = Header(None),
):
    try:
        data = {
            "forecast": req.forecast,
            "intention": req.intention,
            "activity_type": req.activity_type,
            "completed_at": req.completed_at,
        }
        user_id = extract_user_id(authorization)
        if user_id:
            data["user"] = user_id
        record = await pb.create_record(
            "morning_rituals",
            data,
            token=authorization,
        )
        return {"id": record["id"], "saved": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/winddown")
async def save_winddown_ritual(
    req: WindDownRitualCreate,
    authorization: Optional[str] = Header(None),
):
    try:
        data = {
            "release_item": req.release_item,
            "gratitudes": req.gratitudes,
            "audio_choice": req.audio_choice,
            "timer": req.timer,
        }
        user_id = extract_user_id(authorization)
        if user_id:
            data["user"] = user_id
        record = await pb.create_record(
            "wind_down_rituals",
            data,
            token=authorization,
        )
        return {"id": record["id"], "saved": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
