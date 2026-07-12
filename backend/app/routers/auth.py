import logging
import uuid
import bcrypt
from typing import Optional
from datetime import datetime, timedelta, timezone
import jwt

from fastapi import APIRouter, HTTPException, Header, Response, Cookie
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from app.models.schemas import (
    AuthResponse,
    RefreshRequest,
    AriaAgeVerifyRequest,
    PrivacyAcceptanceRequest,
    WithdrawConsentRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MagicLinkRequest,
    MagicLoginRequest,
    GoogleLoginRequest,
)
from app.utils.security import (
    hash_password,
    verify_password,
    validate_password,
    get_deterministic_hash,
)
from app.utils.email import (
    send_password_reset_email,
    send_signup_welcome,
    send_magic_link_email,
)
from app.services.supabase import pb, extract_user_id
from app import config as settings


router = APIRouter()
logger = logging.getLogger(__name__)


def create_access_token(user_id: str, email: Optional[str] = None):
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, settings.JWT_SECRET_KEY, "HS256")


def create_refresh_token(user_id: str, email: Optional[str] = None, name: Optional[str] = None):
    expire = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    if email:
        payload["email"] = email
    if name:
        payload["name"] = name
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET_KEY, "HS256")






@router.post("/refresh", response_model=AuthResponse)
async def refresh_token_endpoint(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    req: Optional[RefreshRequest] = None,
):
    """Exchange a refresh token for a new access token."""
    token_to_verify = refresh_token
    if not token_to_verify and req:
        token_to_verify = req.refresh_token

    if not token_to_verify:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        result = await pb.refresh_session(token_to_verify)
        record = result["record"]
        user_id = record["id"]
        email = record.get("email", "")
        name = record.get("name", "")
        new_access_token = result["token"]
        new_refresh_token = result["refresh_token"]

        is_prod = (settings.ENVIRONMENT == "production")
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True if is_prod else False,
            samesite="none" if is_prod else "lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/"
        )

        return AuthResponse(
            token=new_access_token,
            refresh_token="",  # DO NOT issue new refresh token (prevent unlimited extension)
            user_id=user_id,
            name=name,
            email=email,
        )
    except Exception:
        is_prod = (settings.ENVIRONMENT == "production")
        response.delete_cookie(
            key="refresh_token",
            path="/",
            secure=True if is_prod else False,
            samesite="none" if is_prod else "lax",
            httponly=True
        )
        logger.warning("Supabase refresh token invalid or expired")
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
        
    # 2. Verify password (only for legacy email/password users)
    try:
        client = _get_client(token)
        user_res = client.auth.get_user(token)
        is_google = False
        if user_res and user_res.user:
            app_metadata = getattr(user_res.user, "app_metadata", {}) or {}
            providers = app_metadata.get("providers", [])
            if "google" in providers or app_metadata.get("provider") == "google":
                is_google = True

        if not is_google:
            if not req.password:
                raise HTTPException(status_code=400, detail="Password is required for legacy accounts.")
            await pb.auth_with_password(email, get_deterministic_hash(req.password))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Incorrect password. Account deletion aborted.")
        
    # 3. Delete the user (cascades to all other data tables)
    try:
        await pb.delete_user_account(token)
        return {"success": True, "message": "Account deleted"}
    except Exception as e:
        logger.error(f"Failed to delete account for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")


