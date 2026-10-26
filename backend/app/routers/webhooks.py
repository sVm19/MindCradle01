import hmac
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Header
from app.config import CREEM_WEBHOOK_SECRET, ENVIRONMENT
from app.services.supabase import pb
from app.core.security import get_supabase_token_for_user, generate_subscription_token

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify_creem_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Verify incoming Creem webhook HMAC-SHA256 signature."""
    if not CREEM_WEBHOOK_SECRET:
        if ENVIRONMENT == "production":
            logger.error("CREEM_WEBHOOK_SECRET is not configured in production.")
            return False
        logger.warning("CREEM_WEBHOOK_SECRET is not set; skipping signature verification in development.")
        return True

    if not signature_header:
        logger.warning("Creem webhook rejected: Missing signature header.")
        return False

    expected_signature = hmac.new(
        CREEM_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    # Compare case-insensitively using constant-time comparison
    return hmac.compare_digest(expected_signature.lower(), signature_header.strip().lower())


@router.post("/creem")
async def creem_webhook(
    request: Request,
    x_creem_signature: Optional[str] = Header(None, alias="x-creem-signature"),
    creem_signature: Optional[str] = Header(None, alias="creem-signature"),
):
    """Handle Creem payment events with cryptographic signature verification."""
    raw_body = await request.body()
    signature = x_creem_signature or creem_signature

    if not _verify_creem_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid or missing webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as e:
        logger.warning("Malformed JSON in Creem webhook: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type")
    data = payload.get("data") or {}
    metadata = data.get("metadata") or payload.get("metadata") or {}
    user_id = metadata.get("user_id")
    subscription_id = data.get("subscription_id") or data.get("id")

    logger.info("Creem Webhook: Received event %s for User ID %s", event_type, user_id)

    if not user_id:
        return {"status": "received", "message": "No user ID in metadata"}

    try:
        # Generate token for the user to bypass RLS in pb client
        user_token = get_supabase_token_for_user(user_id)

        # Retrieve user profile
        profile_resp = await pb.list_records(
            "user_profiles",
            token=user_token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = profile_resp.get("items") or []

        if event_type == "subscription.created":
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            sub_token = generate_subscription_token(user_id, expires_at)

            payload_update = {
                "is_premium": True,
                "subscription_expires_at": expires_at.isoformat(),
                "subscription_token": sub_token,
                "creem_subscription_id": subscription_id
            }

            if items:
                profile_id = items[0]["id"]
                await pb.update_record("user_profiles", profile_id, payload_update, token=user_token)
            else:
                payload_update["user_id"] = user_id
                await pb.create_record("user_profiles", payload_update, token=user_token)

            logger.info("Creem Webhook: Successfully activated subscription for user %s", user_id)

        elif event_type == "subscription.cancelled":
            payload_update = {
                "is_premium": False,
                "subscription_expires_at": None,
                "subscription_token": None,
                "creem_subscription_id": None
            }

            if items:
                profile_id = items[0]["id"]
                await pb.update_record("user_profiles", profile_id, payload_update, token=user_token)

            logger.info("Creem Webhook: Successfully deactivated subscription for user %s", user_id)

        return {"status": "received"}
    except Exception as e:
        logger.error("Creem Webhook processing failed: %s", e)
        # Prevent leaking raw database/client exception details to callers
        raise HTTPException(status_code=500, detail="Webhook processing failed")
