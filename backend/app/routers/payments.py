import logging
import re
import httpx
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request
from app.config import CREEM_API_KEY, CREEM_API_URL, CREEM_PRODUCT_ID
from app.services.supabase import pb, extract_user_id, extract_user_email

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/creem-checkout")
async def create_creem_checkout(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Create Creem checkout session"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
        
    token = authorization.removeprefix("Bearer ").strip()
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    email = extract_user_email(token)
    if not email:
        raise HTTPException(status_code=400, detail="Could not extract email from token")
        
    # Get Referer or Host for dynamic redirect URLs
    referer = request.headers.get("referer") or request.headers.get("host") or "https://mindcradle.online"
    host_match = re.match(r"^(https?://[^/]+)", referer)
    host = host_match.group(1) if host_match else referer.rstrip("/")
    
    payload = {
        "email": email,
        "product_id": CREEM_PRODUCT_ID,
        "success_url": f"{host}/billing?success=true",
        "cancel_url": f"{host}/billing?success=false",
        "metadata": {
            "user_id": user_id
        }
    }
    
    headers = {
        "x-api-key": CREEM_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CREEM_API_URL}/checkout",
                json=payload,
                headers=headers
            )
            
        if response.status_code == 200:
            return {"checkout_url": response.json().get("url")}
        else:
            logger.error("Creem checkout creation failed: %s %s", response.status_code, response.text)
            raise HTTPException(status_code=502, detail="Failed to create checkout session with Creem")
    except Exception as e:
        logger.error("Unexpected error in create_creem_checkout: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
