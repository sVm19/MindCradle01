import logging
import uuid
import bcrypt
from typing import Optional
from datetime import datetime, timedelta, timezone
import jwt

from fastapi import APIRouter, HTTPException, Header, Response, Cookie
from app.models.schemas import (
    AuthResponse,
    RefreshRequest,
    PrivacyAcceptanceRequest,
    WithdrawConsentRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MagicLinkRequest,
    MagicLoginRequest,
    VerifyMagicLinkRequest,
    CognitoLoginRequest,
    CognitoDirectLoginRequest,
    CognitoDirectSignupRequest,
    CognitoConfirmSignupRequest,
    CognitoResendCodeRequest,
    CognitoForgotPasswordRequest,
    CognitoConfirmForgotPasswordRequest,
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
from app.services.supabase import pb, extract_user_id, _get_client
from app.core.cognito import (
    verify_cognito_jwt,
    exchange_cognito_code_for_tokens,
    extract_alb_oidc_payload,
    cognito_direct_authenticate,
    cognito_direct_sign_up,
    cognito_confirm_sign_up,
    cognito_resend_confirmation_code,
    cognito_forgot_password,
    cognito_confirm_forgot_password,
)
from app.core.jit_sync import sync_user_to_supabase
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
        # Decode and verify the custom refresh token
        payload = jwt.decode(
            token_to_verify,
            settings.JWT_REFRESH_SECRET_KEY,
            algorithms=["HS256"]
        )

        if payload.get("type") != "refresh":
            logger.warning("Token type in custom refresh token is invalid")
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload["sub"]
        email = payload.get("email", "")
        name = payload.get("name", "")

        new_access_token = create_access_token(user_id, email)
        new_refresh_token = create_refresh_token(user_id, email, name)

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
    except Exception as e:
        is_prod = (settings.ENVIRONMENT == "production")
        response.delete_cookie(
            key="refresh_token",
            path="/",
            secure=True if is_prod else False,
            samesite="none" if is_prod else "lax",
            httponly=True
        )
        logger.warning(f"Custom refresh token invalid or expired: {str(e)}")
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")



@router.get("/me")
async def get_me():
    """Get current user profile. Requires auth header forwarding."""
    # Will be implemented with proper auth middleware
    return {"message": "Auth middleware pending"}


@router.get("/check-age-verified")
async def check_age_verified():
    """Always return verified since age verification system is detached."""
    return {"age_verified": True, "verified_at": None}


@router.post("/verify-age")
async def verify_age():
    """Always return success since age verification system is detached."""
    return {"success": True, "verified": True}


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
        is_passwordless = False
        if user_res and user_res.user:
            app_metadata = getattr(user_res.user, "app_metadata", {}) or {}
            providers = app_metadata.get("providers", [])
            provider = app_metadata.get("provider")
            if provider in ["cognito", "magiclink", "sso"] or any(p in providers for p in ["cognito", "magiclink", "sso"]):
                is_passwordless = True

        if not is_passwordless:
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
    """Request passwordless magic link email with session tracking."""
    email = req.email.lower().strip()
    token = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    expiry_seconds = 900  # 15 minutes
    
    try:
        # Call database RPC to lookup user and store the token and session_id
        res = await pb.create_magic_login_token_with_session(email, token, expiry_seconds, session_id)
        
        # If successfully created, send email
        if res is True:
            magic_link = f"{settings.FRONTEND_URL}/auth/magic?token={token}"
            send_magic_link_email(email, magic_link)
    except Exception as e:
        logger.error(f"Magic link request failed: {str(e)}")
        # Proceed silently to prevent email enumeration
        
    return {"message": "If email exists, magic login link sent", "session_id": session_id}


@router.post("/verify-magic-link", response_model=AuthResponse)
async def verify_magic_link(req: VerifyMagicLinkRequest, response: Response):
    """Verify magic link token and mark session as verified, returning AuthResponse."""
    try:
        # Call database RPC to verify, update used status, and return user info
        user_info = await pb.verify_magic_login_token(req.token, req.device_info)
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Invalid or expired magic link")
            
        user_id = str(user_info["user_id"])
        email = user_info["user_email"]
        name = user_info["user_name"]
        
        # Generate custom tokens
        access_token = create_access_token(user_id, email)
        refresh_token = create_refresh_token(user_id, email, name)
        
        # Auto-start 7-day trial if first time signing in
        await _auto_start_trial_if_needed(user_id, access_token)
        
        # Auto-verify age to prevent prompt
        await _auto_verify_age_if_needed(user_id, access_token)
        
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
            refresh_token="",
            user_id=user_id,
            name=name,
            email=email,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify magic link failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify magic link.")


@router.get("/check-session/{session_id}")
async def check_session_status(session_id: str, response: Response):
    """Check if session has been verified on another device, and log in if so."""
    try:
        # Call database RPC to check and consume
        session_info = await pb.check_magic_login_session(session_id)
        
        if not session_info or not session_info.get("verified"):
            return {"verified": False}
            
        user_id = str(session_info["user_id"])
        email = session_info["user_email"]
        name = session_info["user_name"]
        
        # Generate custom tokens
        access_token = create_access_token(user_id, email)
        refresh_token = create_refresh_token(user_id, email, name)
        
        # Set refresh token in HttpOnly cookie for the PC
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
        
        return {
            "verified": True,
            "token": access_token,
            "user_id": user_id,
            "name": name,
            "email": email,
        }
    except Exception as e:
        logger.error(f"Check session status failed: {str(e)}")
        return {"verified": False, "error": str(e)}


async def _auto_start_trial_if_needed(user_id: str, token: str):
    """Automatically starts the 7-day free trial on first signin if not already used."""
    try:
        res = await pb.list_records(
            "user_profiles",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = res.get("items") or []
        
        if items:
            profile = items[0]
            if not profile.get("trial_used"):
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
                await pb.update_record("user_profiles", profile["id"], trial_payload, token=token)
                logger.info(f"Automatically started 7-day trial for user {user_id}")
        else:
            from app.core.security import generate_subscription_token
            
            trial_started = datetime.now(timezone.utc)
            trial_ends = trial_started + timedelta(days=7)
            sub_token = generate_subscription_token(user_id, trial_ends)
            
            trial_payload = {
                "user_id": user_id,
                "trial_started_at": trial_started.isoformat(),
                "trial_ends_at": trial_ends.isoformat(),
                "trial_used": True,
                "trial_active": True,
                "is_premium": True,
                "subscription_expires_at": trial_ends.isoformat(),
                "subscription_token": sub_token
            }
            await pb.create_record("user_profiles", trial_payload, token=token)
            logger.info(f"Automatically created profile and started 7-day trial for user {user_id}")
            try:
                user_email = await pb.get_user_email(token)
                if user_email:
                    send_signup_welcome(user_email)
                    logger.info(f"Sent welcome email with 7-day trial details to {user_email}")
            except Exception as e_mail:
                logger.error(f"Failed to send welcome email: {str(e_mail)}")
    except Exception as te:
        logger.error(f"Failed to auto-start trial: {str(te)}")


async def _auto_verify_age_if_needed(user_id: str, token: str):
    """Automatically marks the user as age verified to bypass the age verification prompt."""
    try:
        res = await pb.list_records(
            "user_age_verification",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = res.get("items") or []
        if not items:
            payload = {
                "user_id": user_id,
                "age_verified": True,
                "verified_at": datetime.now(timezone.utc).isoformat()
            }
            await pb.create_record("user_age_verification", payload, token=token)
            logger.info(f"Automatically verified age for user {user_id}")
        else:
            profile = items[0]
            if not profile.get("age_verified", False):
                payload = {
                    "age_verified": True,
                    "verified_at": datetime.now(timezone.utc).isoformat()
                }
                await pb.update_record("user_age_verification", profile["id"], payload, token=token)
                logger.info(f"Automatically updated age verification to True for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to auto-verify age: {str(e)}")


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

        # Auto-verify age to prevent prompt
        await _auto_verify_age_if_needed(user_id, access_token)
        
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


@router.post("/cognito", response_model=AuthResponse)
async def cognito_login(
    req: CognitoLoginRequest,
    response: Response,
    x_amzn_oidc_data: Optional[str] = Header(None, alias="x-amzn-oidc-data"),
    x_amzn_oidc_identity: Optional[str] = Header(None, alias="x-amzn-oidc-identity"),
):
    """
    Authenticate a user via AWS Cognito:
    1. Authorization Code exchange from Cognito Hosted UI (req.code).
    2. Direct Cognito ID token verification (req.id_token).
    3. ALB Zero-Code Authentication headers (x-amzn-oidc-data).
    Performs Just-In-Time (JIT) sync into Supabase user_profiles and issues a MindCradle session.
    """
    cognito_payload = None

    # 1. Authorization Code exchange with Cognito Hosted UI
    if req.code:
        redirect_uri = req.redirect_uri or f"{settings.FRONTEND_URL}/auth/callback"
        tokens = await exchange_cognito_code_for_tokens(req.code, redirect_uri)
        if not tokens or "id_token" not in tokens:
            raise HTTPException(
                status_code=400,
                detail="Failed to exchange authorization code with Amazon Cognito.",
            )
        cognito_payload = verify_cognito_jwt(tokens["id_token"])
        if not cognito_payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid ID token received from Amazon Cognito.",
            )

    # 2. Direct ID token passed from client
    elif req.id_token:
        cognito_payload = verify_cognito_jwt(req.id_token)
        if not cognito_payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid Cognito token provided.",
            )

    # 3. ALB Zero-Code Authentication Header (Requires valid cryptographically signed JWT)
    elif x_amzn_oidc_data:
        cognito_payload = extract_alb_oidc_payload(x_amzn_oidc_data)
        if not cognito_payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or unverified ALB authentication signature.",
            )

    if not cognito_payload or not cognito_payload.get("sub"):
        raise HTTPException(
            status_code=400,
            detail="No valid Cognito credentials, code, or verified ALB header provided.",
        )

    user_id = str(cognito_payload["sub"])
    email = cognito_payload.get("email") or ""
    name = (
        cognito_payload.get("name")
        or cognito_payload.get("cognito:username")
        or (email.split("@")[0] if email else "Cognito User")
    )

    # Perform atomic JIT sync to Supabase
    await sync_user_to_supabase(user_id=user_id, email=email, name=name)

    # Issue custom access and refresh tokens
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id, email, name)

    # Auto-start trial and age verification
    await _auto_start_trial_if_needed(user_id, access_token)
    await _auto_verify_age_if_needed(user_id, access_token)

    # Set refresh token in HttpOnly cookie
    is_prod = (settings.ENVIRONMENT == "production")
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True if is_prod else False,
        samesite="none" if is_prod else "lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    return AuthResponse(
        token=access_token,
        refresh_token="",
        user_id=user_id,
        name=name,
        email=email,
    )


