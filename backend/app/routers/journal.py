from fastapi import APIRouter, Header
from typing import Optional
from app.models.schemas import JournalCreate
from app.services.pocketbase import pb

router = APIRouter()


@router.post("")
async def create_entry(
    req: JournalCreate,
    authorization: Optional[str] = Header(None),
):
    """Save a journal entry for the authenticated user."""
    record = await pb.create_record(
        "journal_entries",
        {"prompt": req.prompt, "content": req.content},
        token=authorization,
    )
    return {"id": record["id"], "saved": True}


@router.get("")
async def list_entries(authorization: Optional[str] = Header(None)):
    """List journal entries for the authenticated user."""
    result = await pb.list_records(
        "journal_entries",
        token=authorization,
        params={"sort": "-created", "perPage": 50},
    )
    return {"items": result.get("items", []), "total": result.get("totalItems", 0)}
