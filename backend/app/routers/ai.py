from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from app.models.schemas import AIChatRequest, AIChatResponse, AIRecommendRequest
from app.services import nvidia_ai

router = APIRouter()


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    req: AIChatRequest,
    authorization: Optional[str] = Header(None),
):
    """Send a message to the AI wellness assistant (non-streaming)."""
    try:
        reply = await nvidia_ai.chat_completion(
            [{"role": "user", "content": req.message}]
        )
        return AIChatResponse(
            reply=reply,
            conversation_id=req.conversation_id or "new",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(
    req: AIChatRequest,
    authorization: Optional[str] = Header(None),
):
    """Send a message to the AI wellness assistant (streaming SSE)."""
    async def generate():
        try:
            async for chunk in nvidia_ai.chat_completion_stream(
                [{"role": "user", "content": req.message}]
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/recommend")
async def recommend(
    req: AIRecommendRequest,
    authorization: Optional[str] = Header(None),
):
    """Get AI-powered resource recommendations based on context."""
    try:
        result = await nvidia_ai.get_recommendation(
            mood_level=5,
            emotions=[],
            history_summary=req.context,
        )
        return {"recommendation": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
