import logging

from fastapi import APIRouter, HTTPException
from app.models.schemas import LoginRequest, SignupRequest, AuthResponse, RefreshRequest
from app.services.supabase import pb

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
