from datetime import datetime, timedelta, timezone
import re
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status

from app.models.schemas import SubscriptionCheckoutRequest
from app.services.supabase import pb, extract_user_id
from app.core.security import generate_subscription_token

router = APIRouter()

def validate_card_details(card_number: str, cvc: str, expiry: str):
    # Remove whitespace/dashes from card number
    clean_card = re.sub(r"\s+|-", "", card_number)
    if not clean_card.isdigit() or len(clean_card) < 13 or len(clean_card) > 19:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid card number format. Must be 13-19 digits."
        )

    # Validate CVC (3-4 digits)
    if not cvc.isdigit() or len(cvc) not in (3, 4):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CVC. Must be 3 or 4 digits."
        )

    # Validate expiry MM/YY or MM/YYYY
    expiry_match = re.match(r"^(0[1-9]|1[0-2])/(\d{2}|\d{4})$", expiry.strip())
    if not expiry_match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expiry date format. Use MM/YY or MM/YYYY."
        )

    month, year = expiry_match.groups()
    month = int(month)
    year = int(year)
    if year < 100:
        year += 2000

    now = datetime.now()
    if year < now.year or (year == now.year and month < now.month):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card has expired."
        )

@router.post("/checkout")
async def checkout(
    req: SubscriptionCheckoutRequest,
    authorization: Optional[str] = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Securely validate payment details
    validate_card_details(req.card_number, req.cvc, req.expiry)

    # Calculate expiration date (30 days from now)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    
    # Generate cryptographic signature
    sub_token = generate_subscription_token(user_id, expires_at)

    # Fetch current user profile to modify
    try:
        profile_resp = await pb.list_records(
            "user_profiles",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = profile_resp.get("items") or []
        
        payload = {
            "is_premium": True,
            "subscription_expires_at": expires_at.isoformat(),
            "subscription_token": sub_token
        }

        if items:
            profile_id = items[0]["id"]
            # Fallback handling in case columns are missing
            try:
                await pb.update_record("user_profiles", profile_id, payload, token=token)
            except Exception:
                # Fallback: Save within unlocked_badges JSONB array
                current_badges = items[0].get("unlocked_badges") or []
                if not isinstance(current_badges, list):
                    current_badges = []
                
                # Filter out old subscriptions
                current_badges = [b for b in current_badges if not (isinstance(b, dict) and b.get("type") == "subscription")]
                current_badges.append({
                    "type": "subscription",
                    "token": sub_token,
                    "expires_at": expires_at.isoformat()
                })
                await pb.update_record("user_profiles", profile_id, {"unlocked_badges": current_badges}, token=token)
        else:
            # Create profile
            try:
                payload["user_id"] = user_id
                await pb.create_record("user_profiles", payload, token=token)
            except Exception:
                # Fallback
                new_payload = {
                    "user_id": user_id,
                    "unlocked_badges": [{
                        "type": "subscription",
                        "token": sub_token,
                        "expires_at": expires_at.isoformat()
                    }]
                }
                await pb.create_record("user_profiles", new_payload, token=token)

        return {
            "status": "success",
            "message": "Subscription activated successfully",
            "is_premium": True,
            "subscription_expires_at": expires_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/cancel")
async def cancel(
    authorization: Optional[str] = Header(None)
):
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

        if items:
            profile_id = items[0]["id"]
            payload = {
                "is_premium": False,
                "subscription_expires_at": None,
                "subscription_token": None
            }
            try:
                await pb.update_record("user_profiles", profile_id, payload, token=token)
            except Exception:
                # Fallback: remove subscription object from unlocked_badges array
                current_badges = items[0].get("unlocked_badges") or []
                if isinstance(current_badges, list):
                    current_badges = [b for b in current_badges if not (isinstance(b, dict) and b.get("type") == "subscription")]
                    await pb.update_record("user_profiles", profile_id, {"unlocked_badges": current_badges}, token=token)

        return {"status": "success", "message": "Subscription cancelled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
