import time
import logging
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status

from app.core.cognito import verify_cognito_jwt, extract_alb_oidc_payload
from app.services.supabase import pb, extract_user_id, extract_user_email

logger = logging.getLogger(__name__)

# In-memory TTL deduplication cache: {user_id: expire_timestamp}
_sync_cache: Dict[str, float] = {}
CACHE_TTL_SECONDS = 600  # 10 minutes


async def sync_user_to_supabase(user_id: str, email: Optional[str], name: Optional[str] = None) -> bool:
    """
    Idempotently upsert user profile into Supabase.
    Uses in-memory cache to skip database writes if synced within the last 10 minutes.
    """
    now = time.time()
    last_synced_expiry = _sync_cache.get(user_id)

    if last_synced_expiry and now < last_synced_expiry:
        return True  # Cache hit — user recently synced, skip DB write

    try:
        # Call the atomic RPC function (created in migration 030)
        await pb.rpc(
            "get_or_create_cognito_user",
            {
                "p_cognito_sub": user_id,
                "p_email_address": email or "",
                "p_user_name": name or "",
            },
        )
        _sync_cache[user_id] = now + CACHE_TTL_SECONDS
        logger.info("JIT User synced to Supabase via RPC: user_id=%s, email=%s", user_id, email)
        return True
    except Exception as rpc_err:
        logger.debug("RPC get_or_create_cognito_user unavailable or failed, falling back: %s", rpc_err)
        # Fallback to direct user_profiles upsert
        try:
            record: Dict[str, Any] = {
                "user_id": user_id,
                "cognito_sub": user_id,
                "email": email or "",
                "name": name or "",
            }
            await pb.upsert_records("user_profiles", [record], on_conflict="user_id")
            _sync_cache[user_id] = now + CACHE_TTL_SECONDS
            logger.info("JIT User synced to user_profiles fallback: user_id=%s", user_id)
            return True
        except Exception as fallback_err:
            logger.warning("JIT sync failed for user %s (will continue request): %s", user_id, fallback_err)
            return False


async def get_current_user_and_sync(
    authorization: Optional[str] = Header(None),
    x_amzn_oidc_data: Optional[str] = Header(None, alias="x-amzn-oidc-data"),
    x_amzn_oidc_identity: Optional[str] = Header(None, alias="x-amzn-oidc-identity"),
) -> Dict[str, Any]:
    """
    FastAPI dependency that:
    1. Authenticates the user via ALB Cognito Header, Cognito Bearer JWT, or legacy Supabase JWT.
    2. Runs Just-In-Time (JIT) real-time sync into Supabase.
    3. Injects the authenticated user dict into route handlers.
    """
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    auth_provider = "unknown"

    # 1. Check for AWS ALB Zero-Code Authentication Header (Cryptographically verified)
    if x_amzn_oidc_data:
        alb_payload = extract_alb_oidc_payload(x_amzn_oidc_data)
        if alb_payload and alb_payload.get("sub"):
            user_id = str(alb_payload["sub"])
            user_email = alb_payload.get("email")
            user_name = alb_payload.get("name") or alb_payload.get("username")
            auth_provider = "alb_cognito"

    # 2. Check for Bearer Token in Authorization Header
    if not user_id and authorization:
        token = authorization.removeprefix("Bearer ").strip()

        # Try Cognito JWT first
        cognito_payload = verify_cognito_jwt(token)
        if cognito_payload:
            user_id = cognito_payload.get("sub")
            user_email = cognito_payload.get("email")
            user_name = cognito_payload.get("name") or cognito_payload.get("cognito:username")
            auth_provider = "cognito_jwt"
        else:
            # Fallback to Supabase / Custom JWT so existing users continue working seamlessly
            user_id = extract_user_id(authorization)
            user_email = extract_user_email(authorization)
            auth_provider = "supabase_jwt"

    if not user_id or user_id == "unknown":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Perform Just-In-Time sync to Supabase (debounced by in-memory TTL cache)
    await sync_user_to_supabase(user_id=user_id, email=user_email, name=user_name)

    return {
        "user_id": user_id,
        "email": user_email,
        "name": user_name,
        "auth_provider": auth_provider,
    }
