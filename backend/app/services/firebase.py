import os
import logging
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, messaging
from app.services.supabase import _get_client

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
cred_path = Path(__file__).resolve().parent.parent.parent / "firebase-key.json"
if not cred_path.exists():
    cred_path = Path("firebase-key.json")

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
except Exception as e:
    logger.error("Failed to initialize Firebase Admin SDK: %s", e)


def send_push_notification(device_token: str, title: str, body: str) -> Optional[str]:
    """
    Sends a push notification to a specific device using FCM.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=device_token,
        )
        response = messaging.send(message)
        logger.info("Successfully sent FCM message: %s", response)
        return response
    except Exception as e:
        logger.error("Error sending FCM message to token %s: %s", device_token, e)
        return None


def send_to_user(user_id: str, title: str, body: str) -> int:
    """
    Queries the database for active push tokens for a user,
    and sends a push notification to each device.
    Returns the number of successfully sent notifications.
    """
    try:
        client = _get_client()
        # Query database: get all active push tokens for user_id
        response = (
            client.table("push_notification_tokens")
            .select("push_token")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        tokens = [
            row["push_token"]
            for row in (response.data or [])
            if row.get("push_token")
        ]
    except Exception as e:
        logger.error("Error querying push tokens for user %s: %s", user_id, e)
        return 0

    sent_count = 0
    for token in tokens:
        res = send_push_notification(token, title, body)
        if res is not None:
            sent_count += 1

    return sent_count
