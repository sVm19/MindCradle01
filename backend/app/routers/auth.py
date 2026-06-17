import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header
from app.models.schemas import LoginRequest, SignupRequest, AuthResponse, RefreshRequest, AriaAgeVerifyRequest, PrivacyAcceptanceRequest, WithdrawConsentRequest
from app.services.supabase import pb, extract_user_id

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Authenticate user via Supabase."""
    try:
        result = await pb.auth_with_password(req.email, req.password)
        record = result["record"]
        return AuthResponse(
            token=result["token"],
            refresh_token=result.get("refresh_token", ""),
            user_id=record["id"],
            name=record.get("name", ""),
            email=record["email"],
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    """Create a new user in Supabase and return auth token."""
    try:
        await pb.create_user({
            "email": req.email,
            "password": req.password,
            "name": req.name,
        })
        # Auto-login after signup
        result = await pb.auth_with_password(req.email, req.password)
        record = result["record"]
        return AuthResponse(
            token=result["token"],
            refresh_token=result.get("refresh_token", ""),
            user_id=record["id"],
            name=record.get("name", ""),
            email=record["email"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(req: RefreshRequest):
    """Exchange a refresh token for a new access token."""
    try:
        result = await pb.refresh_session(req.refresh_token)
        record = result["record"]
        return AuthResponse(
            token=result["token"],
            refresh_token=result.get("refresh_token", ""),
            user_id=record["id"],
            name=record.get("name", ""),
            email=record["email"],
        )
    except Exception:
        logger.warning("Token refresh failed — refresh_token may be expired or revoked")
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")


@router.get("/me")
async def get_me():
    """Get current user profile. Requires auth header forwarding."""
    # Will be implemented with proper auth middleware
    return {"message": "Auth middleware pending"}


@router.get("/check-age-verified")
async def check_age_verified(
    authorization: Optional[str] = Header(None)
):
    """Check if current user is age verified from user_age_verification."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        res = await pb.list_records("user_age_verification", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
        items = res.get("items") or []
        if items:
            item = items[0]
            return {
                "age_verified": item.get("age_verified", False),
                "verified_at": item.get("verified_at")
            }
        return {"age_verified": False, "verified_at": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check verification status: {str(e)}")


@router.post("/verify-age")
async def verify_age(
    req: AriaAgeVerifyRequest,
    authorization: Optional[str] = Header(None)
):
    """Verify age for the current user in user_age_verification."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        # Check if record exists in user_age_verification
        res = await pb.list_records("user_age_verification", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
        items = res.get("items") or []
        
        payload = {
            "age_verified": req.age_verified,
            "verified_at": datetime.now(timezone.utc).isoformat() if req.age_verified else None
        }
        
        if items:
            record_id = items[0]["id"]
            updated = await pb.update_record("user_age_verification", record_id, payload, token=token)
        else:
            payload["user_id"] = user_id
            updated = await pb.create_record("user_age_verification", payload, token=token)
            
        return {"success": True, "verified": updated.get("age_verified", False)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update verification status: {str(e)}")


PRIVACY_POLICY_TEXT = """Effective Date: June 17, 2026

Welcome to MindCradle. Your trust is our most valuable asset. We are dedicated to providing a safe, secure, and supportive environment for your wellness journey. This Privacy Policy details how we handle, protect, and process your data. Please read this document in its entirety to understand how we store and handle your personal logs, mood entries, and conversation details with ARIA, our built-in wellness AI assistant.

1. Data Collection & Privacy First Approach
MindCradle is built on a privacy-first foundation. We gather minimal personal information required to run the core features of the mental health dashboard. The information we collect includes:
- Account Credentials: Your email address, password, and chosen profile name are collected during user registration. These are securely processed and verified via Supabase authentication.
- Mood Logging Data: Numerical ratings of your state of calm (from 1 to 10), selected emotion categories, and custom narrative notes representing your state at check-in.
- Ritual Entries: Intentions, activity choices, completion timestamps, and reflection entries recorded during your morning and wind-down routines.
- Journal Reflections: Text content you draft inside the digital journal tool, which is processed to generate personalized AI-driven reflections.
- ARIA Chat Logs: Chat logs of all text exchanges with our AI companion, ARIA, to enable context retention, conversational memory, and distress level analysis.

2. How We Use Your Data
Your information is processed strictly to provide the mental wellness tracking functionality and features. We do not sell or trade your data. The data is used to:
- Synthesize recovery rates, calm indices, and wellness progress graphs on your dashboard.
- Maintain historical memory for ARIA to provide contextual, warm, and daily insights.
- Detect acute distress levels or potential crises to proactively deliver emergency resources.
- Perform A/B experiments evaluating interface layouts to refine emotional wellness tracking.

3. Data Storage, Security, & GDPR Compliance
All connection states and transaction details are encrypted using Transport Layer Security (TLS) in transit, and databases are encrypted at rest.
If you are situated in the European Union (EU) or European Economic Area (EEA), you benefit from standard rights under the General Data Protection Regulation (GDPR). These rights include:
- Right of Erasure: The capability to completely purge your account and delete all associated journals, mood records, and chat history permanently.
- Right to Restrict Processing: The ability to adjust notifications, disable background processing trackers, or disconnect push notification tokens.
- Right to Access & Portability: The ability to request a complete export of all historical wellness data linked to your identity.

4. AI Integrations & Prompt Privacy
To power the reflective capabilities of ARIA, we utilize advanced language models via secure APIs (such as OpenRouter).
Before sending your messages or journal contents to these external AI models, all direct personally identifiable information (PII) is stripped out. AI providers do not use your conversations to train their public models, and all interactions are subject to strict data retention policies.

5. Crisis Support & Safety Handover Policies
ARIA is a wellness assistant designed for positive emotional tracking and support. ARIA is not a medical device, a replacement for professional clinical therapy, or an emergency responder.
If you log severe or acute distress, our system will automatically show a crisis banner pointing to 24/7 hotlines (e.g. 988 Lifeline, Crisis Text Line). Furthermore, if you specify an emergency contact in settings, we may log a safety handover record to assist in notifying your designated supporter.

6. Consent and Agreement
By scrolling to the bottom of this text, checking the consent checkbox, and clicking "I Agree & Continue", you confirm that:
- You are at least 18 years of age (or have explicit parental consent).
- You understand that ARIA is an AI companion and does not provide professional medical diagnoses.
- You agree to our data collection, processing, and crisis management policies described above."""


@router.post("/privacy-accepted")
async def privacy_accepted(
    req: PrivacyAcceptanceRequest,
    authorization: Optional[str] = Header(None)
):
    """Record privacy policy acceptance for the user."""
    if not authorization:
        return {"success": True, "message": "Privacy policy accepted anonymously"}
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        # Check if record exists in user_privacy_acceptance
        res = await pb.list_records("user_privacy_acceptance", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
        items = res.get("items") or []
        
        payload = {
            "privacy_accepted": req.privacy_accepted,
            "accepted_at": datetime.now(timezone.utc).isoformat() if req.privacy_accepted else None
        }
        
        if items:
            record_id = items[0]["id"]
            await pb.update_record("user_privacy_acceptance", record_id, payload, token=token)
        else:
            payload["user_id"] = user_id
            await pb.create_record("user_privacy_acceptance", payload, token=token)
            
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to record privacy acceptance in DB: {str(e)}")
        return {"success": True, "warning": "Database sync skipped or table missing"}


@router.get("/check-privacy")
async def check_privacy(
    authorization: Optional[str] = Header(None)
):
    """Retrieve user's privacy policy acceptance status."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        res = await pb.list_records("user_privacy_acceptance", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
        items = res.get("items") or []
        if items:
            item = items[0]
            return {
                "privacy_accepted": item.get("privacy_accepted", False),
                "accepted_at": item.get("accepted_at")
            }
        return {"privacy_accepted": False, "accepted_at": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check privacy status: {str(e)}")


@router.get("/privacy-policy")
async def get_privacy_policy():
    """Retrieve full text of the privacy policy."""
    return {"text": PRIVACY_POLICY_TEXT}


@router.delete("/withdraw-consent")
async def withdraw_consent(
    req: WithdrawConsentRequest,
    authorization: Optional[str] = Header(None)
):
    """Confirm password, delete all user data, delete account and revoke JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    # 1. Resolve email address associated with user's JWT token
    try:
        email = await pb.get_user_email(token)
    except Exception as e:
        logger.error(f"Failed to resolve email for user {user_id}: {str(e)}")
        raise HTTPException(status_code=400, detail="Could not resolve email for active user session.")
        
    # 2. Verify password by logging in
    try:
        await pb.auth_with_password(email, req.password)
    except Exception:
        raise HTTPException(status_code=401, detail="Incorrect password. Account deletion aborted.")
        
    # 3. Delete the user (cascades to all other data tables)
    try:
        await pb.delete_user_account(token)
        return {"success": True, "message": "Account deleted"}
    except Exception as e:
        logger.error(f"Failed to delete account for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")


