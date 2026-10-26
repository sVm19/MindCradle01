import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from app.config import CREEM_API_KEY, CREEM_API_URL, CREEM_PRODUCT_ID
from app.services.supabase import pb, extract_user_id
from app.core.security import generate_subscription_token
from app.utils.idempotency import execute_idempotent

logger = logging.getLogger(__name__)
router = APIRouter()

RESPONSES_COMMON = {
    401: {"description": "Unauthorized"},
    500: {"description": "Internal Server Error"},
}


def _get_auth_user(authorization: Optional[str]) -> tuple[str, str]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token, user_id


async def _ensure_trial_expired(user_id: str, token: str) -> None:
    profile_resp = await pb.list_records(
        "user_profiles",
        token=token,
        params={"filter": f'user_id="{user_id}"', "perPage": 1}
    )
    items = profile_resp.get("items") or []
    if not items:
        return

    profile = items[0]
    trial_ends_at_str = profile.get("trial_ends_at")
    if profile.get("trial_active") and trial_ends_at_str:
        trial_ends_at = datetime.fromisoformat(trial_ends_at_str.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) < trial_ends_at:
            raise HTTPException(status_code=400, detail="Trial is still active")


async def _call_creem_checkout(payload: dict, headers: dict) -> dict:
    base_url = CREEM_API_URL.rstrip('/')
    endpoint = base_url if ("/v1/" in base_url or "/checkout" in base_url) else f"{base_url}/v1/checkouts"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
    except httpx.RequestError:
        logger.exception("Connection error while contacting Creem API")
        return {"error": "Payment gateway communication failed. Please try again."}

    if response.status_code != 200:
        logger.error("Creem checkout creation failed: %s %s", response.status_code, response.text)
        return {"error": response.text}

    data = response.json()
    checkout_url = data.get("checkout_url") or data.get("url")
    if not checkout_url:
        logger.error("Creem response missing checkout_url: %s", data)
        return {"error": "Payment provider did not return a checkout URL"}

    if checkout_url.startswith("https://creem.io"):
        checkout_url = checkout_url.replace("https://creem.io", "https://www.creem.io", 1)
    return {"checkout_url": checkout_url}


@router.post("/start-trial", responses=RESPONSES_COMMON)
async def start_trial(
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Start 7-day free trial"""
    token, user_id = _get_auth_user(authorization)
    cache_key = f"trial:{user_id}:{idempotency_key}" if idempotency_key else None

    async def _do_start_trial():
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
            logger.exception("Error starting trial")
            raise HTTPException(status_code=500, detail=str(e))

    return await execute_idempotent(cache_key, _do_start_trial)


@router.get("/trial-status", responses=RESPONSES_COMMON)
async def get_trial_status(
    authorization: Optional[str] = Header(None)
):
    """Check trial status"""
    token, user_id = _get_auth_user(authorization)

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
        if days_remaining <= 0 and now < trial_ends_at:
            days_remaining = 1

        return {
            "trial_active": trial_active,
            "days_remaining": days_remaining,
            "trial_ends_at": trial_ends_at_str,
            "trial_used": trial_used
        }
    except Exception as e:
        logger.exception("Error checking trial status")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/creem-checkout", responses=RESPONSES_COMMON)
async def create_creem_checkout(
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Create Creem checkout session (after trial ends) with idempotency protection"""
    token, user_id = _get_auth_user(authorization)
    cache_key = f"creem:{user_id}:{idempotency_key}" if idempotency_key else None

    async def _do_create_creem_checkout():
        try:
            await _ensure_trial_expired(user_id, token)

            payload = {
                "product_id": CREEM_PRODUCT_ID,
                "success_url": "https://mindcradle.online/billing/success",
                "metadata": {
                    "user_id": user_id,
                    "idempotency_key": idempotency_key or ""
                }
            }

            headers = {
                "x-api-key": CREEM_API_KEY,
                "Content-Type": "application/json"
            }
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key

            return await _call_creem_checkout(payload, headers)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Unexpected error in create_creem_checkout")
            return {"error": "Internal server error"}

    return await execute_idempotent(cache_key, _do_create_creem_checkout)
