from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status

from app.models.schemas import MorningRitualCreate, WindDownRitualCreate
from app.services.supabase import pb, extract_user_id
from app.core.security import verify_user_premium

router = APIRouter()


async def check_ritual_limit(user_id: str, token: str):
    # Fetch user profile to verify premium
    try:
        profile_resp = await pb.list_records(
            "user_profiles",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = profile_resp.get("items") or []
        is_premium = False
        if items:
            is_premium, _ = verify_user_premium(items[0], user_id)
            
        if is_premium:
            return  # Unlimited access
            
        # Free tier limit check: count rituals completed today
        today_start = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")
        filter_str = f'user_id="{user_id}" && created >= "{today_start}"'
        
        mornings = await pb.list_records("morning_rituals", token=token, params={"filter": filter_str})
        wind_downs = await pb.list_records("wind_down_rituals", token=token, params={"filter": filter_str})
        
        total_today = len(mornings.get("items") or []) + len(wind_downs.get("items") or [])
        if total_today >= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Free tier is limited to 1 ritual per day. Upgrade to Premium for unlimited rituals."
            )
    except HTTPException:
        raise
    except Exception as e:
        # Fallback: if database fails, log and let request proceed or fail gracefully
        pass


@router.post("/morning")
async def save_morning_ritual(
    req: MorningRitualCreate,
    authorization: Optional[str] = Header(None),
):
    try:
        user_id = extract_user_id(authorization)
        if user_id:
            await check_ritual_limit(user_id, authorization)
            
        data = {
            "forecast": req.forecast,
            "intention": req.intention,
            "activity_type": req.activity_type,
            "completed_at": req.completed_at,
        }
        if user_id:
            data["user"] = user_id
        record = await pb.create_record(
            "morning_rituals",
            data,
            token=authorization,
        )
        return {"id": record["id"], "saved": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/winddown")
async def save_winddown_ritual(
    req: WindDownRitualCreate,
    authorization: Optional[str] = Header(None),
):
    try:
        user_id = extract_user_id(authorization)
        if user_id:
            await check_ritual_limit(user_id, authorization)
            
        data = {
            "release_item": req.release_item,
            "gratitudes": req.gratitudes,
            "audio_choice": req.audio_choice,
            "timer": req.timer,
        }
        if user_id:
            data["user"] = user_id
        record = await pb.create_record(
            "wind_down_rituals",
            data,
            token=authorization,
        )
        return {"id": record["id"], "saved": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def get_rituals_stats(
    authorization: Optional[str] = Header(None),
):
    try:
        user_id = extract_user_id(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        now_utc = datetime.now(timezone.utc)
        since_7d = (now_utc - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        filter_str = f'user_id="{user_id}" && created >= "{since_7d}"'
        
        try:
            mornings = await pb.list_records("morning_rituals", token=authorization, params={"filter": filter_str})
            morning_items = mornings.get("items") or []
        except Exception:
            morning_items = []
            
        try:
            wind_downs = await pb.list_records("wind_down_rituals", token=authorization, params={"filter": filter_str})
            wind_down_items = wind_downs.get("items") or []
        except Exception:
            wind_down_items = []
            
        unique_days = set()
        for item in morning_items + wind_down_items:
            created_str = item.get("created")
            if not created_str:
                continue
            # Extract date part: YYYY-MM-DD
            day_str = created_str.split("T")[0]
            unique_days.add(day_str)
            
        completed = min(len(unique_days), 7)
        return {"completed": completed, "total": 7}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
