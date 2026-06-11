from fastapi import APIRouter, Header
from typing import Optional
from app.models.schemas import JournalCreate
from app.services.supabase import pb, extract_user_id

router = APIRouter()


@router.post("")
async def create_entry(
    req: JournalCreate,
    authorization: Optional[str] = Header(None),
):
    """Save a journal entry for the authenticated user."""
    data = {"prompt": req.prompt, "content": req.content}
    user_id = extract_user_id(authorization)
    if user_id:
        data["user"] = user_id

    record = await pb.create_record(
        "journal_entries",
        data,
        token=authorization,
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
