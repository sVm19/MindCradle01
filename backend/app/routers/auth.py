from fastapi import APIRouter, HTTPException
from app.models.schemas import LoginRequest, SignupRequest, AuthResponse
from app.services.pocketbase import pb

router = APIRouter()


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Authenticate user via PocketBase."""
    try:
        result = await pb.auth_with_password(req.email, req.password)
        record = result["record"]
        return AuthResponse(
            token=result["token"],
            user_id=record["id"],
            name=record.get("name", ""),
            email=record["email"],
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    """Create a new user in PocketBase and return auth token."""
    try:
        await pb.create_user({
            "email": req.email,
            "password": req.password,
            "passwordConfirm": req.password_confirm,
            "name": req.name,
            "verified": True,
        })
        # Auto-login after signup
        result = await pb.auth_with_password(req.email, req.password)
        record = result["record"]
        return AuthResponse(
            token=result["token"],
            user_id=record["id"],
            name=record.get("name", ""),
            email=record["email"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
async def get_me():
    """Get current user profile. Requires auth header forwarding."""
    # Will be implemented with proper auth middleware
    return {"message": "Auth middleware pending"}
