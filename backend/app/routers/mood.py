import logging

from fastapi import APIRouter, Header, Query, Request, Depends, BackgroundTasks
from typing import Optional
from fastapi_csrf_protect import CsrfProtect
from app.models.schemas import MoodCreate, MoodOut
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
    """Save a mood entry for the authenticated user."""
    await csrf_protect.validate_csrf(request)
    logger.info(
        "Mood log request received: level=%s emotions=%s note_length=%s auth_present=%s",
        req.level,
        req.emotions,
        len(req.note or ""),
        authorization is not None,
    )

    from app.utils.sanitize import sanitize_mood_notes
    
    sanitized_note = sanitize_mood_notes(req.note) if req.note else ""
    data = {
        "level": req.level,
        "emotions": req.emotions,
        "note": sanitized_note,
    }
    user_id = extract_user_id(authorization)
    logger.info("Extracted user_id=%s from authorization header", user_id)
    if user_id:
        data["user"] = user_id

    record = await pb.create_record(
        "mood_logs",
        data,
        token=authorization,
    )
    logger.info("Mood record created: id=%s", record.get("id"))
    if user_id and sanitized_note:
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
    user_id = extract_user_id(authorization)
    logger.info(
        "Mood history request received: range=%s auth_present=%s user_id=%s",
        range,
        authorization is not None,
        user_id,
    )
    params = {"sort": "-created", "perPage": 100}
    if user_id:
        params["filter"] = f'user_id="{user_id}"'

    result = await pb.list_records(
        "mood_logs",
        token=authorization,
        params=params,
    )
    return {"items": result.get("items", []), "total": result.get("totalItems", 0)}
