import logging
from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from app.models.schemas import (
    TrackEventRequest,
    ActiveAssignmentResponse,
    ActiveAssignmentsList,
    GrowthAnalyticsResponse,
    CreateExperimentRequest,
    UpdateExperimentStatusRequest
)
from app.services.supabase import pb, extract_user_id
from app.services.growth_engine import growth_engine

router = APIRouter()
logger = logging.getLogger(__name__)

ERR_AUTH_CREDENTIALS = "Authentication credentials not found or expired"
STANDARD_RESPONSES = {
    401: {"description": "Authentication credentials not found or expired"},
    500: {"description": "Internal server error"}
}


@router.get(
    "/experiments/active",
    response_model=ActiveAssignmentsList,
    responses={401: {"description": ERR_AUTH_CREDENTIALS}}
)
async def get_active_experiments(authorization: Optional[str] = Header(None)):
    """Fetch active A/B test variant assignments for the authenticated user."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail=ERR_AUTH_CREDENTIALS)
        
    assignments = await growth_engine.get_active_assignments(user_id, authorization)
    
    formatted_assigns = []
    for a in assignments:
        formatted_assigns.append(ActiveAssignmentResponse(
            experiment_id=a["experiment_id"],
            experiment_name=a["experiment_name"],
            variant=a["variant"],
            variants=a["variants"]
        ))
        
    return ActiveAssignmentsList(assignments=formatted_assigns)


@router.post(
    "/events",
    responses=STANDARD_RESPONSES
)
async def track_growth_event(req: TrackEventRequest, authorization: Optional[str] = Header(None)):
    """Log an analytics clickstream or conversion event for funnel analysis."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail=ERR_AUTH_CREDENTIALS)
        
    success = await growth_engine.record_event(
        user_id=user_id,
        event_name=req.event_name,
        properties=req.properties,
        token=authorization
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to log growth event")
        
    return {"success": True}


@router.get(
    "/experiments/stats",
    response_model=GrowthAnalyticsResponse,
    responses={401: {"description": ERR_AUTH_CREDENTIALS}}
)
async def get_growth_analytics(authorization: Optional[str] = Header(None)):
    """Retrieve full product analytics funnel drop-offs and A/B test results."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail=ERR_AUTH_CREDENTIALS)
        
    # Run stats calculation (Chi-Square/Z-test metrics and Funnel tracking)
    experiments_data = await growth_engine.get_experiment_analytics(authorization)
    funnel_data = await growth_engine.get_funnel_analytics(authorization)
    
    return GrowthAnalyticsResponse(
        experiments=experiments_data,
        funnel=funnel_data
    )


async def _verify_admin(user_id: str, token: Optional[str]) -> None:
    try:
        profile_res = await pb.list_records("user_profiles", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
        items = profile_res.get("items") or []
        if items:
            profile = items[0]
            if profile.get("role") == "admin" or profile.get("is_admin") is True:
                return
    except Exception as e:
        logger.warning("Failed to check admin status for %s: %s", user_id, e)
    raise HTTPException(status_code=403, detail="Admin permissions required to manage experiments")


@router.post(
    "/experiments/create",
    responses={
        401: {"description": ERR_AUTH_CREDENTIALS},
        403: {"description": "Admin permissions required to manage experiments"},
        500: {"description": "Failed to register experiment"}
    }
)
async def create_experiment(req: CreateExperimentRequest, authorization: Optional[str] = Header(None)):
    """Admin-only API to launch new growth experiments."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail=ERR_AUTH_CREDENTIALS)
    
    await _verify_admin(user_id, authorization)
        
    try:
        new_expr = await pb.create_record(
            "ab_experiments",
            {
                "name": req.name,
                "description": req.description,
                "variants": req.variants,
                "status": "draft"
            },
            token=authorization
        )
        return {"success": True, "experiment": new_expr}
    except Exception:
        logger.exception("Failed to create A/B experiment")
        raise HTTPException(status_code=500, detail="Failed to register experiment")


@router.post(
    "/experiments/{id}/status",
    responses={
        400: {"description": "Invalid status value"},
        401: {"description": ERR_AUTH_CREDENTIALS},
        403: {"description": "Admin permissions required to manage experiments"},
        500: {"description": "Failed to update experiment status"}
    }
)
async def update_experiment_status(
    id: str, 
    req: UpdateExperimentStatusRequest, 
    authorization: Optional[str] = Header(None)
):
    """Admin-only API to pause, resume, or finish growth experiments."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail=ERR_AUTH_CREDENTIALS)
        
    if req.status not in ["draft", "running", "paused", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status value")
        
    await _verify_admin(user_id, authorization)

    try:
        updated = await pb.update_record(
            "ab_experiments",
            id,
            {"status": req.status},
            token=authorization
        )
        return {"success": True, "experiment": updated}
    except Exception:
        logger.exception("Failed to update A/B experiment status")
        raise HTTPException(status_code=500, detail="Failed to update experiment status")
