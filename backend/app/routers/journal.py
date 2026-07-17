from fastapi import APIRouter, Header, Request, Depends, BackgroundTasks
from typing import Optional
from fastapi_csrf_protect import CsrfProtect
from app.models.schemas import JournalCreate
from app.services.supabase import pb, extract_user_id
from app.services import knowledge_graph as kg_svc

router = APIRouter()


@router.post("")
async def create_entry(
    req: JournalCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    csrf_protect: CsrfProtect = Depends(),
):
    await csrf_protect.validate_csrf(request)
    from app.utils.sanitize import sanitize_journal_entry, sanitize_text
    
    sanitized_content = sanitize_journal_entry(req.content)
    sanitized_prompt = sanitize_text(req.prompt)
    sanitized_reflection = sanitize_text(req.ai_reflection) if req.ai_reflection else None
    
    data = {
        "prompt": sanitized_prompt,
        "content": sanitized_content,
        "ai_reflection": sanitized_reflection,
    }
    user_id = extract_user_id(authorization)
    if user_id:
        data["user"] = user_id

    record = await pb.create_record(
        "journal_entries",
        data,
        token=authorization,
    )
    if user_id and sanitized_content:
        background_tasks.add_task(
            kg_svc.process_source,
            user_id,
            "journal",
            record["id"],
            sanitized_content,
            authorization
        )
    return {"id": record["id"], "saved": True}


@router.get("")
async def list_entries(authorization: Optional[str] = Header(None)):
    """List journal entries for the authenticated user."""
    user_id = extract_user_id(authorization)
    params = {"sort": "-created", "perPage": 50}
    if user_id:
        params["filter"] = f'user_id="{user_id}"'

    result = await pb.list_records(
        "journal_entries",
        token=authorization,
        params=params,
    )
    return {"items": result.get("items", []), "total": result.get("totalItems", 0)}
