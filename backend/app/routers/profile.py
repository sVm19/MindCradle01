from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import ProfileMilestonesUpdate
from app.services.supabase import pb

router = APIRouter()


@router.patch("/milestones")
async def patch_milestones(
    req: ProfileMilestonesUpdate,
    authorization: Optional[str] = Header(None),
):
    try:
        return await pb.upsert_user_profile(
            authorization or "",
            {"unlocked_badges": req.unlocked_badges},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync milestones: {type(exc).__name__}: {exc}",
        ) from exc