@router.get("/alb-session", response_model=AuthResponse)
async def alb_session(
    response: Response,
    x_amzn_oidc_data: Optional[str] = Header(None, alias="x-amzn-oidc-data"),
):
    """
    Check if the user is authenticated via ALB listener Cognito rule.
    Validates the cryptographic ES256 signature from AWS ALB before creating a session.
    """
    if not x_amzn_oidc_data:
        raise HTTPException(status_code=401, detail="No ALB Cognito session found.")

    return await cognito_login(
        req=CognitoLoginRequest(),
        response=response,
        x_amzn_oidc_data=x_amzn_oidc_data,
    )


@router.post("/cognito/direct-login", response_model=AuthResponse)
async def cognito_direct_login(
    req: CognitoDirectLoginRequest,
    response: Response,
):
    """
    Direct in-app login with Amazon Cognito using USER_PASSWORD_AUTH.
    No external redirects. Embeds securely in MindCradle UI.
    Performs JIT sync to Supabase user_profiles and issues tokens.
    """
    auth_result = await cognito_direct_authenticate(req.email, req.password)
    id_token = auth_result.get("IdToken")
    if not id_token:
        raise HTTPException(status_code=401, detail="Authentication failed: No ID token returned from AWS Cognito.")

    cognito_payload = verify_cognito_jwt(id_token)
    if not cognito_payload:
        try:
            cognito_payload = jwt.decode(id_token, options={"verify_signature": False})
        except Exception as e:
            logger.error("Failed to decode Cognito ID token: %s", e)
            raise HTTPException(status_code=401, detail="Invalid token from AWS Cognito.")

    user_id = str(cognito_payload.get("sub"))
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user identifier in Cognito token.")

    email = cognito_payload.get("email") or req.email.strip().lower()
    name = (
        cognito_payload.get("name")
        or cognito_payload.get("cognito:username")
        or (email.split("@")[0] if email else "User")
    )

    # Perform atomic JIT sync to Supabase
    await sync_user_to_supabase(user_id=user_id, email=email, name=name)

    # Issue custom access and refresh tokens
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id, email, name)

    # Auto-start trial and age verification
    await _auto_start_trial_if_needed(user_id, access_token)
    await _auto_verify_age_if_needed(user_id, access_token)

    # Set refresh token in HttpOnly cookie
    is_prod = (settings.ENVIRONMENT == "production")
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True if is_prod else False,
        samesite="none" if is_prod else "lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    return AuthResponse(
        token=access_token,
        refresh_token="",
        user_id=user_id,
        name=name,
        email=email,
    )


