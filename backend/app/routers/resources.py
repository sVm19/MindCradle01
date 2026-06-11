from fastapi import APIRouter, Query
from typing import Optional
from app.services.supabase import pb

router = APIRouter()


@router.get("")
async def list_resources(category: Optional[str] = Query(None)):
    """List all active resources, optionally filtered by category."""
    params = {"sort": "order", "filter": "is_active=true"}
    if category:
        params["filter"] += f' && category="{category}"'

    result = await pb.list_records("resources", params=params)
    return {"items": result.get("items", []), "total": result.get("totalItems", 0)}


@router.get("/{resource_id}")
async def get_resource(resource_id: str):
    """Get a single resource by ID."""
    record = await pb.get_record("resources", resource_id)
    return record
