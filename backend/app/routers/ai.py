import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from fastapi.responses import StreamingResponse
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import AIChatRequest, AIChatResponse, AIRecommendRequest
from app.services import nvidia_ai
from app.services.pocketbase import pb

router = APIRouter()
logger = logging.getLogger(__name__)

ARIA_SYSTEM_PROMPT = """You are ARIA, a quiet companion inside MindCradle.
You are not a therapist, doctor, or coach.
Validate feelings before offering any next step.
Ask at most one question in each response.
Reference prior context naturally when useful.
Offer exactly one MindCradle tool when relevant: breathing, Wind Down, or journal.
Never diagnose, never prescribe medication/supplements, and avoid clinical jargon.
Never use the phrases "As an AI", "I cannot give medical advice", or "I am not a doctor".
If self-harm or suicide language appears, respond warmly, offer 988 and text HOME to 741741, stay present if declined, and re-offer support every few turns.
Keep responses concise."""

CRISIS_KEYWORDS = [
    "kill myself",
    "end it all",
    "want to die",
    "suicide",
    "self-harm",
    "hurt myself",
    "no point living",
    "can't go on",
]

SAFETY_BANNED_TERMS = [
    "as an ai",
    "i cannot give medical advice",
    "i am not a doctor",
    "depression",
    "anxiety disorder",
    "adhd",
    "bipolar",
    "schizophrenia",
    "ptsd",
    "ocd",
    "ssri",
    "antidepressant",
    "benzodiazepine",
    "supplement",
    "medication",
    "dosage",
]


def _normalize_token(token: Optional[str]) -> str:
    if not token:
        return ""
    return token.removeprefix("Bearer ").strip()


def _decode_token_claims(token: str) -> dict:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    padded = payload + "=" * (-len(payload) % 4)
    try:
        import base64

        decoded = base64.urlsafe_b64decode(padded)
        return json.loads(decoded)
    except Exception:
        return {}


def _is_crisis_text(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in CRISIS_KEYWORDS)


def _passes_safety_filter(text: str) -> bool:
    lower = text.lower()
    return not any(term in lower for term in SAFETY_BANNED_TERMS)


def _crisis_handoff_message() -> str:
    return (
        "I am really glad you shared this with me. You do not have to hold this alone right now. "
        "If you might act on these thoughts, please call or text 988 right now, or text HOME to 741741 "
        "to reach the Crisis Text Line. If calling feels hard, I can stay with you while you take one small step."
    )


def _extract_top_words(entries: list[dict]) -> list[str]:
    counts: dict[str, int] = {}
    stop_words = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "been",
        "your",
        "just",
        "about",
        "today",
        "felt",
        "into",
    }

    for entry in entries:
        content = (entry.get("content") or "").lower()
        cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in content)
        for word in cleaned.split():
            if len(word) <= 3 or word in stop_words:
                continue
            counts[word] = counts.get(word, 0) + 1

    return [word for word, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:3]]


async def _build_user_context(token: str, conversation_id: Optional[str]) -> dict:
    claims = _decode_token_claims(token)
    user_id = claims.get("id", "")
    user_name = claims.get("name") or claims.get("email") or "Friend"
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    recent_moods = await pb.list_records(
        "mood_logs",
        token=token,
        params={"perPage": 50, "sort": "-created", "filter": f'created >= "{since}"'},
    )
    recent_journals = await pb.list_records(
        "journal_entries",
        token=token,
        params={"perPage": 50, "sort": "-created", "filter": f'created >= "{since}"'},
    )
    morning = await pb.list_records(
        "morning_rituals",
        token=token,
        params={"perPage": 1, "sort": "-created"},
    )
    wind_down = await pb.list_records(
        "wind_down_rituals",
        token=token,
        params={"perPage": 200, "sort": "-created"},
    )
    convo = await pb.list_records(
        "ai_conversations",
        token=token,
        params={"perPage": 1, "sort": "-updated"},
    )

    recent_mood_items = (recent_moods.get("items") or [])[:7]
    recent_journal_items = (recent_journals.get("items") or [])[:7]
    intention = None
    if morning.get("items"):
        intention = morning["items"][0].get("intention")

    wind_down_dates = {item.get("created", "")[:10] for item in (wind_down.get("items") or []) if item.get("created")}
    mood_dates = {item.get("created", "")[:10] for item in recent_mood_items if item.get("created")}
    streak = len(wind_down_dates.union(mood_dates))

    history_messages: list[dict] = []
    if convo.get("items"):
        messages = convo["items"][0].get("messages") or []
        if isinstance(messages, list):
            history_messages = messages[-10:]

    return {
        "user_id": user_id,
        "name": user_name,
        "intention": intention,
        "streak": streak,
        "recent_moods": [
            {
                "date": item.get("created"),
                "rating": item.get("level"),
                "tags": item.get("emotions") or [],
            }
            for item in recent_mood_items
        ],
        "recent_journal_themes": _extract_top_words(recent_journal_items),
        "conversation_history": history_messages,
        "conversation_id": conversation_id or "new",
    }


def _context_block(context: dict) -> str:
    return json.dumps(
        {
            "name": context["name"],
            "streak": context["streak"],
            "intention": context["intention"],
            "recentMoods": context["recent_moods"],
            "recentJournalThemes": context["recent_journal_themes"],
            "conversationHistory": context["conversation_history"],
        },
        ensure_ascii=True,
    )


async def _store_conversation(token: str, context: dict, user_message: str, ai_reply: str) -> None:
    history = list(context["conversation_history"])
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": ai_reply})
    history = history[-10:]

    existing = await pb.list_records(
        "ai_conversations",
        token=token,
        params={"perPage": 1, "sort": "-updated"},
    )
    items = existing.get("items", [])
    payload = {"messages": history, "summary": f"Latest exchange with {context['name']}"}
    if items:
        await pb.update_record("ai_conversations", items[0]["id"], payload, token=token)
    else:
        await pb.create_record(
            "ai_conversations",
            {
                **payload,
                "user": context["user_id"],
            },
            token=token,
        )


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    req: AIChatRequest,
    authorization: Optional[str] = Header(None),
):
    """Send a message to ARIA with safety and crisis handling."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    if _is_crisis_text(req.message):
        user_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
        logger.warning("ARIA crisis handoff triggered user=%s", user_hash)
        return AIChatResponse(
            reply=_crisis_handoff_message(),
            conversation_id=req.conversation_id or "new",
        )

    try:
        context = await _build_user_context(token, req.conversation_id)
        contextual_user_prompt = (
            "User context:\n"
            f"{_context_block(context)}\n\n"
            f"User message:\n{req.message}"
        )
        reply = await nvidia_ai.chat_completion(
            [{"role": "user", "content": contextual_user_prompt}],
            system_prompt=ARIA_SYSTEM_PROMPT,
            model="nemotron-4",
            temperature=0.7,
            top_p=0.9,
            max_tokens=180,
        )

        if not _passes_safety_filter(reply):
            raise HTTPException(
                status_code=500,
                detail="ARIA response failed safety filter and was blocked.",
            )

        await _store_conversation(token, context, req.message, reply)
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