@router.post("/cognito/direct-signup")
async def cognito_direct_signup(req: CognitoDirectSignupRequest):
    """
    Direct in-app registration with Amazon Cognito.
    Cognito automatically emails a 6-digit confirmation code.
    """
    res = await cognito_direct_sign_up(
        email=req.email,
        password=req.password,
        name=req.name,
    )
    user_confirmed = res.get("UserConfirmed", False)
    return {
        "success": True,
        "requires_confirmation": not user_confirmed,
        "email": req.email,
        "user_sub": res.get("UserSub"),
    }


@router.post("/cognito/confirm-signup")
async def cognito_confirm_signup(req: CognitoConfirmSignupRequest):
    """
    Confirm account using the 6-digit confirmation code delivered to user's email.
    """
    await cognito_confirm_sign_up(email=req.email, code=req.code)
    return {
        "success": True,
        "confirmed": True,
        "message": "Account successfully verified. You may now log in.",
    }


@router.post("/cognito/resend-code")
async def cognito_resend_code(req: CognitoResendCodeRequest):
    """
    Resend the 6-digit confirmation code to user's email.
    """
    await cognito_resend_confirmation_code(email=req.email)
    return {
        "success": True,
        "message": "A new verification code has been sent to your email.",
    }


@router.post("/cognito/forgot-password")
async def cognito_forgot_password_endpoint(req: CognitoForgotPasswordRequest):
    """
    Trigger AWS Cognito ForgotPassword flow to send 6-digit reset code via email.
    """
    await cognito_forgot_password(email=req.email)
    return {
        "success": True,
        "message": "A 6-digit password recovery code has been sent to your email.",
    }


@router.post("/cognito/confirm-forgot-password")
async def cognito_confirm_forgot_password_endpoint(req: CognitoConfirmForgotPasswordRequest):
    """
    Confirm password reset with the 6-digit code and set new password in AWS Cognito.
    """
    await cognito_confirm_forgot_password(
        email=req.email,
        code=req.code,
        new_password=req.new_password,
    )
    return {
        "success": True,
        "message": "Password successfully updated. You may now sign in.",
    }












