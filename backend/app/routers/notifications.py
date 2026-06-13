import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from app.models.schemas import DeviceRegister
from app.services.supabase import _get_client, extract_user_id
from app.services.firebase import send_to_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register-device")
async def register_device(
    req: DeviceRegister,
    authorization: Optional[str] = Header(None),
):
    """
    Registers or updates the FCM push notification token for the user's device.
    """
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    logger.info(
        "Register device request received: user_id=%s, device_id=%s",
        user_id,
        req.device_id,
    )

    try:

        def _db_operations():
            client = _get_client(authorization)

            # Check if device_id already exists for this user
            existing = (
                client.table("push_notification_tokens")
                .select("*")
                .eq("user_id", user_id)
                .eq("device_id", req.device_id)
                .execute()
            )

            if existing.data:
                # If device_id already exists for this user, update instead of insert
                record_id = existing.data[0]["id"]
                client.table("push_notification_tokens").update(
                    {
                        "push_token": req.push_token,
                        "platform": req.platform,
                        "is_active": True,
                    }
                ).eq("id", record_id).execute()
                logger.info(
                    "Updated existing push notification token for device_id=%s",
                    req.device_id,
                )
            else:
                # Insert new push token record
                client.table("push_notification_tokens").insert(
                    {
                        "user_id": user_id,
                        "push_token": req.push_token,
                        "platform": req.platform,
                        "device_id": req.device_id,
                        "is_active": True,
                    }
                ).execute()
                logger.info(
                    "Registered new push notification token for device_id=%s",
                    req.device_id,
                )

        await asyncio.to_thread(_db_operations)
        return {"registered": True, "device_id": req.device_id}

    except Exception as e:
        logger.error(
            "Error registering push token for user %s: %s", user_id, e
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register device: {type(e).__name__}: {e}",
        )


@router.post("/test")
async def test_notifications(
    authorization: Optional[str] = Header(None),
):
    """
    Sends a test push notification to all active devices of the current user.
    """
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    logger.info("Test notification request received for user_id=%s", user_id)

    try:

        def _send():
            return send_to_user(user_id, "Test", "Hello from Firebase!")

        count = await asyncio.to_thread(_send)
        return {"sent": True, "count": count}
    except Exception as e:
        logger.error(
            "Error sending test notification to user %s: %s", user_id, e
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test notification: {type(e).__name__}: {e}",
        )

