from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import ProfileMilestonesUpdate, ProfileResponse, ProfileUpdate
from app.services.supabase import pb, extract_user_id

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


@router.get("", response_model=ProfileResponse)
async def get_profile(
    authorization: Optional[str] = Header(None),
):
    """Retrieve the current user's profile."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        res = await pb.list_records("user_profiles", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
        items = res.get("items") or []
        if items:
            i = items[0]
            return ProfileResponse(
                id=i["id"],
                user_id=i["user_id"],
                unlocked_badges=i.get("unlocked_badges"),
                badge_history=i.get("badge_history"),
                emergency_contact=i.get("emergency_contact"),
                notify_on_crisis=i.get("notify_on_crisis", False),
                created=i.get("created") or i.get("created_at") or ""
            )
        # Create a new profile if it doesn't exist
        new_prof = await pb.create_record("user_profiles", {"user": user_id}, token=token)
        return ProfileResponse(
            id=new_prof["id"],
            user_id=new_prof["user_id"],
            unlocked_badges=new_prof.get("unlocked_badges") or [],
            badge_history=new_prof.get("badge_history") or [],
            emergency_contact=new_prof.get("emergency_contact"),
            notify_on_crisis=new_prof.get("notify_on_crisis", False),
            created=new_prof.get("created") or new_prof.get("created_at") or ""
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")


@router.patch("", response_model=ProfileResponse)
async def patch_profile(
    req: ProfileUpdate,
    authorization: Optional[str] = Header(None),
):
    """Update current user's profile metadata (e.g. emergency contact)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        # Check if profile exists
        res = await pb.list_records("user_profiles", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
        items = res.get("items") or []
        
        payload = {}
        if req.emergency_contact is not None:
            payload["emergency_contact"] = req.emergency_contact
        if req.notify_on_crisis is not None:
            payload["notify_on_crisis"] = req.notify_on_crisis
            
        if items:
            profile_id = items[0]["id"]
            updated = await pb.update_record("user_profiles", profile_id, payload, token=token)
        else:
            payload["user"] = user_id
            updated = await pb.create_record("user_profiles", payload, token=token)
            
        return ProfileResponse(
            id=updated["id"],
            user_id=updated["user_id"],
            unlocked_badges=updated.get("unlocked_badges"),
            badge_history=updated.get("badge_history"),
            emergency_contact=updated.get("emergency_contact"),
            notify_on_crisis=updated.get("notify_on_crisis", False),
            created=updated.get("created") or updated.get("created_at") or ""
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")
