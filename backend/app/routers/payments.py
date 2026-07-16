import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
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
            
        
        payload = {
            "product_id": CREEM_PRODUCT_ID,
            "success_url": "https://mindcradle.online/billing/success",
            "customer_email": email,
            "metadata": {
                "user_id": user_id
            }
        }
        
        headers = {
            "x-api-key": CREEM_API_KEY,
            "Content-Type": "application/json"
        }
        
        base_url = CREEM_API_URL.rstrip('/')
        if "/v1/" in base_url or "/checkout" in base_url:
            endpoint = base_url
        else:
            endpoint = f"{base_url}/v1/checkouts"
            
        logger.info("Creating Creem checkout session via endpoint: %s", endpoint)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
        except httpx.RequestError as exc:
            logger.error("Connection error while contacting Creem API: %s", exc)
            raise HTTPException(
                status_code=400,
                detail="Payment gateway communication failed. Please try again."
            )
            
        if response.status_code == 200:
            data = response.json()
            checkout_url = data.get("checkout_url") or data.get("url")
            if not checkout_url:
                logger.error("Creem response missing checkout_url: %s", data)
                raise HTTPException(status_code=400, detail="Payment provider did not return a checkout URL")
            return {"checkout_url": checkout_url}
        else:
            logger.error("Creem checkout creation failed: %s %s", response.status_code, response.text)
            error_msg = "Failed to create checkout session with Creem"
            try:
                err_data = response.json()
                if "message" in err_data:
                    error_msg = f"{error_msg}: {err_data['message']}"
            except Exception:
                if response.text:
                    error_msg = f"{error_msg}: {response.text[:100]}"
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in create_creem_checkout: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
