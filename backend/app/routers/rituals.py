from typing import Optional

from fastapi import APIRouter, Header

from app.models.schemas import MorningRitualCreate, WindDownRitualCreate
from app.services.pocketbase import pb

router = APIRouter()


@router.post("/morning")
async def save_morning_ritual(
    req: MorningRitualCreate,
    authorization: Optional[str] = Header(None),
):
    data = {
        "forecast": req.forecast,
        "intention": req.intention,
        "activity_type": req.activity_type,
        "completed_at": req.completed_at,
    }
    if authorization:
        import base64
        import json
        payload = authorization.split('.')[1]
        decoded = base64.urlsafe_b64decode(payload + '==')
        data_dict = json.loads(decoded)
        user_id = data_dict['id']
        data["user"] = user_id
    record = await pb.create_record(
        "morning_rituals",
        data,
        token=authorization,
    )
    return {"id": record["id"], "saved": True}


@router.post("/winddown")
async def save_winddown_ritual(
    req: WindDownRitualCreate,
    authorization: Optional[str] = Header(None),
):
    data = {
        "release_item": req.release_item,
        "gratitudes": req.gratitudes,
        "audio_choice": req.audio_choice,
        "timer": req.timer,
    }
    if authorization:
        import base64
        import json
        payload = authorization.split('.')[1]
        decoded = base64.urlsafe_b64decode(payload + '==')
        data_dict = json.loads(decoded)
        user_id = data_dict['id']
        data["user"] = user_id
    record = await pb.create_record(
        "wind_down_rituals",
        data,
        token=authorization,
    )
    return {"id": record["id"], "saved": True}
