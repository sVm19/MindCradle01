import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from app.services.supabase import pb

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/paypal")
async def paypal_webhook(payload: dict):
    """Handle PayPal IPN / Webhook notifications for Billing Agreements."""
    event_type = payload.get("event_type")
    resource = payload.get("resource") or {}
    agreement_id = resource.get("id")
    
    logger.info("PayPal Webhook: Received event %s for Agreement %s", event_type, agreement_id)
    
    if not agreement_id:
        return {"status": "ok", "message": "No agreement ID in payload"}
        
    try:
        profile = None
        
        # Search 1: paypal_agreement_id
        try:
            res = await pb.list_records(
                "user_profiles",
                params={"filter": f'paypal_agreement_id="{agreement_id}"', "perPage": 1}
            )
            items = res.get("items") or []
            if items:
                profile = items[0]
        except Exception:
            pass
            
        # Search 2: subscription_token
        if not profile:
            try:
                res = await pb.list_records(
                    "user_profiles",
                    params={"filter": f'subscription_token="{agreement_id}"', "perPage": 1}
                )
                items = res.get("items") or []
                if items:
                    profile = items[0]
            except Exception:
                pass
                
        # Search 3: unlocked_badges fallback
        if not profile:
            try:
                res = await pb.list_records("user_profiles", params={"perPage": 100})
                items = res.get("items") or []
                for item in items:
                    badges = item.get("unlocked_badges") or []
                    if isinstance(badges, list):
                        for badge in badges:
                            if isinstance(badge, dict) and badge.get("type") == "subscription":
                                if badge.get("paypal_agreement_id") == agreement_id or badge.get("token") == agreement_id:
                                    profile = item
                                    break
                        if profile:
                            break
            except Exception as e:
                logger.warning("Failed local scan for unlocked_badges: %s", e)
                
        if not profile:
            logger.warning("PayPal Webhook: No user profile found matching Agreement ID %s", agreement_id)
            return {"status": "ok", "message": "No matching user profile"}

        profile_id = profile["id"]

        if event_type in ["BILLING.SUBSCRIPTION.CANCELLED", "BILLING.SUBSCRIPTION.EXPIRED", "BILLING.SUBSCRIPTION.SUSPENDED"]:
            logger.info("PayPal Webhook: Deactivating subscription for Profile %s", profile_id)
            payload_update = {
                "is_premium": False,
                "subscription_expires_at": None,
                "subscription_token": None
            }
            try:
                await pb.update_record("user_profiles", profile_id, payload_update)
            except Exception:
                current_badges = profile.get("unlocked_badges") or []
                if isinstance(current_badges, list):
                    current_badges = [b for b in current_badges if not (isinstance(b, dict) and b.get("type") == "subscription")]
                    await pb.update_record("user_profiles", profile_id, {"unlocked_badges": current_badges})
                    
        elif event_type == "PAYMENT.SALE.COMPLETED":
            logger.info("PayPal Webhook: Sale completed, extending subscription for Profile %s", profile_id)
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            payload_update = {
                "is_premium": True,
                "subscription_expires_at": expires_at.isoformat()
            }
            try:
                await pb.update_record("user_profiles", profile_id, payload_update)
            except Exception:
                current_badges = profile.get("unlocked_badges") or []
                if isinstance(current_badges, list):
                    found = False
                    for b in current_badges:
                        if isinstance(b, dict) and b.get("type") == "subscription":
                            b["expires_at"] = expires_at.isoformat()
                            found = True
                            break
                    if not found:
                        current_badges.append({
                            "type": "subscription",
                            "paypal_agreement_id": agreement_id,
                            "expires_at": expires_at.isoformat()
                        })
                    await pb.update_record("user_profiles", profile_id, {"unlocked_badges": current_badges})
                    
        return {"status": "ok"}
    except Exception as e:
        logger.error("PayPal Webhook processing failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
