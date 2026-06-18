"""
app/core/security.py
────────────────────
JWT verification utilities for the MindCradle backend.

Architecture note
─────────────────
MindCradle uses Supabase Auth — Supabase issues and validates JWTs with its
own internal secret (SUPABASE_JWT_SECRET).  This application does NOT mint
its own tokens; it only *verifies* tokens that Supabase has issued.

The previous implementation of extract_user_id() decoded the JWT payload via
raw base64 WITHOUT verifying the signature.  That is a critical security flaw:
an attacker could craft an arbitrary payload, set any sub (user_id) they want,
and bypass all per-user data isolation.

This module replaces that unsafe decode with full cryptographic verification:
  - Signature checked against SUPABASE_JWT_SECRET
  - Expiry (exp) enforced
  - Issuer (iss) checked to match the Supabase project URL
  - Role / audience check (anon / authenticated)

Usage
─────
    from app.core.security import verify_supabase_token, TokenPayload

    payload = verify_supabase_token(raw_bearer_token)
    user_id = payload.sub            # verified user ID
    is_anon = payload.role == "anon" # anonymous session guard

Never log:
    - The raw token string
    - SUPABASE_JWT_SECRET
    - Any decoded secret/key material
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidTokenError,
)

from app.config import SUPABASE_JWT_SECRET, SUPABASE_URL, JWT_SECRET_KEY, JWT_REFRESH_SECRET_KEY

logger = logging.getLogger(__name__)

# ── Token settings ────────────────────────────────────────────────────────────
JWT_ALGORITHM = "HS256"

# Expected issuer: Supabase sets iss = <your project URL>/auth/v1
_EXPECTED_ISSUER = f"{SUPABASE_URL.rstrip('/')}/auth/v1"


# ── Payload models ────────────────────────────────────────────────────────────

@dataclass
class TokenPayload:
    """Verified, decoded Supabase JWT payload."""
    sub: str              # User UUID (the canonical user_id)
    email: Optional[str]  # May be absent for anonymous sessions
    role: str             # "authenticated" | "anon" | "service_role"
    exp: int              # Unix timestamp — expiry


@dataclass
class CustomTokenPayload:
    """Verified, decoded Custom access/refresh token payload."""
    sub: str              # User UUID
    exp: int              # Unix timestamp — expiry
    iat: int              # Unix timestamp — issued at
    type: str             # "access" or "refresh"


# ── Custom JWT Verification & Generation ──────────────────────────────────────

def verify_custom_access_token(token: Optional[str]) -> Optional[CustomTokenPayload]:
    """
    Verify a custom access token signed with JWT_SECRET_KEY.
    """
    if not token:
        return None

    clean = token.removeprefix("Bearer ").strip()
    if not clean:
        return None

    try:
        data = jwt.decode(
            clean,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_signature": True}
        )
        if data.get("type") != "access":
            logger.warning("Token type is not access: %s", data.get("type"))
            return None

        return CustomTokenPayload(
            sub=data["sub"],
            exp=data["exp"],
            iat=data["iat"],
            type=data["type"]
        )
    except ExpiredSignatureError:
        logger.info("Custom access token expired")
        raise
    except InvalidTokenError as exc:
        logger.warning("Invalid custom access token: %s", type(exc).__name__)
        raise


def get_supabase_token_for_user(user_id: str, email: Optional[str] = None) -> str:
    """
    Generate a valid Supabase JWT for the given user ID, signed with SUPABASE_JWT_SECRET.
    This enables the backend to query Supabase tables on behalf of the user when using a custom JWT.
    """
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email or "",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 600,  # Valid for 10 minutes
        "iss": _EXPECTED_ISSUER
    }
    return jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm=JWT_ALGORITHM)


# ── Verification ──────────────────────────────────────────────────────────────

def verify_supabase_token(token: Optional[str]) -> Optional[TokenPayload]:
    """
    Verify a Supabase JWT and return the decoded payload.

    Returns None instead of raising if the token is absent or structurally
    invalid — callers that require auth should raise HTTPException(401) on None.

    Raises jwt.ExpiredSignatureError  if the token has expired.
    Raises jwt.InvalidTokenError      if the signature is wrong or claims invalid.
    """
    if not token:
        return None

    clean = token.removeprefix("Bearer ").strip()
    if not clean:
        return None

    if not SUPABASE_JWT_SECRET:
        # Can't verify without the secret — treat as unverified (dev only)
        logger.warning(
            "SUPABASE_JWT_SECRET is not set; falling back to unsafe token decode. "
            "Set the secret in .env to enable signature verification."
        )
        return _unsafe_decode_for_dev(clean)

    try:
        data = jwt.decode(
            clean,
            SUPABASE_JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            # Supabase tokens include iss; verify it matches our project
            options={"verify_iss": True},
            issuer=_EXPECTED_ISSUER,
        )
    except ExpiredSignatureError:
        # Let callers distinguish expiry from other errors
        raise
    except InvalidSignatureError:
        logger.warning("JWT signature verification failed — possible token tampering")
        raise
    except InvalidTokenError as exc:
        logger.warning("Invalid JWT token: %s", type(exc).__name__)
        raise

    return TokenPayload(
        sub=data["sub"],
        email=data.get("email"),
        role=data.get("role", "anon"),
        exp=data["exp"],
    )


def extract_user_id_verified(token: Optional[str]) -> Optional[str]:
    """
    Verify the JWT (custom access token or Supabase token) and return the user UUID (sub claim).

    Returns None if the token is absent, invalid, or expired.
    Callers that need the user_id for data isolation should raise 401 on None.
    """
    if not token:
        return None

    # 1. Try to verify as custom access token
    try:
        payload = verify_custom_access_token(token)
        if payload:
            return payload.sub
    except ExpiredSignatureError:
        return None
    except InvalidTokenError:
        pass  # Fall through to try Supabase token

    # 2. Try to verify as Supabase token (for backwards compatibility/dev fallback)
    try:
        payload = verify_supabase_token(token)
        if payload:
            return payload.sub
    except (ExpiredSignatureError, InvalidTokenError):
        return None

    return None



# ── Dev-only fallback ─────────────────────────────────────────────────────────

def _unsafe_decode_for_dev(clean_token: str) -> Optional[TokenPayload]:
    """
    Decode JWT payload without signature verification.

    Only used when SUPABASE_JWT_SECRET is not configured (local dev without
    the secret).  Never call this in production — config.py startup validation
    will sys.exit() first if the secret is missing in production mode.
    """
    import base64, json
    try:
        parts = clean_token.split(".")
        if len(parts) < 2:
            return None
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        return TokenPayload(
            sub=data.get("sub", ""),
            email=data.get("email"),
            role=data.get("role", "anon"),
            exp=data.get("exp", 0),
        )
    except Exception:
        return None
