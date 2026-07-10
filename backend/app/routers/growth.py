import logging
from fastapi import APIRouter, Header, HTTPException, Depends
from typing import Optional, List
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


@router.get("/experiments/active", response_model=ActiveAssignmentsList)
async def get_active_experiments(authorization: Optional[str] = Header(None)):
    """Fetch active A/B test variant assignments for the authenticated user."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication credentials not found or expired")
        
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


@router.post("/events")
async def track_growth_event(req: TrackEventRequest, authorization: Optional[str] = Header(None)):
    """Log an analytics clickstream or conversion event for funnel analysis."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication credentials not found or expired")
        
    success = await growth_engine.record_event(
        user_id=user_id,
        event_name=req.event_name,
        properties=req.properties,
        token=authorization
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to log growth event")
        
    return {"success": True}


@router.get("/experiments/stats", response_model=GrowthAnalyticsResponse)
async def get_growth_analytics(authorization: Optional[str] = Header(None)):
    """Retrieve full product analytics funnel drop-offs and A/B test results."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication credentials not found or expired")
        
    # Run stats calculation (Chi-Square/Z-test metrics and Funnel tracking)
    experiments_data = await growth_engine.get_experiment_analytics(authorization)
    funnel_data = await growth_engine.get_funnel_analytics(authorization)
    
    return GrowthAnalyticsResponse(
        experiments=experiments_data,
        funnel=funnel_data
    )


@router.post("/experiments/create")
async def create_experiment(req: CreateExperimentRequest, authorization: Optional[str] = Header(None)):
    """Admin-only API to launch new growth experiments."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication credentials not found or expired")
        
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
    except Exception as e:
        logger.error("Failed to create A/B experiment: %s", e)
        raise HTTPException(status_code=500, detail="Failed to register experiment")


@router.post("/experiments/{id}/status")
async def update_experiment_status(
    id: str, 
    req: UpdateExperimentStatusRequest, 
    authorization: Optional[str] = Header(None)
):
    """Admin-only API to pause, resume, or finish growth experiments."""
    user_id = extract_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication credentials not found or expired")
        
    if req.status not in ["draft", "running", "paused", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status value")
        
    try:
        updated = await pb.update_record(
            "ab_experiments",
            id,
            {"status": req.status},
            token=authorization
        )
        return {"success": True, "experiment": updated}
    except Exception as e:
        logger.error("Failed to update A/B experiment status: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update experiment status")
