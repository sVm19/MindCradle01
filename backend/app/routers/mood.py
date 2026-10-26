import logging

from fastapi import APIRouter, Header, Query, Request, Depends, BackgroundTasks, HTTPException
from typing import Optional
from fastapi_csrf_protect import CsrfProtect
from app.models.schemas import MoodCreate
from app.services.supabase import pb, extract_user_id
from app.services import knowledge_graph as kg_svc

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("")
async def log_mood(
    req: MoodCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    csrf_protect: CsrfProtect = Depends(),
):
    await csrf_protect.validate_csrf(request)
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from app.utils.sanitize import sanitize_mood_notes

    sanitized_note = sanitize_mood_notes(req.note) if req.note else ""
    data = {
        "user": user_id,
        "level": req.level,
        "emotions": req.emotions,
        "note": sanitized_note,
    }

    record = await pb.create_record(
        "mood_logs",
        data,
        token=authorization,
    )
    logger.info("Mood record created: id=%s for user_id=%s", record.get("id"), user_id)
    if sanitized_note:
        background_tasks.add_task(
            kg_svc.process_source,
            user_id,
            "mood",
            record["id"],
            sanitized_note,
            authorization
        )
    return {"id": record["id"], "saved": True}


@router.get("")
async def get_mood_history(
    range: str = Query("7d", pattern="^(7d|30d|90d|all)$"),
    authorization: Optional[str] = Header(None),
):
    """Get mood history for the authenticated user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    params = {
        "sort": "-created",
        "perPage": 100,
        "filter": f'user_id="{user_id}"'
    }

    result = await pb.list_records(
        "mood_logs",
        token=authorization,
        params=params,
    )
    return {"items": result.get("items", []), "total": result.get("totalItems", 0)}