@router.post("/logout")
async def logout_endpoint(response: Response):
    """Log out user by clearing the refresh token cookie."""
    is_prod = (settings.ENVIRONMENT == "production")
    response.delete_cookie(
        key="refresh_token",
        path="/",
        secure=True if is_prod else False,
        samesite="none" if is_prod else "lax",
        httponly=True
    )
    return {"success": True}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    authorization: Optional[str] = Header(None)
):
    """Change user password, verifying current credentials and preventing last 5 reuse."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    # Validate password strength requirements
    password_error = validate_password(req.new_password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)
        
    # 1. Fetch user's email to verify identity
    try:
        email = await pb.get_user_email(token)
    except Exception as e:
        logger.error("Failed to retrieve email for password change: %s", e)
        raise HTTPException(status_code=400, detail="Failed to resolve user session.")
        
    # 2. Verify current password
    try:
        await pb.auth_with_password(email, get_deterministic_hash(req.current_password))
    except Exception:
        raise HTTPException(status_code=401, detail="Incorrect current password")
        
    # 3. Check password history
    try:
        res = await pb.list_records(
            "user_password_history",
            token=token,
            params={"filter": f'user_id="{user_id}"', "sort": "-created_at"}
        )
        history = res.get("items") or []
    except Exception as hexc:
        logger.warning("Failed to fetch password history from database: %s", hexc)
        history = []
        
    # Verify against the last 5 password hashes in history
    for record in history[:5]:
        if verify_password(req.new_password, record["password_hash"]):
            raise HTTPException(status_code=400, detail="Cannot reuse any of your last 5 passwords.")
            
    # 4. Update password in Supabase Auth
    try:
        await pb.update_user(token, {"password": get_deterministic_hash(req.new_password)})
    except Exception as uexc:
        logger.error("Failed to update password in Supabase Auth: %s", uexc)
        raise HTTPException(status_code=500, detail="Failed to update password.")
        
    # 5. Save new password hash to history
    try:
        await pb.create_record(
            "user_password_history",
            {
                "user_id": user_id,
                "password_hash": hash_password(req.new_password)
            },
            token=token
        )
    except Exception as hexc:
        logger.warning("Failed to record new password in history: %s", hexc)
        
    return {"success": True, "message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Request password reset email."""
    # Generate reset token (15 min expiry)
    reset_token = str(uuid.uuid4())
    expiry_seconds = 900  # 15 minutes
    
    try:
        # Call Database RPC to lookup user and save the token securely
        res = await pb.create_password_reset_token(req.email, reset_token, expiry_seconds)
        
        # If successfully created, send email
        if res is True:
            reset_link = f"{settings.FRONTEND_URL}/reset?token={reset_token}"
            send_password_reset_email(req.email, reset_link)
    except Exception as e:
        logger.error(f"Forgot password failed: {str(e)}")
        # Proceed silently to prevent email enumeration
        
    return {"message": "If email exists, reset link sent"}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    """Verify token and reset password."""
    # 1. Validate password strength
    password_error = validate_password(req.new_password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    try:
        # 2. Retrieve last 5 passwords to enforce history constraint
        history = await pb.get_password_history_by_token(req.token)
        for record in history:
            if verify_password(req.new_password, record.get("password_hash")):
                raise HTTPException(status_code=400, detail="Cannot reuse any of your last 5 passwords.")
                
        # 3. Bcrypt-hash the new deterministic password and call the reset RPC
        deterministic_pass = get_deterministic_hash(req.new_password)
        salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
        new_encrypted_pass = bcrypt.hashpw(deterministic_pass.encode("utf-8"), salt).decode("utf-8")
        
        # Hash new password for history
        new_history_hash = hash_password(req.new_password)
        
        # Execute reset password RPC
        reset_res = await pb.reset_password_with_token(
            req.token,
            new_encrypted_pass,
            new_history_hash
        )
        
        if not reset_res:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
            
        return {"message": "Password reset successful. Login now."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset password. Please try again.")


@router.post("/magic-link")
async def magic_link_request(req: MagicLinkRequest):
    """Request passwordless magic link email."""
    # Generate token
    token = str(uuid.uuid4())
    expiry_seconds = 900  # 15 minutes
    
    try:
        # Call database RPC to lookup user and store the token
        res = await pb.create_magic_login_token(req.email, token, expiry_seconds)
        
        # If successfully created, send email
        if res is True:
            magic_link = f"{settings.FRONTEND_URL}/magic-login?token={token}"
            send_magic_link_email(req.email, magic_link)
    except Exception as e:
        logger.error(f"Magic link request failed: {str(e)}")
        # Proceed silently to prevent email enumeration
        
    return {"message": "If email exists, magic login link sent"}


async def _auto_start_trial_if_needed(user_id: str, token: str):
    """Automatically starts the 7-day free trial on first signin if not already used."""
    try:
        profile = await pb.get_record("user_profiles", user_id, token=token)
        if profile and not profile.get("trial_used"):
            from app.core.security import generate_subscription_token
            
            trial_started = datetime.now(timezone.utc)
            trial_ends = trial_started + timedelta(days=7)
            sub_token = generate_subscription_token(user_id, trial_ends)
            
            trial_payload = {
                "trial_started_at": trial_started.isoformat(),
                "trial_ends_at": trial_ends.isoformat(),
                "trial_used": True,
                "trial_active": True,
                "is_premium": True,
                "subscription_expires_at": trial_ends.isoformat(),
                "subscription_token": sub_token
            }
            await pb.update_record("user_profiles", user_id, trial_payload, token=token)
            logger.info(f"Automatically started 7-day trial for user {user_id}")
    except Exception as te:
        logger.error(f"Failed to auto-start trial: {str(te)}")


@router.post("/magic-login", response_model=AuthResponse)
async def magic_login(req: MagicLoginRequest, response: Response):
    """Verify magic link token and log user in, returning Custom JWT AuthResponse."""
    try:
        # Consume the token via Database RPC
        user_info = await pb.consume_magic_login_token(req.token)
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Invalid or expired magic link")
            
        user_id = str(user_info["user_id"])
        email = user_info["user_email"]
        name = user_info["user_name"]
        
        # Generate custom tokens (standard custom JWT flow)
        access_token = create_access_token(user_id, email)
        refresh_token = create_refresh_token(user_id, email, name)
        
        # Auto-start 7-day trial if first time signing in
        await _auto_start_trial_if_needed(user_id, access_token)
        
        # Set refresh token in HttpOnly cookie
        is_prod = (settings.ENVIRONMENT == "production")
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True if is_prod else False,
            samesite="none" if is_prod else "lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/"
        )
        
        return AuthResponse(
            token=access_token,
            refresh_token="",  # Do not return refresh token in body
            user_id=user_id,
            name=name,
            email=email,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Magic login failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to log in with magic link.")


@router.post("/google", response_model=AuthResponse)
async def google_login(req: GoogleLoginRequest, response: Response):
    """Verify Google token and create or authenticate user session"""
    try:
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_CLIENT_ID is not configured on the backend."
            )
            
        # Verify token from frontend with 10s clock tolerance for skew
        idinfo = google_id_token.verify_oauth2_token(
            req.token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
        )
        
        email = idinfo['email']
        name = idinfo.get('name', 'User')
        google_sub = idinfo['sub']
        
        # Use database RPC to find or create the user securely and return details
        user_info_list = await pb.call_rpc(
            "get_or_create_google_user",
            {
                "p_email_address": email,
                "p_user_name": name,
                "p_google_sub": google_sub
            }
        )
        
        if not user_info_list or len(user_info_list) == 0:
            raise HTTPException(status_code=400, detail="Failed to retrieve or create Google user account.")
            
        user_info = user_info_list[0]
        user_id = str(user_info["user_id"])
        ret_email = user_info["user_email"]
        ret_name = user_info["user_name"]
        
        # Generate custom tokens (same custom JWT flow as magic login)
        access_token = create_access_token(user_id, ret_email)
        refresh_token = create_refresh_token(user_id, ret_email, ret_name)
        
        # Auto-start 7-day trial if first time signing in
        await _auto_start_trial_if_needed(user_id, access_token)
        
        # Set refresh token in HttpOnly cookie
        is_prod = (settings.ENVIRONMENT == "production")
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True if is_prod else False,
            samesite="none" if is_prod else "lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/"
        )
        
        return AuthResponse(
            token=access_token,
            refresh_token="",  # Do not return in body
            user_id=user_id,
            name=ret_name,
            email=ret_email,
        )
    except Exception as e:
        logger.error(f"Google login failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Google authentication failed: {str(e)}")






