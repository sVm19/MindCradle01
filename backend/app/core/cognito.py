import logging
import base64
import json
from typing import Optional, Dict, Any
import jwt
from jwt import PyJWKClient, PyJWKClientError
import httpx
from app.config import (
    AWS_REGION,
    COGNITO_USER_POOL_ID,
    COGNITO_APP_CLIENT_ID,
    COGNITO_APP_CLIENT_SECRET,
    COGNITO_DOMAIN,
)

logger = logging.getLogger(__name__)

_jwk_client: Optional[PyJWKClient] = None

def get_jwk_client() -> Optional[PyJWKClient]:
    """Initialize and cache the PyJWKClient for Cognito's well-known keys."""
    global _jwk_client
    if _jwk_client is None and COGNITO_USER_POOL_ID:
        jwks_url = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
        _jwk_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwk_client


def verify_cognito_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify an incoming Cognito JWT token (ID or Access Token) using RS256 JWKS.
    Returns the decoded payload dict if valid, or None if invalid/expired.
    """
    if not token or not COGNITO_USER_POOL_ID:
        return None

    clean_token = token.removeprefix("Bearer ").strip()
    jwk_client = get_jwk_client()
    if not jwk_client:
        return None

    try:
        signing_key = jwk_client.get_signing_key_from_jwt(clean_token)
        issuer = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"

        # Verify signature, exp, and iss
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": True,
            "verify_aud": False,  # Manual audience/client_id verification below to support both ID and Access tokens
        }

        payload = jwt.decode(
            clean_token,
            key=signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options=options,
        )

        # Validate audience for ID tokens or client_id for Access tokens
        if COGNITO_APP_CLIENT_ID:
            token_use = payload.get("token_use")
            if token_use == "id":
                if payload.get("aud") != COGNITO_APP_CLIENT_ID:
                    logger.warning("Cognito ID token audience mismatch")
                    return None
            elif token_use == "access":
                if payload.get("client_id") != COGNITO_APP_CLIENT_ID:
                    logger.warning("Cognito Access token client_id mismatch")
                    return None

        return payload
    except (jwt.PyJWTError, PyJWKClientError) as e:
        logger.warning("Cognito JWT verification failed: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error verifying Cognito JWT: %s", e)
        return None


async def exchange_cognito_code_for_tokens(code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
    """
    Exchange an authorization code from Cognito Hosted UI for ID and Access tokens.
    """
    if not COGNITO_DOMAIN or not COGNITO_APP_CLIENT_ID:
        logger.error("COGNITO_DOMAIN or COGNITO_APP_CLIENT_ID is not configured.")
        return None

    # Normalize domain (strip https:// or trailing slashes)
    domain = COGNITO_DOMAIN.removeprefix("https://").removeprefix("http://").rstrip("/")
    token_url = f"https://{domain}/oauth2/token"

    data: Dict[str, str] = {
        "grant_type": "authorization_code",
        "client_id": COGNITO_APP_CLIENT_ID,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    if COGNITO_APP_CLIENT_SECRET:
        data["client_secret"] = COGNITO_APP_CLIENT_SECRET

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(token_url, data=data, headers=headers)
            if response.status_code != 200:
                logger.warning(
                    "Cognito code exchange failed: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                return None
            return response.json()
        except Exception as e:
            logger.error("Exception during Cognito code exchange: %s", e)
            return None


_alb_public_keys: Dict[str, str] = {}


def verify_alb_oidc_payload(oidc_data_header: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Cryptographically verify the ALB-injected 'x-amzn-oidc-data' JWT.
    ALB signs this header using an ES256 key published at:
    https://public-keys.auth.elb.{AWS_REGION}.amazonaws.com/{kid}
    """
    if not oidc_data_header or not AWS_REGION:
        return None

    clean_token = oidc_data_header.strip()
    try:
        header = jwt.get_unverified_header(clean_token)
        kid = header.get("kid")
        alg = header.get("alg")

        if not kid or alg != "ES256":
            logger.warning("ALB OIDC header missing kid or unsupported algorithm: %s", alg)
            return None

        # Fetch and cache AWS ALB public key
        public_key = _alb_public_keys.get(kid)
        if not public_key:
            key_url = f"https://public-keys.auth.elb.{AWS_REGION}.amazonaws.com/{kid}"
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(key_url)
                if resp.status_code != 200:
                    logger.warning("Failed to fetch ALB public key from %s: status=%s", key_url, resp.status_code)
                    return None
                public_key = resp.text
                _alb_public_keys[kid] = public_key

        payload = jwt.decode(
            clean_token,
            key=public_key,
            algorithms=["ES256"],
            options={"verify_exp": True, "verify_signature": True},
        )
        return payload
    except jwt.PyJWTError as e:
        logger.warning("ALB OIDC signature verification failed: %s", e)
        return None
    except Exception as e:
        logger.warning("Unexpected error verifying ALB OIDC header: %s", e)
        return None


def extract_alb_oidc_payload(oidc_data_header: Optional[str]) -> Optional[Dict[str, Any]]:
    """Verified wrapper around verify_alb_oidc_payload for backward compatibility."""
    return verify_alb_oidc_payload(oidc_data_header)

