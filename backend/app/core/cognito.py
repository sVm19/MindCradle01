import logging
import base64
import json
import hmac
import hashlib
from typing import Optional, Dict, Any
from fastapi import HTTPException
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


# ── Direct Cognito API (Zero Hosted UI Redirects) ──────────────────────────────

def calculate_secret_hash(username: str) -> Optional[str]:
    """Calculate HMAC-SHA256 secret hash if app client has a secret."""
    if not COGNITO_APP_CLIENT_SECRET or not COGNITO_APP_CLIENT_ID:
        return None
    message = username + COGNITO_APP_CLIENT_ID
    dig = hmac.new(
        COGNITO_APP_CLIENT_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(dig).decode()


async def _call_cognito_idp(target_action: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Call low-level AWS Cognito IDP JSON 1.1 API."""
    region = AWS_REGION or "us-east-1"
    endpoint = f"https://cognito-idp.{region}.amazonaws.com/"
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": f"AWSCognitoIdentityProviderService.{target_action}",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(endpoint, json=body, headers=headers)
            data = resp.json() if resp.text else {}
        except Exception as e:
            logger.error("Network error contacting AWS Cognito: %s", e)
            raise HTTPException(status_code=502, detail="Unable to connect to AWS Cognito service.")

    if resp.status_code != 200:
        err_type = data.get("__type", "").split("#")[-1]
        msg = data.get("message", "Cognito request failed.")
        logger.warning("Cognito %s failed: [%s] %s", target_action, err_type, msg)

        if err_type == "NotAuthorizedException":
            raise HTTPException(status_code=401, detail=msg or "Incorrect email or password.")
        elif err_type == "UserNotConfirmedException":
            raise HTTPException(status_code=403, detail="USER_NOT_CONFIRMED")
        elif err_type == "UsernameExistsException":
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        elif err_type == "UserNotFoundException":
            raise HTTPException(status_code=401, detail="No account found with this email.")
        elif err_type == "CodeMismatchException":
            raise HTTPException(status_code=400, detail="Invalid verification code. Please check and try again.")
        elif err_type == "ExpiredCodeException":
            raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
        elif err_type == "InvalidPasswordException":
            raise HTTPException(status_code=400, detail=msg)
        else:
            raise HTTPException(status_code=400, detail=msg)

    return data


async def cognito_direct_authenticate(email: str, password: str) -> Dict[str, Any]:
    """Authenticate directly with Cognito using USER_PASSWORD_AUTH."""
    if not COGNITO_APP_CLIENT_ID:
        raise HTTPException(status_code=500, detail="COGNITO_APP_CLIENT_ID is not configured.")

    username = email.strip().lower()
    auth_params: Dict[str, str] = {
        "USERNAME": username,
        "PASSWORD": password,
    }
    secret_hash = calculate_secret_hash(username)
    if secret_hash:
        auth_params["SECRET_HASH"] = secret_hash

    body = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": COGNITO_APP_CLIENT_ID,
        "AuthParameters": auth_params,
    }
    data = await _call_cognito_idp("InitiateAuth", body)
    result = data.get("AuthenticationResult")
    if not result:
        raise HTTPException(status_code=401, detail="Authentication failed: No token returned.")
    return result


async def cognito_direct_sign_up(email: str, password: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Register a new user directly in Cognito."""
    if not COGNITO_APP_CLIENT_ID:
        raise HTTPException(status_code=500, detail="COGNITO_APP_CLIENT_ID is not configured.")

    username = email.strip().lower()
    user_attrs = [
        {"Name": "email", "Value": username},
    ]
    if name:
        user_attrs.append({"Name": "name", "Value": name.strip()})

    body: Dict[str, Any] = {
        "ClientId": COGNITO_APP_CLIENT_ID,
        "Username": username,
        "Password": password,
        "UserAttributes": user_attrs,
    }
    secret_hash = calculate_secret_hash(username)
    if secret_hash:
        body["SecretHash"] = secret_hash

    return await _call_cognito_idp("SignUp", body)


async def cognito_confirm_sign_up(email: str, code: str) -> bool:
    """Confirm user registration using the 6-digit confirmation code."""
    if not COGNITO_APP_CLIENT_ID:
        raise HTTPException(status_code=500, detail="COGNITO_APP_CLIENT_ID is not configured.")

    username = email.strip().lower()
    body: Dict[str, Any] = {
        "ClientId": COGNITO_APP_CLIENT_ID,
        "Username": username,
        "ConfirmationCode": code.strip(),
    }
    secret_hash = calculate_secret_hash(username)
    if secret_hash:
        body["SecretHash"] = secret_hash

    await _call_cognito_idp("ConfirmSignUp", body)
    return True


async def cognito_resend_confirmation_code(email: str) -> bool:
    """Resend 6-digit confirmation code."""
    if not COGNITO_APP_CLIENT_ID:
        raise HTTPException(status_code=500, detail="COGNITO_APP_CLIENT_ID is not configured.")

    username = email.strip().lower()
    body: Dict[str, Any] = {
        "ClientId": COGNITO_APP_CLIENT_ID,
        "Username": username,
    }
    secret_hash = calculate_secret_hash(username)
    if secret_hash:
        body["SecretHash"] = secret_hash

    await _call_cognito_idp("ResendConfirmationCode", body)
    return True

