import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import paypalrestsdk
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_MODE
from app.services.supabase import pb, extract_user_id
from app.core.security import generate_subscription_token

# Configure PayPal REST SDK
paypalrestsdk.configure({
    "mode": PAYPAL_MODE if PAYPAL_MODE in ["sandbox", "live"] else "sandbox",
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET
})

logger = logging.getLogger(__name__)

router = APIRouter()

class ExecuteRequest(BaseModel):
    plan_id: str
    token: str

@router.post("/paypal-subscription")
async def create_paypal_subscription(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Create PayPal billing plan, activate it, and create billing agreement. Return the approval token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get Referer or Host for dynamic redirect URLs
    referer = request.headers.get("referer") or request.headers.get("host") or "https://mindcradle.online"
    host_match = re.match(r"^(https?://[^/]+)", referer)
    host = host_match.group(1) if host_match else referer.rstrip("/")
    
    return_url = f"{host}/billing?success=true"
    cancel_url = f"{host}/billing?success=false"

    try:
        # Create plan
        plan = paypalrestsdk.BillingPlan({
            "name": "MindCradle Premium Monthly",
            "description": "Unlimited features",
            "type": "REGULAR",
            "payment_definitions": [{
                "name": "Premium Plan",
                "type": "REGULAR",
                "cycles": "0",  # Infinite
                "frequency_unit": "MONTH",
                "frequency": "1",
                "amount": {
                    "value": "9.99",
                    "currency": "USD"
                }
            }],
            "merchant_preferences": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "notify_url": f"https://mindcradle.online/api/webhooks/paypal",
                "max_fail_attempts": "3",
                "initial_fail_amount_action": "CANCEL"
            }
        })
        
        if not plan.create():
            logger.error("Failed to create BillingPlan: %s", plan.error)
            raise HTTPException(status_code=502, detail=f"PayPal plan creation failed: {plan.error}")
            
        # Activate plan
        if not plan.replace([{"op": "replace", "path": "/", "value": {"state": "ACTIVE"}}]):
            logger.error("Failed to activate BillingPlan: %s", plan.error)
            raise HTTPException(status_code=502, detail=f"PayPal plan activation failed: {plan.error}")

        # Create billing agreement
        start_date = (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        agreement = paypalrestsdk.Agreement({
            "name": "MindCradle Premium Monthly Subscription",
            "description": "MindCradle Premium Subscription - $9.99/month",
            "start_date": start_date,
            "plan": {
                "id": plan.id
            },
            "payer": {
                "payment_method": "paypal"
            }
        })
        
        if not agreement.create():
            logger.error("Failed to create BillingAgreement: %s", agreement.error)
            raise HTTPException(status_code=502, detail=f"PayPal agreement creation failed: {agreement.error}")

        # Extract Express Checkout token from approval_url
        approval_url = None
        for link in agreement.links:
            if link.rel == "approval_url":
                approval_url = link.href
                break
                
        if not approval_url:
            raise HTTPException(status_code=502, detail="No approval URL found in agreement response")
            
        token_match = re.search(r"token=(EC-[A-Z0-9]+)", approval_url)
        if token_match:
            ec_token = token_match.group(1)
            return {"plan_id": ec_token}
        else:
            raise HTTPException(status_code=502, detail="Failed to extract token from approval URL")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in create_paypal_subscription: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/paypal-execute")
async def execute_paypal_subscription(
    req: ExecuteRequest,
    authorization: Optional[str] = Header(None)
):
    """Execute PayPal subscription after user approval, update user premium status in DB with robust fallback."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        agreement = paypalrestsdk.Agreement()
        if not agreement.execute(req.token):
            logger.error("Failed to execute BillingAgreement: %s", agreement.error)
            raise HTTPException(status_code=400, detail=f"PayPal agreement execution failed: {agreement.error}")
            
        agreement_id = agreement.id
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        sub_token = generate_subscription_token(user_id, expires_at)

        # Retrieve user profile
        profile_resp = await pb.list_records(
            "user_profiles",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = profile_resp.get("items") or []

        payload = {
            "is_premium": True,
            "subscription_expires_at": expires_at.isoformat(),
            "subscription_token": sub_token,
            "paypal_agreement_id": agreement_id,
            "paypal_plan_id": req.plan_id
        }

        if items:
            profile_id = items[0]["id"]
            try:
                # Try updating with new paypal columns
                await pb.update_record("user_profiles", profile_id, payload, token=token)
            except Exception as upd_err:
                logger.warning("Failed to update profile with paypal columns, attempting fallback: %s", upd_err)
                fallback_payload = {
                    "is_premium": True,
                    "subscription_expires_at": expires_at.isoformat(),
                    "subscription_token": sub_token
                }
                try:
                    await pb.update_record("user_profiles", profile_id, fallback_payload, token=token)
                except Exception:
                    # Save within unlocked_badges array
                    current_badges = items[0].get("unlocked_badges") or []
                    if not isinstance(current_badges, list):
                        current_badges = []
                    current_badges = [b for b in current_badges if not (isinstance(b, dict) and b.get("type") == "subscription")]
                    current_badges.append({
                        "type": "subscription",
                        "token": sub_token,
                        "paypal_agreement_id": agreement_id,
                        "expires_at": expires_at.isoformat()
                    })
                    await pb.update_record("user_profiles", profile_id, {"unlocked_badges": current_badges}, token=token)
        else:
            # Create user profile
            try:
                payload["user_id"] = user_id
                await pb.create_record("user_profiles", payload, token=token)
            except Exception as create_err:
                logger.warning("Failed to create profile with paypal columns, attempting fallback: %s", create_err)
                fallback_payload = {
                    "user_id": user_id,
                    "is_premium": True,
                    "subscription_expires_at": expires_at.isoformat(),
                    "subscription_token": sub_token
                }
                try:
                    await pb.create_record("user_profiles", fallback_payload, token=token)
                except Exception:
                    new_payload = {
                        "user_id": user_id,
                        "unlocked_badges": [{
                            "type": "subscription",
                            "token": sub_token,
                            "paypal_agreement_id": agreement_id,
                            "expires_at": expires_at.isoformat()
                        }]
                    }
                    await pb.create_record("user_profiles", new_payload, token=token)

        return {"success": True, "agreement_id": agreement_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in execute_paypal_subscription: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
