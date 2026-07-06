import logging
import re
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request
from app.config import CREEM_API_KEY, CREEM_API_URL, CREEM_PRODUCT_ID
from app.services.supabase import pb, extract_user_id, extract_user_email
from app.core.security import generate_subscription_token

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/start-trial")
async def start_trial(
    authorization: Optional[str] = Header(None)
):
    """Start 7-day free trial"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        profile_resp = await pb.list_records(
            "user_profiles",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = profile_resp.get("items") or []
        
        if items and items[0].get("trial_used"):
            raise HTTPException(status_code=400, detail="Trial already used")
            
        trial_started = datetime.now(timezone.utc)
        trial_ends = trial_started + timedelta(days=7)
        sub_token = generate_subscription_token(user_id, trial_ends)
        
        payload = {
            "trial_started_at": trial_started.isoformat(),
            "trial_ends_at": trial_ends.isoformat(),
            "trial_used": True,
            "trial_active": True,
            "is_premium": True,
            "subscription_expires_at": trial_ends.isoformat(),
            "subscription_token": sub_token
        }
        
        if items:
            profile_id = items[0]["id"]
            await pb.update_record("user_profiles", profile_id, payload, token=token)
        else:
            payload["user_id"] = user_id
            await pb.create_record("user_profiles", payload, token=token)
            
        return {
            "success": True,
            "trial_ends_at": trial_ends.isoformat(),
            "message": "7-day trial started"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting trial: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trial-status")
async def get_trial_status(
    authorization: Optional[str] = Header(None)
):
    """Check trial status"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        profile_resp = await pb.list_records(
            "user_profiles",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = profile_resp.get("items") or []
        if not items:
            return {"trial_active": False, "days_remaining": 0, "trial_used": False}
            
        profile = items[0]
        trial_started_at = profile.get("trial_started_at")
        trial_ends_at_str = profile.get("trial_ends_at")
        trial_used = bool(profile.get("trial_used"))
        trial_active = bool(profile.get("trial_active"))
        
        if not trial_started_at or not trial_ends_at_str:
            return {"trial_active": False, "days_remaining": 0, "trial_used": trial_used}
            
        trial_ends_at = datetime.fromisoformat(trial_ends_at_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        
        if now >= trial_ends_at:
            if trial_active:
                payload = {
                    "trial_active": False,
                    "is_premium": False,
                    "subscription_expires_at": None,
                    "subscription_token": None
                }
                await pb.update_record("user_profiles", profile["id"], payload, token=token)
            return {"trial_active": False, "days_remaining": 0, "trial_used": trial_used}
            
        diff = trial_ends_at - now
        days_remaining = diff.days
        # Ensure we return at least 1 day remaining if active and not yet expired
        if days_remaining <= 0 and now < trial_ends_at:
            days_remaining = 1
            
        return {
            "trial_active": trial_active,
            "days_remaining": days_remaining,
            "trial_ends_at": trial_ends_at_str,
            "trial_used": trial_used
        }
    except Exception as e:
        logger.error("Error checking trial status: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/creem-checkout")
async def create_creem_checkout(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Create Creem checkout session (after trial ends)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        # Check if trial still active
        profile_resp = await pb.list_records(
            "user_profiles",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = profile_resp.get("items") or []
        if items:
            profile = items[0]
            trial_active = bool(profile.get("trial_active"))
            trial_ends_at_str = profile.get("trial_ends_at")
            if trial_active and trial_ends_at_str:
                trial_ends_at = datetime.fromisoformat(trial_ends_at_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) < trial_ends_at:
                    raise HTTPException(status_code=400, detail="Trial is still active")
                    
        email = extract_user_email(token)
        if not email:
            raise HTTPException(status_code=400, detail="Could not extract email from token")
            
        # Get Referer or Host for dynamic redirect URLs
        referer = request.headers.get("referer") or request.headers.get("host") or "https://mindcradle.online"
        host_match = re.match(r"^(https?://[^/]+)", referer)
        host = host_match.group(1) if host_match else referer.rstrip("/")
        
        payload = {
            "email": email,
            "product_id": CREEM_PRODUCT_ID,
            "success_url": f"{host}/billing?success=true",
            "cancel_url": f"{host}/billing?success=false",
            "metadata": {
                "user_id": user_id
            }
        }
        
        headers = {
            "x-api-key": CREEM_API_KEY,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CREEM_API_URL}/checkout",
                json=payload,
                headers=headers
            )
            
        if response.status_code == 200:
            return {"checkout_url": response.json().get("url")}
        else:
            logger.error("Creem checkout creation failed: %s %s", response.status_code, response.text)
            raise HTTPException(status_code=502, detail="Failed to create checkout session with Creem")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in create_creem_checkout: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
