from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Header, HTTPException, status

from app.models.schemas import MorningRitualCreate, WindDownRitualCreate
from app.services.supabase import pb, extract_user_id
from app.core.security import verify_user_premium
from app.services import openrouter_ai

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


@router.get("/morning/prompt")
async def get_dynamic_morning_prompt(
    authorization: Optional[str] = Header(None)
):
    """
    Generate a dynamic focus prompt for the user's morning based on active life chapters and goals.
    """
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    fallback_prompt = "Focus on your breath and find small moments of peace today."

    try:
        # 1. Fetch current chapter
        ch_resp = await pb.list_records(
            "user_life_chapters",
            token=token,
            params={"filter": f'user_id="{user_id}" && is_current=true', "perPage": 1}
        )
        ch_items = ch_resp.get("items") or []
        current_ch = ch_items[0] if ch_items else None

        # 2. Fetch active goal threads
        goal_resp = await pb.list_records(
            "user_goal_threads",
            token=token,
            params={"filter": f'user_id="{user_id}" && status="growing"', "perPage": 5}
        )
        active_goals = goal_resp.get("items") or []

        if not current_ch and not active_goals:
            return {"prompt": fallback_prompt}

        # 3. Formulate LLM input
        context_str = ""
        if current_ch:
            context_str += f"Current Chapter: '{current_ch.get('title')}' ({current_ch.get('theme_summary')})\n"
        if active_goals:
            goal_labels = [g.get("target_node_label") for g in active_goals if g.get("target_node_label")]
            goal_strs = ", ".join(f"'{lbl}'" for lbl in goal_labels)
            context_str += f"Active Goals: {goal_strs}\n"

        sys_prompt = (
            "You are ARIA's ritual assistant in MindCradle.\n"
            "Write a short, highly personalized morning focus recommendation (1 sentence, max 15 words) based on the user's active life chapter and goal threads.\n"
            "Keep it encouraging, specific, and actionable. Frame it as a suggested anchor focus. Do not quote or prefix."
        )

        prompt_val = await openrouter_ai.chat_completion(
            messages=[{"role": "user", "content": context_str}],
            system_prompt=sys_prompt,
            temperature=0.7,
            max_tokens=100
        )
        return {"prompt": prompt_val.strip().strip('"').strip("'")}

    except Exception as exc:
        logger.warning("Failed to generate dynamic morning prompt: %s", exc)
        return {"prompt": fallback_prompt}


@router.get("/winddown/prompt")
async def get_dynamic_winddown_prompt(
    authorization: Optional[str] = Header(None)
):
    """
    Generate a dynamic letting-go question based on the user's active stressors.
    """
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    fallback_prompt = "Write down one thought or concern you wish to let go of tonight."

    try:
        # Fetch active stressors
        nodes_resp = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={"filter": f'user_id="{user_id}" && node_type="stressor" && is_archived=false && confidence>=0.4', "perPage": 3, "sort": "-confidence"}
        )
        stressors = nodes_resp.get("items") or []

        if not stressors:
            return {"prompt": fallback_prompt}

        selected_stressor = stressors[0].get("label")

        sys_prompt = (
            "You are ARIA's wind down assistant in MindCradle.\n"
            "The user is coping with this stressor: '" + selected_stressor + "'.\n"
            "Write a warm, non-judgmental question (1 sentence, max 20 words) for their evening wind-down to help them reflect on and let go of this stressor tonight."
        )

        prompt_val = await openrouter_ai.chat_completion(
            messages=[{"role": "user", "content": "Generate evening letting go question."}],
            system_prompt=sys_prompt,
            temperature=0.7,
            max_tokens=100
        )
        return {"prompt": prompt_val.strip().strip('"').strip("'")}

    except Exception as exc:
        logger.warning("Failed to generate dynamic winddown prompt: %s", exc)
        return {"prompt": fallback_prompt}

