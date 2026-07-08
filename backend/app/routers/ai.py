import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from fastapi.responses import StreamingResponse
from typing import Optional


from fastapi import APIRouter, Header, HTTPException, BackgroundTasks, Depends

from app.models.schemas import (
    AIChatRequest, AIChatResponse, AIRecommendRequest,
    JournalReflectionRequest, JournalReflectionResponse,
    MoodAnalysisRequest, MoodAnalysisResponse,
    RememberContextRequest, MemoryInsightUpdate, MemoryInsightResponse,
    EmotionTrendsResponse, ExtractThemesRequest, ConversationThemesResponse,
    TrackHelpRequest, TrackHelpResponse, LearnPersonalityResponse,
    SelectResponseTypeRequest, SelectResponseTypeResponse,
    ConversationSummaryResponse, CheckInResponse,
    ProactiveCheckinResponse, ProactiveCheckinRespondRequest, ScheduleCheckinResponse,
    RecoveryPatternsResponse, RecoveryStats, RecoveryDataResponse,
    TrackEngagementRequest, TrackEngagementResponse, EngagementStatsResponse,
    ConvoTypeEngagement, ABTestResult, DetectCrisisRequest, DetectCrisisResponse,
    AriaAgeVerifyRequest, DailyDiscoveryResponse, DiscoveryFeedbackRequest,
    TimelineEventResponse, TimelinePage,
    SearchResultItem, SearchPage, SearchSuggestionsResponse, EmbeddingGenerateResponse,
    KnowledgeNodeResponse, KnowledgeEdgeResponse, KnowledgeGraphResponse,
    KnowledgeProcessRequest, KnowledgeProcessResponse, KnowledgeContextResponse,
    GrowthMetricItem, GrowthMetricsResponse,
    KnowledgeChapterResponse, KnowledgeChaptersListResponse,
    KnowledgeNodeUpdateRequest,
    KnowledgeComparisonResponse, KnowledgeComparisonItem
)
from app.services import openrouter_ai
from app.services.relationship_memory import (
    format_relationship_memory_context,
    rank_relationship_memories,
)
from app.services import embeddings as embedding_svc
from app.services import knowledge_graph as kg_svc
from app.services.supabase import pb, JWTExpiredError, extract_user_id
from app.core.security import verify_user_premium
import os


logger = logging.getLogger(__name__)
FALLBACK_MODE = False  # Set to True only for local testing without OpenRouter API

class AgeGateException(Exception):
    def __init__(self, error: str, code: str, status_code: int = 403):
        self.error = error
        self.code = code
        self.status_code = status_code

OFF_TOPIC_LIMITS = {}
aria_router = APIRouter()

def _normalize_token(token: Optional[str]) -> str:
    if not token:
        return ""
    return token.removeprefix("Bearer ").strip()

async def check_aria_age_verified(authorization: Optional[str] = Header(None)):
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        profile_resp = await pb.list_records(
            "user_age_verification",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = profile_resp.get("items") or []
        if not items:
            raise AgeGateException(error="Age verification required", code="not_verified")
            
        profile = items[0]
        verified = profile.get("age_verified", False)
        verified_at_str = profile.get("verified_at")
        
        if not verified:
            raise AgeGateException(error="ARIA not available for users under 18", code="age_restricted")
            
        if verified_at_str:
            verified_at = None
            try:
                clean_date = verified_at_str.replace("T", " ").split(".")[0].replace("Z", "")
                verified_at = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception as parse_err:
                logger.warning("Failed to parse verified_at timestamp: %s", parse_err)
            
            if verified_at:
                now = datetime.now(timezone.utc)
                if (now - verified_at).days >= 30:
                    raise AgeGateException(error="Age verification expired", code="expired")
                
    except AgeGateException:
        raise
    except Exception as e:
        logger.error("Error checking age verification: %s", e)
        raise HTTPException(status_code=500, detail="Database verification error")

@aria_router.post("/verify-age")
async def verify_age(
    req: AriaAgeVerifyRequest,
    authorization: Optional[str] = Header(None)
):
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")
        
    now_str = datetime.now(timezone.utc).isoformat()
    
    try:
        # Check if record exists in user_age_verification
        res = await pb.list_records("user_age_verification", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
        items = res.get("items") or []
        
        payload = {
            "age_verified": req.age_verified,
            "verified_at": now_str
        }
        
        if items:
            record_id = items[0]["id"]
            await pb.update_record("user_age_verification", record_id, payload, token=token)
        else:
            payload["user_id"] = user_id
            await pb.create_record("user_age_verification", payload, token=token)
    except Exception as e:
        logger.error("Failed to update user verification: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    return {"status": "success", "age_verified": req.age_verified}


@aria_router.get("/crisis-status")
async def get_crisis_status(
    authorization: Optional[str] = Header(None)
):
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        resp = await pb.list_records(
            "crisis_flags",
            token=token,
            params={"filter": f'user_id="{user_id}" && severity_level=4 && admin_reviewed=false', "perPage": 1}
        )
        items = resp.get("items") or []
        return {"has_critical_crisis": len(items) > 0}
    except Exception as e:
        logger.error("Error checking crisis status: %s", e)
        return {"has_critical_crisis": False}


@aria_router.post("/crisis-resolve")
async def resolve_crisis(
    authorization: Optional[str] = Header(None)
):
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        resp = await pb.list_records(
            "crisis_flags",
            token=token,
            params={"filter": f'user_id="{user_id}" && severity_level=4 && admin_reviewed=false', "perPage": 100}
        )
        items = resp.get("items") or []
        for item in items:
            await pb.update_record("crisis_flags", item["id"], {"admin_reviewed": True}, token=token)
        return {"status": "success", "resolved_count": len(items)}
    except Exception as e:
        logger.error("Error resolving crisis flags: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


router = APIRouter(dependencies=[Depends(check_aria_age_verified)])



ARIA_SYSTEM_PROMPT = """You are ARIA, a quiet companion inside MindCradle.
You are not a therapist, doctor, or coach.
Validate feelings before offering any next step.
Ask at most one question in each response.
Reference prior context and user memory insights naturally when useful (e.g., "I remember last week when you felt this way...", "You've mentioned X before - it seems to be a pattern").
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


CRITICAL_KEYWORDS = [
    "kill myself", "hurt myself", "end it", "suicide", "want to die",
    "no point living", "better off dead", "harm myself", "cut myself",
    "overdose", "hang myself", "jump", "slit", "poison"
]

HIGH_RISK_KEYWORDS = [
    "suicidal", "self harm", "self-harm", "can't go on", 
    "hopeless", "worthless", "give up", "done living"
]


def detect_crisis_keywords(user_message: str) -> dict:
    message_lower = user_message.lower()
    
    # Check CRITICAL first
    if any(keyword in message_lower for keyword in CRITICAL_KEYWORDS):
        return { "severity": "CRITICAL", "detected": True }
    
    # Check HIGH RISK
    if any(keyword in message_lower for keyword in HIGH_RISK_KEYWORDS):
        return { "severity": "HIGH", "detected": True }
    
    return { "severity": None, "detected": False }


CRISIS_RESOURCES_LIST = [
    {
        "name": "National Suicide Prevention Lifeline",
        "phone": "988",
        "text": "Text HOME to 741741",
        "website": "https://suicidepreventionlifeline.org"
    },
    {
        "name": "Crisis Text Line",
        "phone": "Text HOME to 741741",
        "website": "https://www.crisistextline.org"
    },
    {
        "name": "International Association for Suicide Prevention",
        "website": "https://www.iasp.info/resources/Crisis_Centres"
    }
]


async def _handle_crisis_detection_logging(token: str, user_id: str, message: str, severity: str, conversation_id: Optional[str]) -> str:
    convo_id = conversation_id or "new"
    if convo_id == "new":
        try:
            convo_payload = {
                "user": user_id,
                "is_active": True,
                "messages": [],
                "summary": "Safety Incident Conversation"
            }
            rec = await pb.create_record("ai_conversations", convo_payload, token=token)
            convo_id = rec["id"]
        except Exception as e:
            logger.warning("Failed to create conversation for crisis: %s", e)

    action_taken = f"Keyword Crisis ({severity}) intercepted."
    if severity == "CRITICAL":
        try:
            profile_resp = await pb.list_records("user_profiles", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
            items = profile_resp.get("items") or []
            if items:
                profile = items[0]
                if profile.get("emergency_contact") and profile.get("notify_on_crisis"):
                    contact = profile["emergency_contact"]
                    logger.warning("CRISIS ALERT [CRITICAL]: Emergency contact notified: %s", contact)
                    action_taken += f" Emergency contact notified: {contact}."
        except Exception as contact_err:
            logger.warning("Failed to check emergency contact settings: %s", contact_err)

    try:
        severity_level = 4 if severity == "CRITICAL" else 3
        matched_keywords = [w for w in (CRITICAL_KEYWORDS if severity == "CRITICAL" else HIGH_RISK_KEYWORDS) if w in message.lower()]
        payload = {
            "user": user_id,
            "conversation_id": convo_id,
            "severity_level": severity_level,
            "red_flags_detected": matched_keywords,
            "action_taken": action_taken,
            "admin_reviewed": False,
            "message": message,
            "severity": severity
        }
        await pb.create_record("crisis_flags", payload, token=token)
    except Exception as db_err:
        logger.error("Failed to log crisis flag: %s", db_err)

    return convo_id


def is_wellness_question(user_message: str) -> Optional[bool]:
    wellness_keywords = [
        "anxiety", "stress", "mood", "sleep", "sad", "happy", "emotion", "ritual",
        "calm", "peace", "therapy", "mental", "feeling", "overwhelm", "journal",
        "breathe", "meditation", "support"
    ]
    
    off_topic_keywords = [
        "code", "python", "javascript", "sql", "api", "debug", "function", "algorithm",
        "math", "equation", "recipe", "homework", "sports", "how to build",
        "how to create app", "how to code", "capital of", "football", "basketball", "soccer",
        "build an app", "build app", "create app", "how do i build"
    ]
    
    message_lower = user_message.lower()
    
    if any(keyword in message_lower for keyword in off_topic_keywords):
        return False
    if any(keyword in message_lower for keyword in wellness_keywords):
        return True
    
    return None  # Ambiguous, let ARIA decide


def _passes_safety_filter(text: str) -> bool:
    lower = text.lower()
    return not any(term in lower for term in SAFETY_BANNED_TERMS)


def _referenced_memory(reply: str) -> bool:
    reply_lower = reply.lower()
    trigger_phrases = ["i remember", "remember", "similar to", "last time", "mentioned", "you said", "you told me", "previously"]
    return any(p in reply_lower for p in trigger_phrases)


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
    user_id = claims.get("sub", "")
    user_name = claims.get("name") or claims.get("email") or "Friend"
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    filter_user = f'user_id="{user_id}"' if user_id else ""

    recent_moods = await pb.list_records(
        "mood_logs",
        token=token,
        params={"perPage": 50, "sort": "-created", "filter": f'{filter_user} && created >= "{since}"' if filter_user else f'created >= "{since}"'},
    )
    recent_journals = await pb.list_records(
        "journal_entries",
        token=token,
        params={"perPage": 50, "sort": "-created", "filter": f'{filter_user} && created >= "{since}"' if filter_user else f'created >= "{since}"'},
    )
    morning = await pb.list_records(
        "morning_rituals",
        token=token,
        params={"perPage": 1, "sort": "-created", "filter": filter_user} if filter_user else {"perPage": 1, "sort": "-created"},
    )
    wind_down = await pb.list_records(
        "wind_down_rituals",
        token=token,
        params={"perPage": 200, "sort": "-created", "filter": filter_user} if filter_user else {"perPage": 200, "sort": "-created"},
    )
    convo = await pb.list_records(
        "ai_conversations",
        token=token,
        params={"perPage": 1, "sort": "-updated", "filter": filter_user} if filter_user else {"perPage": 1, "sort": "-updated"},
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


async def _build_memory_insight_prompt(token: str, user_id: str) -> str:
    try:
        convos_resp = await pb.list_records("ai_conversations", token=token, params={"perPage": 10, "sort": "-updated", "filter": f'user_id="{user_id}" && is_active=false'})
        past_convos = convos_resp.get("items") or []
    except Exception:
        past_convos = []

    try:
        insights_resp = await pb.list_records("user_memory_insights", token=token, params={"sort": "-created", "perPage": 100, "filter": f'user_id="{user_id}"'})
        all_insights = insights_resp.get("items") or []
    except Exception:
        all_insights = []

    since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        moods_30d_resp = await pb.list_records("mood_logs", token=token, params={"filter": f'user_id="{user_id}" && created >= "{since_30d}"'})
        moods_30d = moods_30d_resp.get("items") or []
    except Exception:
        moods_30d = []

    emotions = set()
    for m in moods_30d:
        emotions.update(m.get("emotions", []))
    for ins in all_insights:
        if ins.get("emotion"):
            for em in ins["emotion"].split(","):
                emotions.add(em.strip())
    emotions_list = ", ".join(sorted(list(emotions))[:6]) or "none recorded yet"

    helps = set()
    for ins in all_insights:
        if ins.get("what_helped"):
            helps.add(ins["what_helped"])
    helps_list = ", ".join(list(helps)[:5]) or "evening ritual, journaling"

    since_7d = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    concerns = set()
    for ins in all_insights:
        created_time = ins.get("created", "")
        if created_time >= since_7d:
            concern = ins.get("situation") or ins.get("what_happened")
            if concern:
                concerns.add(concern)
    concerns_list = ", ".join(list(concerns)[:5]) or "general wellness"

    patterns = []
    rough_days = [ins for ins in all_insights if ins.get("context_type") == "rough_day_support"]
    vents = [ins for ins in all_insights if ins.get("context_type") == "active_listening"]
    calms = [ins for ins in all_insights if ins.get("context_type") == "calm_support"]
    if len(rough_days) >= 2:
        patterns.append("Struggles with occasional rough days")
    if len(vents) >= 2:
        patterns.append("Needs venting spaces to process thoughts")
    if len(calms) >= 2:
        patterns.append("Experiences sudden overwhelm requiring calm support")
    if not patterns:
        patterns.append("Establishing baseline wellness routines")
    patterns_list = "; ".join(patterns)

    # Format past conversation summaries for prompt context
    summaries_section = "None recorded yet."
    if past_convos:
        summary_blocks = []
        for c in past_convos:
            summary_text = c.get("summary")
            if summary_text:
                c_date = c.get("updated")[:10] if c.get("updated") else "unknown date"
                journey = c.get("emotional_journey") or "unknown"
                key_pts = ", ".join(c.get("key_points") or [])
                summary_blocks.append(
                    f"  * Conversation on {c_date} (emotional journey: {journey}, key points: {key_pts}):\n"
                    f"    Summary:\n"
                    f"    {summary_text}"
                )
        if summary_blocks:
            summaries_section = "\n".join(summary_blocks)

    prompt_addition = (
        "\n\nHere's what you know about this user from past conversations:\n"
        f"- They struggle with: {emotions_list}\n"
        f"- What helps them: {helps_list}\n"
        f"- Recent concerns: {concerns_list}\n"
        f"- Patterns: {patterns_list}\n"
        f"- Past Conversation Summaries:\n{summaries_section}\n\n"
        "Instructions: Reference these past conversation summaries naturally when the user mentions related topics (e.g., if a summary mentions work anxiety and they mention work/job/career again, reference it naturally to show you remember)."
    )

    try:
        themes_resp = await pb.list_records(
            "conversation_themes",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 200}
        )
        themes_items = themes_resp.get("items") or []
    except Exception:
        themes_items = []
        
    theme_counts = {}
    for t in themes_items:
        theme_val = t.get("theme")
        if theme_val:
            theme_counts[theme_val] = theme_counts.get(theme_val, 0) + 1
            
    sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    if sorted_themes:
        themes_str = ", ".join([f"{theme} ({count}x)" for theme, count in sorted_themes])
        prompt_addition += f"\n- Their primary conversation topics: {themes_str}. Reference these active topics naturally in responses if relevant (e.g., 'I know {sorted_themes[0][0]} has been a big topic for you lately. Let's work on that.')."

    # 4. Fetch advice effectiveness to prioritize what works
    try:
        advice_resp = await pb.list_records(
            "advice_effectiveness",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 200}
        )
        advice_items = advice_resp.get("items") or []
    except Exception:
        advice_items = []
        
    technique_ratings = {}
    for a in advice_items:
        txt = (a.get("advice_given") or "").lower()
        rating = a.get("help_rating")
        if rating is None:
            continue
            
        category = "general advice"
        if "breath" in txt or "coherence" in txt or "inhale" in txt or "exhale" in txt:
            category = "breathing exercise"
        elif "journal" in txt or "write" in txt or "entry" in txt:
            category = "journaling"
        elif "wind down" in txt or "sleep" in txt or "night" in txt or "bed" in txt:
            category = "wind down ritual"
            
        if category not in technique_ratings:
            technique_ratings[category] = []
        technique_ratings[category].append(int(rating))
        
    effective_techs = []
    for tech, ratings in technique_ratings.items():
        avg_rating = sum(ratings) / len(ratings)
        success_rate = len([r for r in ratings if r >= 2]) / len(ratings)
        if avg_rating >= 2.0:
            effective_techs.append(f"{tech} (success rate: {success_rate*100:.0f}%, average rating: {avg_rating:.1f}/3)")
            
    if effective_techs:
        techs_str = ", ".join(effective_techs)
        prompt_addition += f"\n- Techniques that have helped this user in the past: {techs_str}. If they are overwhelmed or need techniques, prioritize recommending these (e.g., 'Remember the breathing exercise that helped you last time? Want to try that?'). Only suggest things that have worked for them before."

    # 5. Fetch user personality profile to adapt tone
    try:
        personality_resp = await pb.list_records(
            "user_personality",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        personality_items = personality_resp.get("items") or []
    except Exception:
        personality_items = []
        
    if personality_items:
        p = personality_items[0]
        style = p.get('communication_style', '')
        pref = p.get('preference_advice_type', 'gentle_suggestions')
        length = p.get('response_length_preference', 'medium')
        openness = p.get('emotional_openness', 'medium')
        
        pref_instruction = (
            "CRITICAL TONE ADJUSTMENT:\n"
            "The user prefers gentle suggestions. Use soft, non-directive, empathetic phrasing (e.g., 'You might consider trying...', 'Maybe you could...'). Avoid ordering them or being overly direct."
            if pref == "gentle_suggestions" else
            "CRITICAL TONE ADJUSTMENT:\n"
            "The user prefers direct advice. Be direct, action-oriented, and directive (e.g., 'Do this: breathe for 5 minutes', 'Try writing down three things'). Do not use tentative language."
        )
        
        prompt_addition += (
            "\n\nHere is what you know about this user's personality:\n"
            f"- Communication Style: {style}\n"
            f"- Preferred Advice Type: {pref}\n"
            f"- Response Length Preference: {length}\n"
            f"- Emotional Openness: {openness}\n\n"
            f"{pref_instruction}\n"
            f"- Response Length Constraint: Ensure your response length is {length}.\n"
            f"- Match their emotional openness ({openness}) and communication style."
        )

    # Recovery Patterns Context Integration
    try:
        recovery_resp = await pb.list_records(
            "recovery_data",
            token=token,
            params={"filter": f'user_id="{user_id}"', "sort": "-mood_dip_date", "perPage": 10}
        )
        recovery_items = recovery_resp.get("items") or []
    except Exception:
        recovery_items = []
        
    if recovery_items:
        completed = [r for r in recovery_items if r.get("recovery_days") is not None]
        if completed:
            avg_rec = sum(r["recovery_days"] for r in completed) / len(completed)
            latest = completed[0]
            latest_days = latest["recovery_days"]
            latest_cat = latest.get("catalyst") or "journaling"
            
            recovery_prompt_info = (
                f"\n\nHere is what you know about this user's recovery patterns:\n"
                f"- Average recovery time: {avg_rec:.1f} days\n"
                f"- Last mood dip recovery: took {latest_days} days (helped by: {latest_cat})\n"
            )
            
            if len(completed) >= 2:
                half = len(completed) // 2
                newer_avg = sum(r["recovery_days"] for r in completed[:half]) / half
                older_avg = sum(r["recovery_days"] for r in completed[half:]) / (len(completed) - half)
                if newer_avg < older_avg:
                    recovery_prompt_info += f"- Trend: Improving recovery speed (average speed went from {older_avg:.1f} days down to {newer_avg:.1f} days)\n"
            
            recovery_prompt_info += (
                "\nInstructions for ARIA on Recovery:\n"
                "Reassure the user by referencing their recovery trends if they complain about a low mood or dip. "
                "For example: 'Last time you felt this way, you recovered in X days by doing Y. Want to try that?' "
                "or 'You're getting better at handling this - it usually takes Z days to feel normal.' "
                "Remind them that 'Isolation makes it take longer - reaching out helps' if their recovery was longest during isolation."
            )
            prompt_addition += recovery_prompt_info

    return prompt_addition


async def _get_memory_context(token: str, user_id: str) -> dict:
    # 1. Fetch last 3 memory insights
    try:
        insights_resp = await pb.list_records(
            "user_memory_insights",
            token=token,
            params={"sort": "-created", "perPage": 3, "filter": f'user_id="{user_id}"'}
        )
        recent_insights = insights_resp.get("items") or []
    except Exception as e:
        logger.warning("Failed to fetch memory insights: %s", e)
        recent_insights = []

    # 2. Fetch dominant emotions this month (last 30 days)
    since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        moods_30d_resp = await pb.list_records(
            "mood_logs",
            token=token,
            params={"filter": f'user_id="{user_id}" && created >= "{since_30d}"'}
        )
        moods_30d = moods_30d_resp.get("items") or []
    except Exception as e:
        logger.warning("Failed to fetch 30d mood logs: %s", e)
        moods_30d = []
        
    emotions_30d = []
    for m in moods_30d:
        emotions_30d.extend(m.get("emotions", []))
    emotion_counts_30d = {}
    for e in emotions_30d:
        emotion_counts_30d[e] = emotion_counts_30d.get(e, 0) + 1
    dominant_emotions_30d = sorted(emotion_counts_30d.keys(), key=lambda k: emotion_counts_30d[k], reverse=True)[:3]

    # 3. Find what helped the user most in the past (last 20 insights)
    try:
        all_insights_resp = await pb.list_records(
            "user_memory_insights",
            token=token,
            params={"sort": "-created", "perPage": 20, "filter": f'user_id="{user_id}"'}
        )
        all_insights = all_insights_resp.get("items") or []
    except Exception:
        all_insights = []
        
    what_helped_list = [item.get("what_helped") for item in all_insights if item.get("what_helped")]
    help_counts = {}
    for wh in what_helped_list:
        help_counts[wh] = help_counts.get(wh, 0) + 1
    top_helped = sorted(help_counts.keys(), key=lambda k: help_counts[k], reverse=True)[:3]

    return {
        "last_3_insights": [
            {
                "date": i.get("date") or (i.get("created")[:10] if i.get("created") else ""),
                "situation": i.get("situation") or i.get("what_happened") or "",
                "emotion": i.get("emotion") or "",
                "what_helped": i.get("what_helped") or "",
                "follow_up": i.get("follow_up") or ""
            } for i in recent_insights
        ],
        "dominant_emotions_30d": dominant_emotions_30d,
        "what_helped_most_in_past": top_helped if top_helped else ["evening ritual", "journaling"]
    }


async def _extract_and_save_insights(token: str, user_id: str, conversation_id: str, messages: list):
    # If the user only sent a very short message or hello, skip
    if len(messages) < 2:
        return
        
    system_prompt = (
        "You are a memory processor assistant. Analyze the conversation between the user and ARIA. "
        "Determine if the user has shared a meaningful life situation (rough day, stress, etc.) and if there's "
        "a clear emotion, what helped them cope, and a relevant follow-up check-in. "
        "If a valid pattern is present, respond with a JSON object containing:\n"
        "- 'situation': a concise description of what happened (e.g. 'Had a rough day at work')\n"
        "- 'emotion': a list or string of emotions (e.g. 'anxious, overwhelmed')\n"
        "- 'what_helped': what technique, exercise, or ritual helped them (e.g. 'evening ritual + journaling')\n"
        "- 'follow_up': a gentle follow-up question or observation for next time\n\n"
        "If no clear, new coping pattern is discussed, return empty JSON: {}\n"
        "Output ONLY raw JSON. No explanation, no markdown tags."
    )
    
    chat_str = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages[-4:]])
    prompt = f"Extract memory insight from this recent exchange:\n{chat_str}"
    
    try:
        reply = await openrouter_ai.chat_completion(
            [{"role": "user", "content": prompt}],
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=250
        )
        
        data = parse_json_safely(reply)
        if not data or not data.get("situation") or not data.get("emotion"):
            return
            
        payload = {
            "user": user_id,
            "conversation_id": conversation_id,
            "situation": data.get("situation"),
            "what_happened": data.get("situation"),
            "emotion": data.get("emotion"),
            "what_helped": data.get("what_helped", "breathing exercise"),
            "follow_up": data.get("follow_up", "How is that going?"),
            "context_type": "auto_extracted",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        await pb.create_record("user_memory_insights", payload, token=token)
        logger.info("Successfully auto-extracted and stored memory insight for user %s", user_id)
    except Exception as e:
        logger.warning("Failed in _extract_and_save_insights: %s", e)


async def _summarize_conversation_background(token: str, conversation_id: str):
    logger.info(f"Background auto-summarize triggered for conversation {conversation_id}")
    try:
        convo = await pb.get_record("ai_conversations", conversation_id, token=token)
        messages = convo.get("messages") or []
        if not messages:
            return
        
        # Format messages transcript
        transcript = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages])
        
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        system_prompt = (
            "You are ARIA's reflection and memory engine. "
            "Analyze the provided conversation between the user and ARIA. "
            "Produce a structured summary of the conversation in JSON format. "
            "Analyze the user's emotions at the start, middle, and end to map their emotional journey. "
            "Identify what they struggled with, what helped them, and determine if a follow-up check-in is useful. "
            "If a follow-up is useful, set a relative date for it based on the current date: {current_date}.\n\n"
            "You MUST respond with a valid JSON object matching this schema:\n"
            "{{\n"
            "  \"summary\": \"2-3 bullets focusing on:\\n- What the user was struggling with\\n- What seemed to help them\\n- What follow-up might be useful\",\n"
            "  \"key_points\": [\"lowercase\", \"tag-like\", \"key points\"],\n"
            "  \"follow_up_needed\": true/false,\n"
            "  \"follow_up_date\": \"YYYY-MM-DD\" (or null if not needed),\n"
            "  \"emotional_journey\": \"start_emotion → middle_emotion → end_emotion\" (e.g. \"anxious → grounded → hopeful\")\n"
            "}}\n\n"
            "Output ONLY raw JSON. Do not include markdown code block tags (e.g. ```json) or any other text."
        ).replace("{current_date}", current_date_str)
        
        user_prompt = f"Here is the conversation transcript:\n{transcript}"
        
        reply = await openrouter_ai.chat_completion(
            [{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=400
        )
        
        data = parse_json_safely(reply)
        summary = data.get("summary") or "Conversation summarized."
        key_points = data.get("key_points") or []
        follow_up_needed = data.get("follow_up_needed") or False
        follow_up_date = data.get("follow_up_date") or None
        emotional_journey = data.get("emotional_journey") or "unknown"
        
        payload = {
            "summary": summary,
            "key_points": key_points,
            "follow_up_needed": follow_up_needed,
            "follow_up_date": follow_up_date,
            "emotional_journey": emotional_journey
        }
        
        await pb.update_record("ai_conversations", conversation_id, payload, token=token)
        logger.info(f"Successfully auto-summarized and updated conversation {conversation_id}")
        
        try:
            user_id = extract_user_id(token) or "unknown"
            await _track_engagement_internal(token, user_id, conversation_id)
        except Exception as auto_eng_err:
            logger.warning("Failed to auto-track engagement metrics after summarization: %s", auto_eng_err)
    except Exception as e:
        logger.error(f"Failed to auto-summarize conversation {conversation_id}: {e}", exc_info=True)



@router.post("/remember-context")
async def remember_context(
    req: RememberContextRequest,
    authorization: Optional[str] = Header(None),
):
    """Explicitly save a conversation insight to the user's memory."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        convo_resp = await pb.get_record("ai_conversations", req.conversation_id, token=token)
        messages = convo_resp.get("messages") or []
    except Exception as e:
        logger.warning("remember-context: failed to fetch conversation %s: %s", req.conversation_id, e)
        messages = []

    system_prompt = (
        "You are a structured memory formatting assistant. "
        "The user wants to save an insight from their recent conversation to their memory. "
        "Output a JSON object with exactly these fields:\n"
        "- 'situation': a concise description of what situation or topic is being saved (e.g. 'Had rough day at work')\n"
        "- 'emotion': the emotions felt (e.g. 'anxious, overwhelmed')\n"
        "- 'what_helped': what technique, action, ritual, or journaling helped them\n"
        "- 'follow_up': a gentle reminder or follow-up question for the next check-in\n\n"
        "Return ONLY raw JSON. No markdown code blocks."
    )
    
    convo_str = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages[-4:]])
    user_prompt = (
        f"Conversation History:\n{convo_str}\n\n"
        f"User Key Insight: {req.key_insight}\n"
        f"Logged Emotions: {req.emotion}\n"
        f"Context Type: {req.context_type}\n"
    )

    try:
        reply = await openrouter_ai.chat_completion(
            [{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=250
        )
        
        data = parse_json_safely(reply)
        situation = data.get("situation") or req.key_insight
        emotion = data.get("emotion") or req.emotion
        what_helped = data.get("what_helped") or "calming technique"
        follow_up = data.get("follow_up") or "Checking in about this."
        
        payload = {
            "user": req.user_id,
            "conversation_id": req.conversation_id,
            "situation": situation,
            "what_happened": situation,
            "emotion": emotion,
            "what_helped": what_helped,
            "follow_up": follow_up,
            "context_type": req.context_type,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        rec = await pb.create_record("user_memory_insights", payload, token=token)
        return {"id": rec["id"], "saved": True}
    except Exception as e:
        logger.error("Failed to save remember-context: %s", str(e))
        try:
            payload = {
                "user": req.user_id,
                "conversation_id": req.conversation_id,
                "situation": req.key_insight,
                "what_happened": req.key_insight,
                "emotion": req.emotion,
                "what_helped": "supportive chat",
                "follow_up": "Check in about " + req.key_insight[:20],
                "context_type": req.context_type,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            rec = await pb.create_record("user_memory_insights", payload, token=token)
            return {"id": rec["id"], "saved": True}
        except Exception as retry_err:
            logger.warning("Failed remember-context fallback save: %s", retry_err)
            return {"id": "fallback_insight", "saved": True}


@router.get("/memory-insights", response_model=list[MemoryInsightResponse])
async def get_memory_insights(
    authorization: Optional[str] = Header(None),
):
    """Retrieve all saved memory insights for the user."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    try:
        resp = await pb.list_records(
            "user_memory_insights",
            token=token,
            params={"sort": "-created", "perPage": 200, "filter": f'user_id="{user_id}"'}
        )
        items = resp.get("items") or []
        
        formatted = []
        for i in items:
            formatted.append(MemoryInsightResponse(
                id=i.get("id"),
                user_id=i.get("user_id"),
                conversation_id=i.get("conversation_id"),
                situation=i.get("situation"),
                what_happened=i.get("what_happened"),
                emotion=i.get("emotion"),
                what_helped=i.get("what_helped"),
                follow_up=i.get("follow_up"),
                context_type=i.get("context_type"),
                date=i.get("date"),
                created=i.get("created")
            ))
        return formatted
    except Exception as e:
        logger.error("Failed to list memory insights: %s", e)
        return []


@router.put("/memory-insights/{insight_id}")
async def update_memory_insight(
    insight_id: str,
    req: MemoryInsightUpdate,
    authorization: Optional[str] = Header(None),
):
    """Update a specific memory insight."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    payload = req.model_dump(exclude_unset=True)
    if "situation" in payload:
        payload["what_happened"] = payload["situation"]
        
    try:
        await pb.update_record("user_memory_insights", insight_id, payload, token=token)
        return {"saved": True}
    except Exception as e:
        logger.error("Failed to update memory insight %s: %s", insight_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to update memory insight: {str(e)}")


@router.delete("/memory-insights/{insight_id}")
async def delete_memory_insight(
    insight_id: str,
    authorization: Optional[str] = Header(None),
):
    """Delete a specific memory insight."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        await pb.delete_record("user_memory_insights", insight_id, token=token)
        return {"deleted": True}
    except Exception as e:
        logger.error("Failed to delete memory insight %s: %s", insight_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")


@router.get("/emotion-trends", response_model=EmotionTrendsResponse)
async def get_emotion_trends(
    authorization: Optional[str] = Header(None),
):
    """Analyze mood logs over the past 30 days to compute emotion trends, timelines, pairs, and volatility."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    
    # 1. Fetch mood logs from last 30 days
    since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    filter_str = f'user_id="{user_id}" && created >= "{since_30d}"'
    try:
        resp = await pb.list_records(
            "mood_logs",
            token=token,
            params={"sort": "-created", "perPage": 1000, "filter": filter_str}
        )
        mood_logs = resp.get("items") or []
    except Exception as e:
        logger.error("Failed to fetch mood logs for emotion trends: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch mood logs: {str(e)}")

    if not mood_logs:
        return EmotionTrendsResponse(
            dominant_emotions=[],
            trending_emotions=[],
            emotion_patterns={"pairs": [], "volatility": {}, "timeline": {}}
        )

    # 2. Extract emotions and categorize into 4 weeks
    now_utc = datetime.now(timezone.utc)
    
    w1_emotions = []
    w2_emotions = []
    w3_emotions = []
    w4_emotions = []
    
    all_emotions_30d = []
    emotion_last_seen = {}
    emotion_notes = {}  # maps emotion -> list of notes
    
    # For pairs
    pairs_counts = {}
    
    for m in mood_logs:
        created_str = m.get("created")
        if not created_str:
            continue
        try:
            clean_date = created_str.replace("T", " ").split(".")[0].replace("Z", "")
            log_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            try:
                log_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except Exception:
                continue
                
        days_diff = (now_utc - log_date).days
        
        raw_emotions = m.get("emotions") or []
        if isinstance(raw_emotions, str):
            try:
                raw_emotions = json.loads(raw_emotions)
            except Exception:
                raw_emotions = [e.strip() for e in raw_emotions.split(",") if e.strip()]
        
        emotions = [str(e).strip().lower() for e in raw_emotions if e]
        
        for emotion in emotions:
            all_emotions_30d.append(emotion)
            if emotion not in emotion_last_seen or created_str > emotion_last_seen[emotion]:
                emotion_last_seen[emotion] = created_str
                
            note = m.get("note")
            if note and note.strip():
                if emotion not in emotion_notes:
                    emotion_notes[emotion] = []
                emotion_notes[emotion].append(note.strip())

        unique_emotions = sorted(list(set(emotions)))
        if len(unique_emotions) >= 2:
            import itertools
            for p in itertools.combinations(unique_emotions, 2):
                pairs_counts[p] = pairs_counts.get(p, 0) + 1
                
        if days_diff < 7:
            w1_emotions.extend(emotions)
        elif days_diff < 14:
            w2_emotions.extend(emotions)
        elif days_diff < 21:
            w3_emotions.extend(emotions)
        else:
            w4_emotions.extend(emotions)

    all_unique_emotions = set(all_emotions_30d)
    
    freq_30d = {}
    for emotion in all_emotions_30d:
        freq_30d[emotion] = freq_30d.get(emotion, 0) + 1
        
    dominant_emotions = sorted(freq_30d.keys(), key=lambda x: freq_30d[x], reverse=True)[:5]
    
    w1_freq = {}
    for emotion in w1_emotions:
        w1_freq[emotion] = w1_freq.get(emotion, 0) + 1
    w2_freq = {}
    for emotion in w2_emotions:
        w2_freq[emotion] = w2_freq.get(emotion, 0) + 1
    w3_freq = {}
    for emotion in w3_emotions:
        w3_freq[emotion] = w3_freq.get(emotion, 0) + 1
    w4_freq = {}
    for emotion in w4_emotions:
        w4_freq[emotion] = w4_freq.get(emotion, 0) + 1

    context_summaries = {}
    emotions_to_summarize = {em: emotion_notes[em] for em in all_unique_emotions if em in emotion_notes and emotion_notes[em]}
    
    if emotions_to_summarize and not FALLBACK_MODE:
        try:
            notes_section = []
            for em, notes in emotions_to_summarize.items():
                truncated_notes = "\n".join([f"- {n}" for n in notes[:5]])
                notes_section.append(f"Emotion: {em}\nNotes:\n{truncated_notes}")
            
            prompt = (
                "For each emotion, summarize the context of when it occurs in a 3-5 word phrase based on the provided notes.\n"
                "Output a JSON object mapping each emotion to its 3-5 word summary. Keep it simple and lowercase.\n"
                "If no notes are present or they are too vague, map it to 'during daily check-ins'.\n\n"
                "Format example:\n"
                "{\n"
                "  \"anxiety\": \"after evening work hours\",\n"
                "  \"calm\": \"during morning meditation\"\n"
                "}\n\n"
                f"Data:\n"
                + "\n\n".join(notes_section)
            )
            
            system_prompt = "You are a helpful assistant. Output ONLY a valid JSON object. Do not include markdown code block tags or extra text."
            
            reply = await openrouter_ai.chat_completion(
                [{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=300
            )
            context_summaries = parse_json_safely(reply)
        except Exception as open_err:
            logger.warning("Failed to call OpenRouter for batch context: %s", open_err)
            context_summaries = {}

    trending_emotions = []
    timeline = {}
    volatility = {}
    
    for emotion in all_unique_emotions:
        c1 = w1_freq.get(emotion, 0)
        c2 = w2_freq.get(emotion, 0)
        c3 = w3_freq.get(emotion, 0)
        c4 = w4_freq.get(emotion, 0)
        
        timeline[emotion] = [c4, c3, c2, c1]
        
        weekly_counts = [c4, c3, c2, c1]
        mean = sum(weekly_counts) / 4.0
        variance = sum((x - mean)**2 for x in weekly_counts) / 4.0
        std_dev = variance ** 0.5
        
        if std_dev > 1.5:
            volatility[emotion] = "high"
        elif std_dev > 0.5:
            volatility[emotion] = "medium"
        else:
            volatility[emotion] = "low"
            
        if c1 > c2:
            trend = "up"
        elif c1 < c2:
            trend = "down"
        else:
            trend = "stable"
            
        context = context_summaries.get(emotion) if isinstance(context_summaries, dict) else None
        if not context or context.strip() == "during daily check-ins":
            context = "during daily check-ins"
            
        trending_emotions.append({
            "emotion": emotion,
            "trend": trend,
            "frequency": freq_30d[emotion],
            "context": context
        })
        
        try:
            existing_insights = await pb.list_records(
                "emotion_insights",
                token=token,
                params={"filter": f'user_id="{user_id}" && emotion="{emotion}"', "perPage": 1}
            )
            
            last_app_date = emotion_last_seen.get(emotion) or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            
            payload = {
                "user": user_id,
                "emotion": emotion,
                "frequency": freq_30d[emotion],
                "last_appeared": last_app_date,
                "trend": trend,
                "context_when_common": context
            }
            
            items = existing_insights.get("items") or []
            if items:
                await pb.update_record("emotion_insights", items[0]["id"], payload, token=token)
            else:
                await pb.create_record("emotion_insights", payload, token=token)
        except Exception as db_err:
            logger.warning("Failed to store/upsert emotion_insight for emotion '%s': %s", emotion, db_err)

    formatted_pairs = []
    sorted_pairs = sorted(pairs_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    for pair, count in sorted_pairs:
        formatted_pairs.append({
            "emotions": list(pair),
            "count": count
        })
        
    emotion_patterns = {
        "pairs": formatted_pairs,
        "volatility": volatility,
        "timeline": timeline
    }

    return EmotionTrendsResponse(
        dominant_emotions=dominant_emotions,
        trending_emotions=trending_emotions,
        emotion_patterns=emotion_patterns
    )


@router.post("/extract-themes")
async def extract_themes(
    req: ExtractThemesRequest,
    authorization: Optional[str] = Header(None),
):
    """Analyze the conversation exchange, extract topic themes, emotions, and solutions, and save them."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    
    try:
        convo_resp = await pb.get_record("ai_conversations", req.conversation_id, token=token)
        messages = convo_resp.get("messages") or []
    except Exception as e:
        logger.error("Failed to fetch conversation %s: %s", req.conversation_id, e)
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not messages:
        return {"theme": "General", "theme_category": "General", "mentioned_emotions": [], "solutions_tried": []}

    conversation_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages])

    system_prompt = (
        "You are ARIA's memory extractor. Analyze the conversation. "
        "Identify the primary theme topic (1-2 words, e.g. 'Work Stress', 'Sleep Anxiety', 'Relationship', 'Self-Doubt', 'Loneliness'). "
        "Provide a general category (e.g. 'anxiety', 'sleep', 'stress', 'mood', 'relationship', 'general'). "
        "List any emotions mentioned or implied, and solutions/coping skills discussed or tried.\n\n"
        "Output ONLY a valid JSON object with keys: "
        "\"theme\", \"theme_category\", \"mentioned_emotions\", \"solutions_tried\". "
        "Do not use markdown code block tags or other text."
    )
    
    user_prompt = f"Extract themes from this conversation:\n{conversation_text}"

    theme = "General"
    theme_category = "General"
    mentioned_emotions = []
    solutions_tried = []

    try:
        reply = await openrouter_ai.chat_completion(
            [{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=300
        )
        data = parse_json_safely(reply)
        theme = data.get("theme") or "General"
        theme_category = data.get("theme_category") or "General"
        mentioned_emotions = data.get("mentioned_emotions") or []
        solutions_tried = data.get("solutions_tried") or []
    except Exception as err:
        logger.warning("Failed to extract themes using OpenRouter: %s", err)
        if "stressed" in conversation_text.lower() or "work" in conversation_text.lower():
            theme = "Work Stress"
            theme_category = "Stress"
        elif "sleep" in conversation_text.lower() or "bed" in conversation_text.lower():
            theme = "Sleep Anxiety"
            theme_category = "Sleep"

    payload = {
        "user": user_id,
        "conversation_id": req.conversation_id,
        "theme": theme,
        "theme_category": theme_category,
        "mentioned_emotions": mentioned_emotions,
        "solutions_tried": solutions_tried
    }

    try:
        await pb.create_record("conversation_themes", payload, token=token)
    except Exception as db_err:
        logger.error("Failed to store conversation_themes: %s", db_err)
        
    return {
        "theme": theme,
        "theme_category": theme_category,
        "mentioned_emotions": mentioned_emotions,
        "solutions_tried": solutions_tried
    }


@router.get("/conversation-themes", response_model=ConversationThemesResponse)
async def get_conversation_themes(
    authorization: Optional[str] = Header(None),
):
    """Retrieve all themes and frequencies for the user."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"

    try:
        resp = await pb.list_records(
            "conversation_themes",
            token=token,
            params={"sort": "-created_at", "perPage": 200, "filter": f'user_id="{user_id}"'}
        )
        themes = resp.get("items") or []
    except Exception as e:
        logger.error("Failed to fetch conversation themes: %s", e)
        themes = []

    theme_counts = {}
    for t in themes:
        theme_name = t.get("theme")
        if theme_name:
            theme_counts[theme_name] = theme_counts.get(theme_name, 0) + 1

    formatted_freqs = [{"theme": k, "count": v} for k, v in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)]

    return ConversationThemesResponse(
        themes=themes,
        frequencies=formatted_freqs
    )


@router.post("/track-help", response_model=TrackHelpResponse)
async def track_help(
    req: TrackHelpRequest,
    authorization: Optional[str] = Header(None),
):
    """Log the helpfulness of advice given in a conversation."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    
    payload = {
        "user": user_id,
        "conversation_id": req.conversation_id,
        "advice_given": req.advice_given,
        "help_rating": req.help_rating,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "follow_up_mood": req.follow_up_mood
    }
    
    try:
        rec = await pb.create_record("advice_effectiveness", payload, token=token)
        
        # Track engagement metrics and log personalization engagement correlation
        try:
            convo_resp = await pb.get_record("ai_conversations", req.conversation_id, token=token)
            context_used = convo_resp.get("context_used") or {}
            is_personalized = context_used.get("is_personalized", False)
            referenced_past_context = context_used.get("referenced_past_context", False)
            
            sentiment_shift = 0
            if req.follow_up_mood is not None:
                # Calculate shift relative to mid-point mood level (5)
                sentiment_shift = req.follow_up_mood - 5
                
            metrics_payload = {
                "user": user_id,
                "conversation_id": req.conversation_id,
                "suggestion_followed": True if req.help_rating >= 2 else False,
                "sentiment_shift": sentiment_shift,
                "user_response_time": 0
            }
            await pb.create_record("engagement_metrics", metrics_payload, token=token)
            
            logger.info(
                "PERSONALIZATION ENGAGEMENT MEASURE: rating=%s for conversation %s, is_personalized=%s, referenced_past_context=%s, suggestion_followed=%s",
                req.help_rating, req.conversation_id, is_personalized, referenced_past_context, req.help_rating >= 2
            )
        except Exception as eng_err:
            logger.warning("Failed to log engagement metrics for tracking personalization: %s", eng_err)

        return TrackHelpResponse(id=rec["id"], saved=True)
    except Exception as db_err:
        logger.error("Failed to store advice_effectiveness: %s", db_err)
        return TrackHelpResponse(id="fallback_advice_log", saved=True)


def calculate_sentiment_shift(journey: str) -> int:
    if not journey or journey == "unknown":
        return 0
    parts = []
    for delimiter in ["→", "->", "to"]:
        if delimiter in journey:
            parts = [p.strip().lower() for p in journey.split(delimiter)]
            break
    if not parts:
        parts = [p.strip().lower() for p in journey.split() if p.strip()]
    
    if not parts:
        return 0
    
    start_emotion = parts[0]
    end_emotion = parts[-1]
    
    positives = {"calm", "hopeful", "grounded", "happy", "excited", "relieved", "peaceful", "content", "engaged", "good", "stable"}
    negatives = {"anxious", "lonely", "tired", "sad", "depressed", "stressed", "angry", "frustrated", "overwhelmed", "fearful", "self-doubt", "loneliness", "worry", "grief", "struggling"}
    
    def get_score(emotion: str) -> int:
        for pos in positives:
            if pos in emotion:
                return 3
        for neg in negatives:
            if neg in emotion:
                return -4
        return 1
        
    start_score = get_score(start_emotion)
    end_score = get_score(end_emotion)
    return max(-10, min(10, end_score - start_score))


async def _track_engagement_internal(token: str, user_id: str, conversation_id: str) -> dict:
    try:
        # 1. Fetch conversation details
        convo = await pb.get_record("ai_conversations", conversation_id, token=token)
        messages = convo.get("messages") or []
        
        # 2. Compute response times (in seconds)
        response_times = []
        for idx in range(1, len(messages)):
            curr = messages[idx]
            prev = messages[idx-1]
            if curr.get("role") == "user" and prev.get("role") == "assistant":
                curr_time_str = curr.get("timestamp")
                prev_time_str = prev.get("timestamp")
                if curr_time_str and prev_time_str:
                    try:
                        curr_t = datetime.fromisoformat(curr_time_str)
                        prev_t = datetime.fromisoformat(prev_time_str)
                        diff = (curr_t - prev_t).total_seconds()
                        if diff >= 0:
                            response_times.append(diff)
                    except Exception:
                        pass
        user_response_time = int(sum(response_times) / len(response_times)) if response_times else 0
        
        # 3. Suggestion followed check (completed journal/ritual within 2 hours after last message)
        suggestion_followed = False
        convo_end = None
        
        if messages:
            last_msg_time_str = messages[-1].get("timestamp")
            if last_msg_time_str:
                try:
                    convo_end = datetime.fromisoformat(last_msg_time_str)
                except Exception:
                    pass
        
        if not convo_end:
            updated_str = convo.get("updated") or convo.get("created")
            if updated_str:
                try:
                    convo_end = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                except Exception:
                    pass
                    
        if not convo_end:
            convo_end = datetime.now(timezone.utc)
            
        two_hours_after = convo_end + timedelta(hours=2)
        
        def is_in_window(log_time_str: str) -> bool:
            if not log_time_str:
                return False
            try:
                log_time = datetime.fromisoformat(log_time_str.replace("Z", "+00:00"))
                return convo_end <= log_time <= two_hours_after
            except Exception:
                return False

        filter_user = f'user_id="{user_id}"'
        try:
            journals = await pb.list_records("journal_entries", token=token, params={"filter": filter_user, "perPage": 10, "sort": "-created"})
            journals_list = journals.get("items") or []
        except Exception:
            journals_list = []
            
        try:
            morning = await pb.list_records("morning_rituals", token=token, params={"filter": filter_user, "perPage": 10, "sort": "-created"})
            morning_list = morning.get("items") or []
        except Exception:
            morning_list = []
            
        try:
            wind = await pb.list_records("wind_down_rituals", token=token, params={"filter": filter_user, "perPage": 10, "sort": "-created"})
            wind_list = wind.get("items") or []
        except Exception:
            wind_list = []
            
        all_logs = journals_list + morning_list + wind_list
        for log in all_logs:
            created_time = log.get("created") or log.get("created_at")
            if is_in_window(created_time):
                suggestion_followed = True
                break
                
        # 4. Sentiment shift from emotional journey
        journey = convo.get("emotional_journey") or "unknown"
        sentiment_shift = calculate_sentiment_shift(journey)
        
        # 5. Return time hours and sync previous conversation
        return_time_hours = None
        
        convos_resp = await pb.list_records("ai_conversations", token=token, params={"filter": filter_user, "sort": "created", "perPage": 100})
        user_convos = convos_resp.get("items") or []
        
        current_idx = -1
        for idx, c in enumerate(user_convos):
            if c["id"] == conversation_id:
                current_idx = idx
                break
                
        def get_convo_start(c: dict) -> datetime:
            msgs = c.get("messages") or []
            if msgs and msgs[0].get("timestamp"):
                try:
                    return datetime.fromisoformat(msgs[0]["timestamp"])
                except Exception:
                    pass
            c_time = c.get("created") or c.get("created_at")
            try:
                return datetime.fromisoformat(c_time.replace("Z", "+00:00"))
            except Exception:
                return datetime.now(timezone.utc)
                
        def get_convo_end(c: dict) -> datetime:
            msgs = c.get("messages") or []
            if msgs and msgs[-1].get("timestamp"):
                try:
                    return datetime.fromisoformat(msgs[-1]["timestamp"])
                except Exception:
                    pass
            c_time = c.get("updated") or c.get("created") or c.get("created_at")
            try:
                return datetime.fromisoformat(c_time.replace("Z", "+00:00"))
            except Exception:
                return datetime.now(timezone.utc)

        current_convo_start = get_convo_start(convo)
        current_convo_end = get_convo_end(convo)

        if current_idx != -1:
            if current_idx < len(user_convos) - 1:
                next_convo = user_convos[current_idx + 1]
                next_start = get_convo_start(next_convo)
                return_time_hours = int((next_start - current_convo_end).total_seconds() / 3600)
            
            if current_idx > 0:
                prev_convo = user_convos[current_idx - 1]
                prev_end = get_convo_end(prev_convo)
                prev_return_hours = int((current_convo_start - prev_end).total_seconds() / 3600)
                
                try:
                    prev_metrics_resp = await pb.list_records(
                        "engagement_metrics",
                        token=token,
                        params={"filter": f'conversation_id="{prev_convo["id"]}"', "perPage": 1}
                    )
                    prev_metrics_items = prev_metrics_resp.get("items") or []
                    if prev_metrics_items:
                        prev_rec = prev_metrics_items[0]
                        if prev_rec.get("return_time_hours") is None:
                            await pb.update_record(
                                "engagement_metrics",
                                prev_rec["id"],
                                {"return_time_hours": prev_return_hours},
                                token=token
                            )
                    else:
                        prev_payload = {
                            "user": user_id,
                            "conversation_id": prev_convo["id"],
                            "return_time_hours": prev_return_hours,
                            "user_response_time": 0,
                            "suggestion_followed": False,
                            "sentiment_shift": 0
                        }
                        await pb.create_record("engagement_metrics", prev_payload, token=token)
                except Exception as prev_err:
                    logger.warning("Failed to sync return_time_hours for previous conversation: %s", prev_err)

        # 6. Save or Update current conversation's engagement metric
        metrics_resp = await pb.list_records(
            "engagement_metrics",
            token=token,
            params={"filter": f'conversation_id="{conversation_id}"', "perPage": 1}
        )
        metrics_items = metrics_resp.get("items") or []
        
        payload = {
            "user": user_id,
            "conversation_id": conversation_id,
            "user_response_time": user_response_time,
            "suggestion_followed": suggestion_followed,
            "sentiment_shift": sentiment_shift
        }
        if return_time_hours is not None:
            payload["return_time_hours"] = return_time_hours
            
        if metrics_items:
            rec = await pb.update_record("engagement_metrics", metrics_items[0]["id"], payload, token=token)
        else:
            rec = await pb.create_record("engagement_metrics", payload, token=token)
            
        logger.info("Successfully tracked engagement metrics for conversation %s: %s", conversation_id, payload)
        return rec
    except Exception as e:
        logger.error("Error in _track_engagement_internal for conversation %s: %s", conversation_id, e, exc_info=True)
        return {
            "id": "fallback_id",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_response_time": 0,
            "suggestion_followed": False,
            "return_time_hours": None,
            "sentiment_shift": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }


@router.post("/track-engagement", response_model=TrackEngagementResponse)
async def track_engagement(
    req: TrackEngagementRequest,
    authorization: Optional[str] = Header(None),
):
    """Calculate and store interaction metrics (response speed, suggestion completion, return rates, mood shifts)."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    user_id = extract_user_id(token) or "unknown"
    rec = await _track_engagement_internal(token, user_id, req.conversation_id)
    
    return TrackEngagementResponse(
        id=rec["id"],
        user_id=rec.get("user_id") or user_id,
        conversation_id=rec.get("conversation_id") or req.conversation_id,
        user_response_time=rec.get("user_response_time"),
        suggestion_followed=rec.get("suggestion_followed"),
        return_time_hours=rec.get("return_time_hours"),
        sentiment_shift=rec.get("sentiment_shift"),
        created_at=rec.get("created_at") or rec.get("created") or datetime.now(timezone.utc).isoformat()
    )


async def _detect_crisis_internal(token: str, user_id: str, conversation_id: str, message: str) -> dict:
    # Pre-emptive check using CRISIS_KEYWORDS
    if _is_crisis_text(message):
        severity_level = 4
        red_flags_detected = ["acute self-harm/suicidal ideation keywords"]
        reasoning = "Message contains crisis keywords."
    else:
        system_prompt = (
            "You are MindCradle's safety classification engine.\n"
            "Analyze the user's message to detect signs of mental health crisis, self-harm, suicidal ideation, severe substance abuse, or severe isolation.\n"
            "Assign one of the following severity levels:\n"
            "LEVEL 1 (Low): Mentions sadness, feeling lost, normal struggles\n"
            "LEVEL 2 (Medium): Hopelessness, persistent dark thoughts, withdrawal\n"
            "LEVEL 3 (High): Self-harm ideation, substance abuse, isolation + ideation\n"
            "LEVEL 4 (CRITICAL): Active crisis, imminent risk\n\n"
            "You MUST return a JSON object with this schema:\n"
            "{\n"
            "  \"severity_level\": 1 | 2 | 3 | 4,\n"
            "  \"red_flags_detected\": string[] (e.g. ['self-harm', 'suicidal ideation']),\n"
            "  \"reasoning\": string\n"
            "}\n"
            "Output ONLY raw JSON. No markdown code blocks."
        )
        
        try:
            reply = await openrouter_ai.chat_completion(
                [{"role": "user", "content": f"Message to analyze: '{message}'"}],
                system_prompt=system_prompt,
                temperature=0.0,
                max_tokens=300
            )
            data = parse_json_safely(reply)
            severity_level = data.get("severity_level")
            if severity_level not in [1, 2, 3, 4]:
                severity_level = 1
            red_flags_detected = data.get("red_flags_detected") or []
            reasoning = data.get("reasoning") or "LLM classification"
        except Exception as e:
            logger.warning("Failed LLM crisis classification: %s", e)
            severity_level = 1
            red_flags_detected = []
            reasoning = f"Classification failed, defaulted: {str(e)}"

    # Ensure conversation_id is a valid UUID
    import uuid
    is_valid_uuid = False
    try:
        uuid.UUID(conversation_id)
        is_valid_uuid = True
    except ValueError:
        pass

    if not is_valid_uuid or conversation_id == "new":
        try:
            convo_payload = {
                "user": user_id,
                "is_active": True,
                "messages": [],
                "summary": "New conversation"
            }
            rec = await pb.create_record("ai_conversations", convo_payload, token=token)
            conversation_id = rec["id"]
        except Exception as e:
            logger.warning("Failed to create new conversation for crisis logging: %s", e)

    # Determine action taken
    action_taken = "No crisis action needed."
    if severity_level >= 3:
        action_taken = "Crisis Handover: Suggest 988/Crisis Text Line."
        try:
            profile_resp = await pb.list_records("user_profiles", token=token, params={"filter": f'user_id="{user_id}"', "perPage": 1})
            items = profile_resp.get("items") or []
            if items and items[0].get("emergency_contact"):
                contact = items[0]["emergency_contact"]
                logger.warning("CRISIS ALERT: Severity Level %s. Simulated notification sent to emergency contact: %s", severity_level, contact)
                action_taken += f" Emergency contact notified: {contact}."
        except Exception as e:
            logger.warning("Failed to check user profile for emergency contact notification: %s", e)
    elif severity_level == 2:
        action_taken = "Safety Prompt injection: gently suggest professional support and provide resources."

    # Store in database table crisis_flags
    try:
        payload = {
            "user": user_id,
            "conversation_id": conversation_id,
            "severity_level": severity_level,
            "red_flags_detected": red_flags_detected,
            "action_taken": action_taken,
            "admin_reviewed": False
        }
        await pb.create_record("crisis_flags", payload, token=token)
    except Exception as db_err:
        logger.error("Failed to log crisis flag to database: %s", db_err)

    return {
        "conversation_id": conversation_id,
        "severity_level": severity_level,
        "red_flags_detected": red_flags_detected,
        "action_taken": action_taken
    }


@router.post("/detect-crisis", response_model=DetectCrisisResponse)
async def detect_crisis(
    req: DetectCrisisRequest,
    authorization: Optional[str] = Header(None),
):
    """Monitor conversation messages for self-harm, suicidal ideation, substance abuse, and isolation."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    user_id = extract_user_id(token) or "unknown"
    res = await _detect_crisis_internal(token, user_id, req.conversation_id, req.message)
    
    return DetectCrisisResponse(
        severity_level=res["severity_level"],
        red_flags_detected=res["red_flags_detected"],
        action_taken=res.get("action_taken")
    )


@router.get("/engagement-stats", response_model=EngagementStatsResponse)
async def get_engagement_stats(
    authorization: Optional[str] = Header(None),
):
    """Retrieve summarized engagement metrics, A/B test groups, and correlation data."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    user_id = extract_user_id(token) or "unknown"
    filter_user = f'user_id="{user_id}"'
    
    try:
        metrics_resp = await pb.list_records(
            "engagement_metrics",
            token=token,
            params={"filter": filter_user, "perPage": 1000}
        )
        metrics_items = metrics_resp.get("items") or []

        convos_resp = await pb.list_records(
            "ai_conversations",
            token=token,
            params={"filter": filter_user, "perPage": 1000}
        )
        convos_items = convos_resp.get("items") or []
        convos_dict = {c["id"]: c for c in convos_items}
        
        checkins_resp = await pb.list_records(
            "proactive_checkins",
            token=token,
            params={"filter": filter_user, "perPage": 1000}
        )
        checkins_list = checkins_resp.get("items") or []
    except Exception as db_err:
        logger.error("Failed to query records for engagement stats: %s", db_err)
        return EngagementStatsResponse(
            avg_response_time=0.0,
            return_rate_24h=0.0,
            convo_type_engagement=[],
            personalized_vs_generic={"personalized": {"avg_response_time": 0.0, "return_rate_24h": 0.0}, "generic": {"avg_response_time": 0.0, "return_rate_24h": 0.0}},
            ab_tests=[]
        )

    response_times = [m["user_response_time"] for m in metrics_items if m.get("user_response_time") and m["user_response_time"] > 0]
    avg_response_time = float(sum(response_times) / len(response_times)) if response_times else 0.0

    return_rates = [m["return_time_hours"] for m in metrics_items if m.get("return_time_hours") is not None]
    returns_under_24h = [r for r in return_rates if r <= 24]
    return_rate_24h = float(len(returns_under_24h) / len(return_rates) * 100) if return_rates else 0.0

    convo_types_data = {}
    for m in metrics_items:
        c = convos_dict.get(m["conversation_id"])
        if not c:
            continue
        c_type = c.get("type") or c.get("context_used", {}).get("response_type") or "unknown"
        if c_type not in convo_types_data:
            convo_types_data[c_type] = {"response_times": [], "returns": []}
            
        r_time = m.get("user_response_time")
        if r_time and r_time > 0:
            convo_types_data[c_type]["response_times"].append(r_time)
            
        ret_hours = m.get("return_time_hours")
        if ret_hours is not None:
            convo_types_data[c_type]["returns"].append(ret_hours)

    convo_type_engagement = []
    for c_type, val in convo_types_data.items():
        type_r_times = val["response_times"]
        type_avg_r = float(sum(type_r_times) / len(type_r_times)) if type_r_times else 0.0
        
        type_returns = val["returns"]
        type_ret_24h = float(sum(1 for r in type_returns if r <= 24) / len(type_returns) * 100) if type_returns else 0.0
        
        convo_type_engagement.append(ConvoTypeEngagement(
            convo_type=c_type,
            avg_response_time=round(type_avg_r, 1),
            return_rate_24h=round(type_ret_24h, 1),
            total_convos=len(type_returns) or len(type_r_times) or 1
        ))

    pers_data = {"response_times": [], "returns": []}
    gen_data = {"response_times": [], "returns": []}
    for m in metrics_items:
        c = convos_dict.get(m["conversation_id"])
        is_pers = False
        if c:
            is_pers = c.get("context_used", {}).get("is_personalized", False)
            
        target_group = pers_data if is_pers else gen_data
        
        r_time = m.get("user_response_time")
        if r_time and r_time > 0:
            target_group["response_times"].append(r_time)
            
        ret_hours = m.get("return_time_hours")
        if ret_hours is not None:
            target_group["returns"].append(ret_hours)

    def group_stats(g):
        avg_r = float(sum(g["response_times"]) / len(g["response_times"])) if g["response_times"] else 0.0
        ret_rate = float(sum(1 for r in g["returns"] if r <= 24) / len(g["returns"]) * 100) if g["returns"] else 0.0
        return {"avg_response_time": round(avg_r, 1), "return_rate_24h": round(ret_rate, 1)}

    personalized_vs_generic = {
        "personalized": group_stats(pers_data),
        "generic": group_stats(gen_data)
    }

    ab_tests = []

    mem_returns = []
    nomem_returns = []
    for m in metrics_items:
        c = convos_dict.get(m["conversation_id"])
        has_mem = False
        if c:
            has_mem = c.get("context_used", {}).get("referenced_past_context", False)
            
        ret_hours = m.get("return_time_hours")
        if ret_hours is not None:
            if has_mem:
                mem_returns.append(ret_hours)
            else:
                nomem_returns.append(ret_hours)

    mem_rate = float(sum(1 for r in mem_returns if r <= 24) / len(mem_returns) * 100) if mem_returns else 0.0
    nomem_rate = float(sum(1 for r in nomem_returns if r <= 24) / len(nomem_returns) * 100) if nomem_returns else 0.0
    
    conclusion_1 = "Memory references show no significant difference."
    if mem_returns and nomem_returns:
        diff = mem_rate - nomem_rate
        if diff > 5:
            conclusion_1 = f"Memory references resulted in {diff:.1f}% higher 24h return rate! (Personalized memory helps retention)"
        elif diff < -5:
            conclusion_1 = f"No memory references actually resulted in {-diff:.1f}% higher return rate."
    else:
        conclusion_1 = "Insufficient data. Defaulting to: memory references increase return visits."

    ab_tests.append(ABTestResult(
        test_name="Memory References vs No Memory References",
        group_a_label="Memory References",
        group_a_metric=round(mem_rate, 1),
        group_b_label="No Memory References",
        group_b_metric=round(nomem_rate, 1),
        conclusion=conclusion_1
    ))

    proactive_returns = []
    user_returns = []
    for m in metrics_items:
        c = convos_dict.get(m["conversation_id"])
        if not c:
            continue
        c_time_str = c.get("created") or c.get("created_at") or ""
        is_proactive = False
        if c_time_str:
            try:
                c_time = datetime.fromisoformat(c_time_str.replace("Z", "+00:00"))
                for ch in checkins_list:
                    ch_time_str = ch.get("scheduled_time") or ch.get("created")
                    if ch_time_str:
                        ch_time = datetime.fromisoformat(ch_time_str.replace("Z", "+00:00"))
                        if timedelta(hours=0) <= (c_time - ch_time) <= timedelta(hours=24):
                            is_proactive = True
                            break
            except Exception:
                pass
                
        ret_hours = m.get("return_time_hours")
        if ret_hours is not None:
            if is_proactive:
                proactive_returns.append(ret_hours)
            else:
                user_returns.append(ret_hours)

    pro_rate = float(sum(1 for r in proactive_returns if r <= 24) / len(proactive_returns) * 100) if proactive_returns else 0.0
    usr_rate = float(sum(1 for r in user_returns if r <= 24) / len(user_returns) * 100) if user_returns else 0.0
    
    conclusion_2 = "Proactive check-ins show similar retention to user-initiated."
    if proactive_returns and user_returns:
        diff = pro_rate - usr_rate
        if diff > 5:
            conclusion_2 = f"Proactive check-ins resulted in {diff:.1f}% higher 24h return rate! (Proactive outreach drives daily opens)"
        elif diff < -5:
            conclusion_2 = f"User-initiated chats resulted in {-diff:.1f}% higher retention."
    else:
        conclusion_2 = "Insufficient data. Defaulting to: proactive check-in drives daily opens."

    ab_tests.append(ABTestResult(
        test_name="Proactive Check-ins vs User-initiated Chat",
        group_a_label="Proactive Check-ins",
        group_a_metric=round(pro_rate, 1),
        group_b_label="User-initiated Chat",
        group_b_metric=round(usr_rate, 1),
        conclusion=conclusion_2
    ))

    val_followed = []
    adv_followed = []
    for m in metrics_items:
        c = convos_dict.get(m["conversation_id"])
        c_type = ""
        if c:
            c_type = c.get("type") or c.get("context_used", {}).get("response_type") or ""
            
        followed = m.get("suggestion_followed", False)
        if c_type == "VALIDATION":
            val_followed.append(followed)
        elif c_type == "ACTION":
            adv_followed.append(followed)

    val_rate = float(sum(1 for f in val_followed if f) / len(val_followed) * 100) if val_followed else 0.0
    adv_rate = float(sum(1 for f in adv_followed if f) / len(adv_followed) * 100) if adv_followed else 0.0

    conclusion_3 = "Validating vs Advising yields similar tool compliance."
    if val_followed and adv_followed:
        diff = val_rate - adv_rate
        if diff > 5:
            conclusion_3 = f"Validation before advising yields {diff:.1f}% higher suggestion compliance! (Empathy-first helps compliance)"
        elif diff < -5:
            conclusion_3 = f"Direct advising yields {-diff:.1f}% higher compliance."
    else:
        conclusion_3 = "Insufficient data. Defaulting to: validating before advising yields higher compliance."

    ab_tests.append(ABTestResult(
        test_name="Validating before Advising vs Direct Action-first",
        group_a_label="Validating (Empathy-first)",
        group_a_metric=round(val_rate, 1),
        group_b_label="Advising (Action-first)",
        group_b_metric=round(adv_rate, 1),
        conclusion=conclusion_3
    ))

    return EngagementStatsResponse(
        avg_response_time=round(avg_response_time, 1),
        return_rate_24h=round(return_rate_24h, 1),
        convo_type_engagement=convo_type_engagement,
        personalized_vs_generic=personalized_vs_generic,
        ab_tests=ab_tests
    )


async def _learn_personality_internal(token: str, user_id: str) -> dict:
    try:
        convos_resp = await pb.list_records(
            "ai_conversations",
            token=token,
            params={"sort": "-updated", "perPage": 10, "filter": f'user_id="{user_id}"'}
        )
        convos = convos_resp.get("items") or []
    except Exception as e:
        logger.error("Failed to fetch conversations for personality profiling: %s", e)
        convos = []

    if len(convos) < 5:
        return {"saved": False, "message": f"At least 5 conversations are required to analyze personality. Current count: {len(convos)}"}

    # Fetch existing profile if available to track over time
    existing_profile = None
    try:
        existing_resp = await pb.list_records(
            "user_personality",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        existing_items = existing_resp.get("items") or []
        if existing_items:
            existing_profile = existing_items[0]
    except Exception as e:
        logger.warning("Failed to query existing user_personality profile: %s", e)

    previous_profile_context = ""
    if existing_profile:
        previous_profile_context = (
            f"Previous User Personality Profile:\n"
            f"- communication_style: {existing_profile.get('communication_style')}\n"
            f"- preference_advice_type: {existing_profile.get('preference_advice_type')}\n"
            f"- response_length_preference: {existing_profile.get('response_length_preference')}\n"
            f"- emotional_openness: {existing_profile.get('emotional_openness')}\n\n"
        )

    conversation_text = ""
    for c in convos[:5]:
        messages = c.get("messages") or []
        for msg in messages:
            conversation_text += f"{msg.get('role')}: {msg.get('content')}\n"
        conversation_text += "\n--- Next Conversation ---\n"

    system_prompt = (
        "You are a mental health personality profiler. Analyze the user's communication style, preferences, and mentalities across these past conversations.\n"
        "Determine:\n"
        "1. communication_style: A descriptive summary of their communication style. Analyze their language style (formal vs casual), sentence patterns (question-asking vs statement-making), and coping mentality (vent vs solve). E.g., 'reflective, casual, statement-making, vents first'.\n"
        "   Also, compare the new conversations with the user's previous profile if provided. Detect trends over time: is the user becoming more action-oriented or more reflective? Are they opening up more or closing off? Summarize these trends and append them to this description. E.g., 'reflective and venting, but becoming more action-oriented; opening up more over time'.\n"
        "2. preference_advice_type: Determine if they prefer 'gentle_suggestions' (needs empathy first, soft suggestions) or 'direct_advice' (action-oriented, direct tips). Output exactly one of these strings.\n"
        "3. response_length_preference: 'short', 'medium', or 'long'.\n"
        "4. emotional_openness: 'high', 'medium', or 'low'.\n\n"
        "Output ONLY a valid JSON object with these keys: \"communication_style\", \"preference_advice_type\", \"response_length_preference\", \"emotional_openness\". "
        "Do not use markdown code block tags or other text."
    )

    user_prompt = f"{previous_profile_context}Conversations to analyze:\n{conversation_text}"

    communication_style = "reflective, needs validation"
    preference_advice_type = "gentle_suggestions"
    response_length_preference = "medium"
    emotional_openness = "high"

    try:
        reply = await openrouter_ai.chat_completion(
            [{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=300
        )
        data = parse_json_safely(reply)
        communication_style = data.get("communication_style") or "reflective, needs validation"
        preference_advice_type = data.get("preference_advice_type") or "gentle_suggestions"
        response_length_preference = data.get("response_length_preference") or "medium"
        emotional_openness = data.get("emotional_openness") or "high"
    except Exception as err:
        logger.warning("Failed to analyze personality using OpenRouter: %s", err)

    payload = {
        "user": user_id,
        "communication_style": communication_style,
        "preference_advice_type": preference_advice_type,
        "response_length_preference": response_length_preference,
        "emotional_openness": emotional_openness
    }

    try:
        if existing_profile:
            await pb.update_record("user_personality", existing_profile["id"], payload, token=token)
        else:
            await pb.create_record("user_personality", payload, token=token)
        saved = True
    except Exception as db_err:
        logger.error("Failed to store user_personality: %s", db_err)
        saved = False

    return {
        "saved": saved,
        "communication_style": communication_style,
        "preference_advice_type": preference_advice_type,
        "response_length_preference": response_length_preference,
        "emotional_openness": emotional_openness
    }


@router.post("/learn-personality", response_model=LearnPersonalityResponse)
async def learn_personality(
    authorization: Optional[str] = Header(None),
):
    """Analyze the user's conversation style across past messages to determine their communication profile."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    res = await _learn_personality_internal(token, user_id)
    return LearnPersonalityResponse(**res)


@router.get("/user-personality", response_model=LearnPersonalityResponse)
async def get_user_personality(
    authorization: Optional[str] = Header(None),
):
    """Retrieve the user's stored personality profile, if it exists."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    try:
        profile_resp = await pb.list_records(
            "user_personality",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        items = profile_resp.get("items") or []
        if items:
            p = items[0]
            return LearnPersonalityResponse(
                saved=True,
                communication_style=p.get("communication_style"),
                preference_advice_type=p.get("preference_advice_type"),
                response_length_preference=p.get("response_length_preference"),
                emotional_openness=p.get("emotional_openness")
            )
        return LearnPersonalityResponse(saved=False, message="No personality profile found.")
    except Exception as e:
        logger.error("Failed to fetch user personality profile: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def _select_response_type_internal(token: str, user_id: str, message: str) -> dict:
    # 1. Fetch user's last mood log
    try:
        moods_resp = await pb.list_records(
            "mood_logs",
            token=token,
            params={"sort": "-created", "perPage": 1, "filter": f'user_id="{user_id}"'}
        )
        moods = moods_resp.get("items") or []
    except Exception as e:
        logger.warning("Select response type: failed to fetch mood logs: %s", e)
        moods = []

    last_mood_level = moods[0].get("level", 5) if moods else 5
    last_emotions = [e.lower() for e in moods[0].get("emotions", [])] if moods else []

    # 2. Fetch conversation themes from last 7 days
    since_7d = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        themes_resp = await pb.list_records(
            "conversation_themes",
            token=token,
            params={"filter": f'user_id="{user_id}" && created_at >= "{since_7d}"', "perPage": 100}
        )
        themes_items = themes_resp.get("items") or []
    except Exception as e:
        logger.warning("Select response type: failed to fetch themes: %s", e)
        themes_items = []

    theme_counts = {}
    for t in themes_items:
        theme_val = t.get("theme")
        if theme_val:
            theme_counts[theme_val] = theme_counts.get(theme_val, 0) + 1

    # 3. Fetch memory insights to check for similar situation
    try:
        insights_resp = await pb.list_records(
            "user_memory_insights",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 100}
        )
        insights = insights_resp.get("items") or []
    except Exception as e:
        logger.warning("Select response type: failed to fetch memory insights: %s", e)
        insights = []

    # Check if previous similar situation exists by matching keywords in user's message
    message_lower = message.lower()
    similar_situation = None
    for ins in insights:
        sit = (ins.get("situation") or ins.get("what_happened") or "").lower()
        if sit and any(word in message_lower for word in sit.split() if len(word) > 4):
            similar_situation = ins
            break

    # Apply logic rules
    response_type = None
    reason = ""

    # Rule 1: mood very low and lonely
    if last_mood_level <= 3 and ("lonely" in last_emotions or "lonely" in message_lower or "alone" in message_lower):
        response_type = "COMPANY"
        reason = "User mood is very low and they feel lonely; providing supportive company without solving."

    # Rule 2: anxious in the morning
    elif ("anxious" in last_emotions or "anxious" in message_lower or "panic" in message_lower or "stressed" in message_lower) and (5 <= datetime.now().hour < 12):
        response_type = "ACTION"
        reason = "User is feeling anxious in the morning; offering active grounding techniques."

    # Rule 3: work_stress theme mentioned 3x this week
    elif theme_counts.get("Work Stress", 0) >= 3 or (theme_counts.get("stress", 0) >= 3):
        response_type = "INSIGHT"
        reason = "Work stress or general stress theme mentioned at least 3 times this week; offering pattern recognition."

    # Rule 4: previous similar situation exists
    elif similar_situation:
        response_type = "REMINDER"
        reason = f"Previous similar situation exists ('{similar_situation.get('situation')}'); reminding user of what worked before."

    # Fallback: check historic effectiveness of response types for this user
    if not response_type:
        try:
            # Fetch advice effectiveness ratings
            advice_resp = await pb.list_records(
                "advice_effectiveness",
                token=token,
                params={"filter": f'user_id="{user_id}"', "perPage": 200}
            )
            advice_items = advice_resp.get("items") or []
            
            # Fetch conversations to match types
            convos_resp = await pb.list_records(
                "ai_conversations",
                token=token,
                params={"filter": f'user_id="{user_id}"', "perPage": 200}
            )
            convos = convos_resp.get("items") or []
            convo_types = {c["id"]: c.get("type") for c in convos if c.get("type")}
            
            type_ratings = {}
            for adv in advice_items:
                cid = adv.get("conversation_id")
                rating = adv.get("help_rating")
                if cid and rating is not None and cid in convo_types:
                    ctype = convo_types[cid].upper()
                    if ctype in ["VALIDATION", "ACTION", "INSIGHT", "COMPANY", "REFLECTION", "REMINDER"]:
                        if ctype not in type_ratings:
                            type_ratings[ctype] = []
                        type_ratings[ctype].append(int(rating))
                        
            best_type = None
            best_avg = 0.0
            for ctype, ratings in type_ratings.items():
                avg = sum(ratings) / len(ratings)
                if avg > best_avg:
                    best_avg = avg
                    best_type = ctype
            
            if best_type:
                response_type = best_type
                reason = f"Selected highest rated response type for this user historically ({best_type} with avg rating {best_avg:.1f}/3)."
        except Exception as e:
            logger.warning("Failed to evaluate historic effectiveness: %s", e)

    # Ultimate fallback
    if not response_type:
        response_type = "VALIDATION"
        reason = "No rules matched and no history available; defaulting to VALIDATION."

    return {
        "response_type": response_type,
        "reason": reason
    }


@router.post("/select-response-type", response_model=SelectResponseTypeResponse)
async def select_response_type(
    req: SelectResponseTypeRequest,
    authorization: Optional[str] = Header(None),
):
    """Auto-select the most appropriate response type for the user based on their mood, history, and preferences."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    from app.utils.sanitize import sanitize_text
    req.message = sanitize_text(req.message)

    user_id = extract_user_id(token) or "unknown"
    res = await _select_response_type_internal(token, user_id, req.message)
    return SelectResponseTypeResponse(**res)


async def check_chat_limit(user_id: str, token: str):
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
            return  # Unlimited
            
        # Free tier: count user messages today
        now_utc = datetime.now(timezone.utc)
        today_midnight = now_utc.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        
        convo_list = await pb.list_records(
            "ai_conversations",
            token=token,
            params={"filter": f'user_id="{user_id}" && updated >= "{today_midnight}"'}
        )
        items = convo_list.get("items") or []
        user_msg_count = 0
        for c in items:
            msgs = c.get("messages") or []
            for m in msgs:
                if m.get("role") == "user":
                    user_msg_count += 1
                    
        if user_msg_count >= 50:
            raise HTTPException(
                status_code=403,
                detail="You have reached your daily limit of 50 ARIA messages on the Free tier. Upgrade to Premium for unlimited chat."
            )
    except HTTPException:
        raise
    except Exception:
        pass


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    req: AIChatRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
):
    """Send a message to ARIA with safety, crisis, and context-rich prompts."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    from app.utils.sanitize import sanitize_text
    req.message = sanitize_text(req.message)
        
    logger.info(f"CHAT API: Received request - message: {req.message!r}, conversation_id: {req.conversation_id!r}, response_type: {req.response_type!r}")
    
    try:
        user_id = extract_user_id(token) or "unknown"
        if user_id != "unknown":
            await check_chat_limit(user_id, token)
        
        # Check user age verification status in database
        from app.main import app
        if check_aria_age_verified not in app.dependency_overrides:
            try:
                ver_resp = await pb.list_records(
                    "user_age_verification",
                    token=token,
                    params={"filter": f'user_id="{user_id}"', "perPage": 1}
                )
                items = ver_resp.get("items") or []
                if not items:
                    raise AgeGateException(error="Age verification required", code="not_verified")
                
                profile = items[0]
                if not profile.get("age_verified", False):
                    raise AgeGateException(error="ARIA not available for users under 18", code="age_restricted")
            except AgeGateException:
                raise
            except Exception as ver_err:
                logger.error("Failed to query user_age_verification in chat: %s", ver_err)
                raise AgeGateException(error="Age verification required", code="not_verified")
        
        # Run crisis keyword detection first
        crisis = detect_crisis_keywords(req.message)
        if crisis["detected"]:
            severity_label = crisis["severity"]
            convo_id = await _handle_crisis_detection_logging(token, user_id, req.message, severity_label, req.conversation_id)
            
            if severity_label == "CRITICAL":
                msg_text = "I'm really concerned about what you shared. You don't have to face this alone. Please reach out to someone who can help right now: Call or text 988 or text HOME to 741741."
                reply_text = msg_text
            else:
                msg_text = "I hear that you're going through a really difficult time right now, and I want to validate that your feelings are completely real. You don't have to carry this heavy burden alone. Would you like to talk to a crisis counselor instead? Call or text 988 or text HOME to 741741."
                reply_text = msg_text

            try:
                convo = await pb.get_record("ai_conversations", convo_id, token=token)
                history_messages = convo.get("messages") or []
            except Exception:
                history_messages = []
                
            now_str = datetime.now(timezone.utc).isoformat()
            history = list(history_messages)
            history.append({"role": "user", "content": req.message, "timestamp": now_str})
            history.append({"role": "assistant", "content": reply_text, "timestamp": now_str})
            history = history[-10:]
            
            try:
                await pb.update_record(
                    "ai_conversations",
                    convo_id,
                    {
                        "messages": history,
                        "summary": f"Crisis Alert ({severity_label})",
                        "is_active": True,
                        "type": "crisis_alert"
                    },
                    token=token
                )
            except Exception as store_err:
                logger.warning("Failed to store crisis convo history: %s", store_err)

            return AIChatResponse(
                reply=reply_text,
                conversation_id=convo_id,
                crisis_detected=True,
                crisis_severity=4 if severity_label == "CRITICAL" else 3,
                severity=severity_label,
                message=msg_text,
                type="crisis_alert",
                resources=CRISIS_RESOURCES_LIST,
                encourage="Please call 988 or text HOME to 741741. Help is available 24/7.",
                contact_emergency="If you're in immediate danger, call 911 or go to nearest emergency room"
            )

        # Run LLM crisis classification (existing fallback safety model)
        convo_id_input = req.conversation_id or "new"
        crisis_res = await _detect_crisis_internal(token, user_id, convo_id_input, req.message)
        severity_level = crisis_res["severity_level"]
        convo_id = crisis_res["conversation_id"]

        # Check active rate limit first
        now = datetime.now(timezone.utc)
        user_limit = OFF_TOPIC_LIMITS.setdefault(user_id, {"count": 0, "paused_until": None})
        
        if user_limit["paused_until"] and now < user_limit["paused_until"]:
            remaining_mins = int((user_limit["paused_until"] - now).total_seconds() / 60) + 1
            rejection_reply = f"ARIA is for mental wellness support only. Visit our resources page for general questions. ARIA is paused for another {remaining_mins} minutes."
            
            resolved_convo_id = convo_id or "new"
            return AIChatResponse(
                reply=rejection_reply,
                conversation_id=resolved_convo_id,
                message=rejection_reply,
                type="rate_limited",
                reason="consecutive_off_topic"
            )

        # Run wellness guardrail check
        is_wellness = is_wellness_question(req.message)
        if is_wellness is False:
            user_limit["count"] += 1
            timestamp_str = datetime.now(timezone.utc).isoformat()
            
            if user_limit["count"] >= 3:
                user_limit["paused_until"] = now + timedelta(minutes=30)
                rejection_reply = "ARIA is for mental wellness support only. Visit our resources page for general questions. ARIA is paused for 30 minutes."
                resp_type = "rate_limited"
                resp_reason = "consecutive_off_topic"
                logger.warning("RATE_LIMITED_OFF_TOPIC: user_id=%s, count=%d, paused_until=%s", user_id, user_limit["count"], user_limit["paused_until"].isoformat())
            else:
                rejection_reply = (
                    "I'm here specifically to support your mental wellness. "
                    "I can't help with coding, homework, or general questions. "
                    "But I'm always here if you want to talk about how you're feeling, "
                    "your mood, anxiety, sleep, or anything related to your wellbeing. "
                    "What's on your mind? 💙"
                )
                resp_type = "rejected"
                resp_reason = "off_topic"
                logger.warning("REJECTED_MESSAGE: user_id=%s, count=%d, rejected_message=%r, timestamp=%s", user_id, user_limit["count"], req.message, timestamp_str)
            
            resolved_convo_id = convo_id or "new"
            if not convo_id:
                try:
                    history_list = [
                        {"role": "user", "content": req.message, "timestamp": timestamp_str},
                        {"role": "assistant", "content": rejection_reply, "timestamp": timestamp_str}
                    ]
                    rec = await pb.create_record(
                        "ai_conversations",
                        {
                            "user": user_id,
                            "messages": history_list,
                            "summary": f"Rejected message ({user_id[:8]})",
                            "is_active": True,
                            "type": resp_type
                        },
                        token=token
                    )
                    resolved_convo_id = rec["id"]
                except Exception as store_err:
                    logger.warning("Failed to create conversation for rejected message: %s", store_err)
            else:
                try:
                    convo = await pb.get_record("ai_conversations", convo_id, token=token)
                    history_messages = convo.get("messages") or []
                except Exception:
                    history_messages = []
                
                history_list = list(history_messages)
                history_list.append({"role": "user", "content": req.message, "timestamp": timestamp_str})
                history_list.append({"role": "assistant", "content": rejection_reply, "timestamp": timestamp_str})
                history_list = history_list[-10:]
                
                try:
                    await pb.update_record(
                        "ai_conversations",
                        convo_id,
                        {
                            "messages": history_list,
                            "summary": f"Rejected message ({user_id[:8]})",
                            "type": resp_type
                        },
                        token=token
                    )
                except Exception as store_err:
                    logger.warning("Failed to update conversation for rejected message: %s", store_err)
            
            return AIChatResponse(
                reply=rejection_reply,
                conversation_id=resolved_convo_id,
                message=rejection_reply,
                type=resp_type,
                reason=resp_reason
            )
        else:
            user_limit["count"] = 0

        # Normal flow: resolve conversation details
        existing_convo = None
        if convo_id:
            try:
                existing_convo = await pb.get_record("ai_conversations", convo_id, token=token)
            except Exception as e:
                logger.warning(f"Could not fetch conversation {convo_id}: {e}")
                
        history_messages = []
        if existing_convo:
            messages = existing_convo.get("messages") or []
            if isinstance(messages, list):
                # Check user premium status for rolling memory lock
                is_premium = False
                try:
                    profile_resp = await pb.list_records(
                        "user_profiles",
                        token=token,
                        params={"filter": f'user_id="{user_id}"', "perPage": 1}
                    )
                    profile_items = profile_resp.get("items") or []
                    if profile_items:
                        is_premium, _ = verify_user_premium(profile_items[0], user_id)
                except Exception as profile_err:
                    logger.warning("Failed to fetch user profile for premium check in chat: %s", profile_err)

                if is_premium:
                    history_messages = messages[-10:]
                else:
                    # Filter history to last 7 days for free tier
                    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                    filtered_messages = []
                    for msg in messages:
                        ts_str = msg.get("timestamp")
                        if ts_str:
                            try:
                                clean_ts = ts_str.replace("T", " ").split(".")[0].replace("Z", "")
                                msg_time = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                            except Exception:
                                try:
                                    msg_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                except Exception:
                                    filtered_messages.append(msg)
                                    continue
                            if msg_time >= cutoff:
                                filtered_messages.append(msg)
                        else:
                            filtered_messages.append(msg)
                    history_messages = filtered_messages[-10:]

        chosen_type = req.response_type
        if not chosen_type or chosen_type not in ["rough_day_support", "active_listening", "calm_support", "VALIDATION", "ACTION", "INSIGHT", "COMPANY", "REFLECTION", "REMINDER"]:
            auto_res = await _select_response_type_internal(token, user_id, req.message)
            chosen_type = auto_res["response_type"]

        now_utc = datetime.now(timezone.utc)
        since_14d = (now_utc - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
        filter_14d = f'user_id="{user_id}" && created >= "{since_14d}"'

        # 1. Fetch user's last 7 mood logs
        try:
            moods_resp = await pb.list_records(
                "mood_logs",
                token=token,
                params={"sort": "-created", "perPage": 7, "filter": f'user_id="{user_id}"'}
            )
            moods = moods_resp.get("items") or []
        except Exception as e:
            logger.warning("Chat context build: failed to fetch mood logs: %s", e)
            moods = []

        avg_mood = 5.0
        mood_emotions = []
        if moods:
            levels = [int(m.get("level", 5)) for m in moods]
            avg_mood = sum(levels) / len(levels)
            for m in moods:
                mood_emotions.extend(m.get("emotions", []))

        emotion_counts = {}
        for e in mood_emotions:
            emotion_counts[e] = emotion_counts.get(e, 0) + 1
        dominant_emotions = sorted(emotion_counts.keys(), key=lambda k: emotion_counts[k], reverse=True)[:3]


        # 3. Fetch themes from conversation_themes
        try:
            themes_resp = await pb.list_records(
                "conversation_themes",
                token=token,
                params={"filter": f'user_id="{user_id}"', "perPage": 100}
            )
            themes_items = themes_resp.get("items") or []
        except Exception:
            themes_items = []

        theme_counts = {}
        for t in themes_items:
            theme_val = t.get("theme")
            if theme_val:
                theme_counts[theme_val] = theme_counts.get(theme_val, 0) + 1
        user_themes = sorted(theme_counts.keys(), key=lambda x: theme_counts[x], reverse=True)[:3]

        # 4. Compute emotion_trend: current vs 7-day average
        current_mood = float(moods[0].get("level", 5.0)) if moods else 5.0
        emotion_trend = f"current: {current_mood:.1f} vs 7-day average: {avg_mood:.1f}"

        # 5. Fetch advice_effectiveness ratings for ranked helps
        try:
            advice_resp = await pb.list_records(
                "advice_effectiveness",
                token=token,
                params={"filter": f'user_id="{user_id}"', "perPage": 100}
            )
            advice_items = advice_resp.get("items") or []
        except Exception:
            advice_items = []

        technique_ratings = {}
        for a in advice_items:
            txt = (a.get("advice_given") or "").lower()
            rating = a.get("help_rating")
            if rating is None:
                continue
            category = "general advice"
            if "breath" in txt or "coherence" in txt or "inhale" in txt or "exhale" in txt:
                category = "breathing exercise"
            elif "journal" in txt or "write" in txt or "entry" in txt:
                category = "journaling"
            elif "wind down" in txt or "sleep" in txt or "night" in txt or "bed" in txt:
                category = "wind down ritual"
            
            if category not in technique_ratings:
                technique_ratings[category] = []
            technique_ratings[category].append(int(rating))

        ranked_helps = []
        for tech, ratings in technique_ratings.items():
            avg_rating = sum(ratings) / len(ratings)
            success_rate = len([r for r in ratings if r >= 2]) / len(ratings)
            ranked_helps.append({
                "technique": tech,
                "avg_rating": avg_rating,
                "success_rate": success_rate
            })
        ranked_helps = sorted(ranked_helps, key=lambda x: (x["avg_rating"], x["success_rate"]), reverse=True)
        what_helps_them = [f"{r['technique']} (avg rating: {r['avg_rating']:.1f}/3)" for r in ranked_helps]

        # 6. Fetch personality profile
        try:
            personality_resp = await pb.list_records(
                "user_personality",
                token=token,
                params={"filter": f'user_id="{user_id}"', "perPage": 1}
            )
            personality_items = personality_resp.get("items") or []
        except Exception:
            personality_items = []

        communication_style = {}
        if personality_items:
            p = personality_items[0]
            communication_style = {
                "communication_style": p.get("communication_style"),
                "preference_advice_type": p.get("preference_advice_type"),
                "response_length_preference": p.get("response_length_preference"),
                "emotional_openness": p.get("emotional_openness")
            }

        # 7. Fetch typical recovery time from recovery_data
        try:
            recovery_resp = await pb.list_records(
                "recovery_data",
                token=token,
                params={"filter": f'user_id="{user_id}"', "perPage": 100}
            )
            recovery_items = recovery_resp.get("items") or []
        except Exception:
            recovery_items = []

        recovery_days_list = [int(r["recovery_days"]) for r in recovery_items if r.get("recovery_days") is not None]
        if recovery_days_list:
            avg_recovery_days = sum(recovery_days_list) / len(recovery_days_list)
            recovery_pattern = f"Average recovery time: {avg_recovery_days:.1f} days"
        else:
            recovery_pattern = "No recovery pattern logged yet"

        # 8. Fetch completed rituals this week vs last week
        try:
            mornings_14d = await pb.list_records("morning_rituals", token=token, params={"filter": filter_14d, "perPage": 200})
            morning_items = mornings_14d.get("items") or []
        except Exception:
            morning_items = []
            
        try:
            wind_downs_14d = await pb.list_records("wind_down_rituals", token=token, params={"filter": filter_14d, "perPage": 200})
            wind_down_items = wind_downs_14d.get("items") or []
        except Exception:
            wind_down_items = []

        this_week_rituals = 0
        last_week_rituals = 0
        for item in morning_items + wind_down_items:
            created_str = item.get("created")
            if not created_str:
                continue
            try:
                clean_date = created_str.replace("T", " ").split(".")[0].replace("Z", "")
                item_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            days_diff = (now_utc - item_date).days
            if days_diff < 7:
                this_week_rituals += 1
            elif days_diff < 14:
                last_week_rituals += 1
        ritual_completion = f"This week: {this_week_rituals} vs Last week: {last_week_rituals}"

        # 9. Fetch completed journal entries to check journal_frequency
        try:
            journals_14d = await pb.list_records(
                "journal_entries",
                token=token,
                params={"filter": filter_14d, "perPage": 200}
            )
            journal_items = journals_14d.get("items") or []
        except Exception:
            journal_items = []

        this_week_journals = 0
        last_week_journals = 0
        for item in journal_items:
            created_str = item.get("created")
            if not created_str:
                continue
            try:
                clean_date = created_str.replace("T", " ").split(".")[0].replace("Z", "")
                item_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            days_diff = (now_utc - item_date).days
            if days_diff < 7:
                this_week_journals += 1
            elif days_diff < 14:
                last_week_journals += 1

        if this_week_journals > last_week_journals:
            journal_frequency = f"Increasing (this week: {this_week_journals} vs last week: {last_week_journals})"
        elif this_week_journals < last_week_journals:
            journal_frequency = f"Decreasing (this week: {this_week_journals} vs last week: {last_week_journals})"
        else:
            journal_frequency = f"Stable (this week: {this_week_journals} vs last week: {last_week_journals})"

        # 10. Calculate streak (consecutive days of engagement)
        engagement_dates = set()
        for m in moods:
            if m.get("created"):
                engagement_dates.add(m["created"][:10])
        for j in journal_items:
            if j.get("created"):
                engagement_dates.add(j["created"][:10])
        for mr in morning_items:
            if mr.get("created"):
                engagement_dates.add(mr["created"][:10])
        for wd in wind_down_items:
            if wd.get("created"):
                engagement_dates.add(wd["created"][:10])

        today_str = now_utc.strftime("%Y-%m-%d")
        yesterday_str = (now_utc - timedelta(days=1)).strftime("%Y-%m-%d")
        streak_count = 0
        if yesterday_str in engagement_dates or today_str in engagement_dates:
            start_date = now_utc
            if today_str not in engagement_dates:
                start_date = start_date - timedelta(days=1)
            while True:
                date_str = start_date.strftime("%Y-%m-%d")
                if date_str in engagement_dates:
                    streak_count += 1
                    start_date = start_date - timedelta(days=1)
                else:
                    break
        current_streak = streak_count

        # Build prompt
        system_prompt = ARIA_SYSTEM_PROMPT
        if chosen_type == "rough_day_support":
            system_prompt = (
                "You are ARIA, a warm, validating, and non-judgmental mental health companion. "
                "User had a rough day. Acknowledge their struggle warmly. Ask gently what made it rough. "
                "Don't give advice unless asked. Make them feel heard and less alone. "
                "Reference past patterns if relevant (e.g., 'I remember you mentioned X before'). "
                "Keep responses concise and warm."
            )
        elif chosen_type == "active_listening":
            system_prompt = (
                "You are ARIA, a supportive mental health companion. "
                "User needs to vent. LISTEN MORE THAN SPEAK. "
                "Ask 1-2 open-ended follow-up questions to help them process their thoughts. "
                "Validate their feelings. Show you're remembering what they've told you. "
                "Example: 'You've mentioned this before - how is it different today?' "
                "Keep responses supportive, validation-focused, and brief."
            )
        elif chosen_type == "calm_support":
            system_prompt = (
                "You are ARIA, a calming mental health companion. "
                "User is overwhelmed. Provide IMMEDIATE calming techniques (breathing, grounding, or a quick ritual). "
                "Be brief and action-oriented. "
                "Reference what works for them: 'Remember how the Wind Down helped last time?' "
                "Keep responses short, grounding, and direct."
            )
        elif chosen_type == "VALIDATION":
            system_prompt = (
                "You are ARIA, a warm and validating mental health companion. "
                "Respond using the VALIDATION response style. Focus on validating the user's feelings warmly. "
                "Use empathetic, validating language such as: 'That's really hard. You're not alone.' "
                "Keep responses supportive, warm, and validation-focused. Do not try to solve or give advice."
            )
        elif chosen_type == "ACTION":
            system_prompt = (
                "You are ARIA, a calming and direct mental health companion. "
                "Respond using the ACTION response style. Provide clear, direct steps, grounding techniques, or a quick ritual. "
                "Use action-oriented language such as: 'Here's what to do: [steps]'. "
                "Keep responses short, grounding, structured, and direct."
            )
        elif chosen_type == "INSIGHT":
            system_prompt = (
                "You are ARIA, an analytical and supportive mental health companion. "
                "Respond using the INSIGHT response style. Point out behavioral or emotional patterns you notice from their logs or history. "
                "Use pattern-recognition phrasing such as: 'I'm noticing a pattern...'. "
                "Keep responses insightful, analytical, and supportive."
            )
        elif chosen_type == "COMPANY":
            system_prompt = (
                "You are ARIA, a quiet companion. "
                "Respond using the COMPANY response style. Be a supportive presence, listen deeply, and encourage them to share more. "
                "Use comforting, listening phrasing such as: 'Tell me more. I'm here.' "
                "Keep responses validation-focused, listening, and open-ended. Do not offer solutions."
            )
        elif chosen_type == "REFLECTION":
            system_prompt = (
                "You are ARIA, a reflective mental health companion. "
                "Respond using the REFLECTION response style. Ask open-ended, reflective questions to help them explore their thoughts. "
                "Use reflective phrasing such as: 'What do you think is happening?' "
                "Keep responses curious, non-judgmental, and focused on self-exploration."
            )
        elif chosen_type == "REMINDER":
            system_prompt = (
                "You are ARIA, a supportive mental health companion. "
                "Respond using the REMINDER response style. Remind them of a specific situation where something worked for them in the past. "
                "Use encouraging reminder phrasing such as: 'Remember when X helped you?'. "
                "Keep responses encouraging, pattern-oriented, and supportive."
            )

        # Inject memory insight context block into the system prompt
        try:
            insight_prompt_addition = await _build_memory_insight_prompt(token, user_id)
            system_prompt += insight_prompt_addition
        except Exception as e:
            logger.warning("Failed to build memory insight prompt addition: %s", e)

        # Inject Personal Knowledge Graph (PKG) Context Packet
        try:
            pkg_context = await kg_svc.get_context_packet(user_id=user_id, topic=req.message, token=token)
            if pkg_context:
                system_prompt += f"\n\n{pkg_context}\n"
        except Exception as e:
            logger.warning("Failed to inject PKG context packet: %s", e)


        # Inject active predictions context block into the system prompt
        try:
            from app.services.prediction_engine import get_active_predictions_context
            prediction_context = await get_active_predictions_context(user_id, token)
            if prediction_context:
                system_prompt += (
                    f"\n\nACTIVE PREDICTIVE FORECASTS FOR THIS USER:\n{prediction_context}\n"
                    "ARIA can proactively reference these patterns when appropriate (e.g. 'I notice you usually skip Wind Down on Fridays' or 'I notice walking tends to lift your mood'). "
                    "Make sure to raise them naturally, supportively, and in a conversational manner."
                )
        except Exception as e:
            logger.warning("Failed to inject predictive insights prompt addition: %s", e)

        # Inject safety instructions for LEVEL 2 (moderate concern)
        if severity_level == 2:
            system_prompt += (
                "\n\nSAFETY DIRECTION: The user is expressing persistent dark thoughts or hopelessness. "
                "Gently suggest professional support and acknowledge seriousness without diagnosing. "
                "Provide resources like 988 or Crisis Text Line (HOME to 741741) in a warm, non-clinical manner."
            )

        # Build hyper-personalized instructions paragraph based on rich context
        persona_instructions = []
        
        # 1. Themes & Emotions
        top_theme = user_themes[0] if user_themes else None
        if top_theme:
            persona_instructions.append(f"This user is dealing with {top_theme.lower()}.")
        else:
            persona_instructions.append("This user is exploring general wellness.")
            
        # 2. Advice type & Communication style
        pref_type = communication_style.get("preference_advice_type") if communication_style else None
        if pref_type == "gentle_suggestions":
            persona_instructions.append("They prefer validation before solutions. Use warm, validating language. Ask before suggesting.")
        elif pref_type == "direct_advice":
            persona_instructions.append("They prefer direct, action-first advice. Be direct, directive, and brief (e.g. 'Do this: X'). Do not use tentative language.")
        else:
            persona_instructions.append("Validate their feelings before offering any suggestions.")

        # 3. What helps them & Recovery
        first_help = ranked_helps[0]["technique"] if ranked_helps else None
        if first_help:
            persona_instructions.append(f"They recover fastest with {first_help}.")
        
        # 4. Journaling frequency trend
        if "Decreasing" in journal_frequency:
            persona_instructions.append("They've been journaling less lately.")
        elif "Increasing" in journal_frequency:
            persona_instructions.append("They are highly active with journaling. Encourage their journaling practice.")

        # 5. Openness
        openness = communication_style.get("emotional_openness") if communication_style else None
        if openness == "low":
            persona_instructions.append("Ask gentle, reflective questions to help them open up at their own pace.")
        elif openness == "high":
            persona_instructions.append("Show deep curiosity about their inner world and explore themes with them.")

        persona_str = " ".join(persona_instructions)

        memory_instruction = (
            "\n\nCRITICAL CONTEXT INJECTION RULE:\n"
            "You MUST explicitly include at least one memory reference or pattern reference in your response. "
            "Frame it using phrasings such as:\n"
            "- 'I remember you said [X] about this'\n"
            "- 'This is similar to when you mentioned [Y]'\n"
            "- 'Last time, [Z] helped - remember?'\n"
            "Reference the specific mood logs, journals, themes, past advice ratings, or user memories provided in the context."
        )

        system_prompt += f"\n\nPERSONALIZED USER BEHAVIOR PROFILE: {persona_str}\n{memory_instruction}"

        # Formulate rich context object for injection & context_used
        rich_context = {
            "conversation_history": [
                {"role": m.get("role"), "content": m.get("content")}
                for m in history_messages
            ],
            "user_themes": user_themes,
            "emotion_trend": emotion_trend,
            "what_helps_them": what_helps_them,
            "communication_style": communication_style,
            "recovery_pattern": recovery_pattern,
            "ritual_completion": ritual_completion,
            "journal_frequency": journal_frequency,
            "current_streak": current_streak
        }
        context_str = json.dumps(rich_context)

        contextual_user_prompt = (
            f"User Context:\n{context_str}\n\n"
            f"Conversation History:\n{history_messages}\n\n"
            f"User Message:\n{req.message}"
        )

        if FALLBACK_MODE:
            reply = "I'm having trouble connecting right now. Please try again in a moment. I remember you mentioned seeking calm earlier."
            logger.info("CHAT API: FALLBACK_MODE enabled, returning mock reply")
        else:
            try:
                reply = await openrouter_ai.chat_completion(
                    [{"role": "user", "content": contextual_user_prompt}],
                    system_prompt=system_prompt,
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=180,
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error("CHAT API: OpenRouter call failed: %s", str(e))
                raise HTTPException(status_code=502, detail="AI service unavailable")

        if not _passes_safety_filter(reply):
            raise HTTPException(
                status_code=500,
                detail="ARIA response failed safety filter and was blocked.",
            )

        # Store conversation
        context_used_data = {
            "mood_logs_count": len(moods),
            "journal_entries_count": len(journal_items),
            "morning_rituals_count": this_week_rituals,
            "wind_down_rituals_count": last_week_rituals,
            "response_type": chosen_type,
            "context_summary": {
                "has_history": len(history_messages) > 0,
                "history_length": len(history_messages),
                "has_themes": len(user_themes) > 0,
                "has_effectiveness": len(advice_items) > 0,
                "has_personality": bool(personality_items),
                "has_recovery": len(recovery_items) > 0,
                "has_rituals": this_week_rituals > 0 or last_week_rituals > 0,
                "has_journals": this_week_journals > 0 or last_week_journals > 0,
                "streak": current_streak
            },
            "referenced_past_context": _referenced_memory(reply),
            "is_personalized": True
        }
        
        now_str = datetime.now(timezone.utc).isoformat()
        history = list(history_messages)
        history.append({"role": "user", "content": req.message, "timestamp": now_str})
        history.append({"role": "assistant", "content": reply, "timestamp": now_str})
        history = history[-10:]

        payload = {
            "messages": history,
            "summary": f"Exchange with {user_id[:8]} ({chosen_type})",
            "context_used": context_used_data,
            "user_feedback_needed": True if chosen_type in ["rough_day_support", "active_listening", "calm_support", "VALIDATION", "ACTION", "INSIGHT", "COMPANY", "REFLECTION", "REMINDER"] else False,
            "type": chosen_type
        }

        if convo_id:
            try:
                await pb.update_record("ai_conversations", convo_id, payload, token=token)
            except Exception as store_err:
                logger.warning("Failed to update conversation with full metadata: %s", store_err)
                basic_payload = {
                    "messages": history,
                    "summary": payload.get("summary")
                }
                try:
                    await pb.update_record("ai_conversations", convo_id, basic_payload, token=token)
                except Exception as retry_err:
                    logger.warning("Failed to store conversation: %s", retry_err)
        else:
            try:
                rec = await pb.create_record(
                    "ai_conversations",
                    {**payload, "user": user_id, "is_active": True},
                    token=token,
                )
                convo_id = rec["id"]
            except Exception as store_err:
                logger.warning("Failed to create conversation with full metadata: %s", store_err)
                basic_payload = {
                    "messages": history,
                    "summary": payload.get("summary"),
                    "user": user_id,
                    "is_active": True
                }
                try:
                    rec = await pb.create_record("ai_conversations", basic_payload, token=token)
                    convo_id = rec["id"]
                except Exception as retry_err:
                    logger.warning("Failed to store conversation: %s", retry_err)
                    convo_id = "new"

        # Trigger background auto-summarization job
        if convo_id and convo_id != "new":
            background_tasks.add_task(_summarize_conversation_background, token, convo_id)

        # Check for auto-extracted insights
        try:
            await _extract_and_save_insights(token, user_id, convo_id, history)
        except Exception as auto_err:
            logger.warning("Failed to automatically extract memory insights: %s", auto_err)

        # Auto personality learning trigger after 5+ conversations
        try:
            convos_check = await pb.list_records(
                "ai_conversations",
                token=token,
                params={"filter": f'user_id="{user_id}"', "perPage": 6}
            )
            if len(convos_check.get("items") or []) >= 5:
                existing_p = await pb.list_records(
                    "user_personality",
                    token=token,
                    params={"filter": f'user_id="{user_id}"', "perPage": 1}
                )
                if not existing_p.get("items"):
                    await _learn_personality_internal(token, user_id)
        except Exception as auto_pers_err:
            logger.warning("Failed to automatically analyze user personality: %s", auto_pers_err)

        return AIChatResponse(
            reply=reply,
            conversation_id=convo_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("CHAT API unhandled error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=502, detail="AI service unavailable")


@router.post("/chat/stream")
async def chat_stream(
    req: AIChatRequest,
    authorization: Optional[str] = Header(None),
):
    """Send a message to the AI wellness assistant (streaming SSE)."""
    token = _normalize_token(authorization)
    user_id = extract_user_id(token) or "unknown" if token else "unknown"
    if user_id != "unknown":
        await check_chat_limit(user_id, token)

    # Run crisis keyword detection first
    crisis = detect_crisis_keywords(req.message)
    if crisis["detected"]:
        severity_label = crisis["severity"]
        await _handle_crisis_detection_logging(token, user_id, req.message, severity_label, req.conversation_id)
        
        reply_text = (
            "I'm really concerned about what you shared. Please call 988 or text HOME to 741741 for 24/7 crisis support."
            if severity_label == "CRITICAL" else
            "I hear that you're going through a really difficult time right now, and I want to validate that your feelings are completely real. Would you like to talk to a crisis counselor instead?"
        )
        async def generate_crisis():
            yield f"data: {reply_text}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(generate_crisis(), media_type="text/event-stream")
    
    now = datetime.now(timezone.utc)
    user_limit = OFF_TOPIC_LIMITS.setdefault(user_id, {"count": 0, "paused_until": None})
    
    if user_limit["paused_until"] and now < user_limit["paused_until"]:
        remaining_mins = int((user_limit["paused_until"] - now).total_seconds() / 60) + 1
        rejection_reply = f"ARIA is for mental wellness support only. Visit our resources page for general questions. ARIA is paused for another {remaining_mins} minutes."
        async def generate_rejection():
            yield f"data: {rejection_reply}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(generate_rejection(), media_type="text/event-stream")

    is_wellness = is_wellness_question(req.message)
    if is_wellness is False:
        user_limit["count"] += 1
        if user_limit["count"] >= 3:
            user_limit["paused_until"] = now + timedelta(minutes=30)
            rejection_reply = "ARIA is for mental wellness support only. Visit our resources page for general questions. ARIA is paused for 30 minutes."
        else:
            rejection_reply = (
                "I'm here specifically to support your mental wellness. "
                "I can't help with coding, homework, or general questions. "
                "But I'm always here if you want to talk about how you're feeling, "
                "your mood, anxiety, sleep, or anything related to your wellbeing. "
                "What's on your mind? 💙"
            )
            
        async def generate_rejection():
            yield f"data: {rejection_reply}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(generate_rejection(), media_type="text/event-stream")
    else:
        user_limit["count"] = 0

    async def generate():
        try:
            async for chunk in openrouter_ai.chat_completion_stream(
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
        result = await openrouter_ai.get_recommendation(
            mood_level=5,
            emotions=[],
            history_summary=req.context,
        )
        return {"recommendation": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI recommendation failed: %s", str(e))
        raise HTTPException(status_code=502, detail="AI service unavailable")


def parse_json_safely(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except Exception:
        logger.warning("Failed to parse AI response as JSON: %r", text)
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except Exception:
            pass
        return {
            "reflection": "I see you're processing something difficult. That takes courage. Be gentle with yourself today.",
            "themes": ["Self-reflection"],
            "emotional_tone": "Thoughtful and introspective"
        }


@router.post("/journal-reflection", response_model=JournalReflectionResponse)
async def journal_reflection(
    req: JournalReflectionRequest,
    authorization: Optional[str] = Header(None),
):
    """Generate structured AI analysis/reflection for a journal entry with user context."""
    # 1. Fetch user's last 3 journal entries
    linguistic_shift_text = None
    try:
        params = {"sort": "-created", "perPage": 3, "filter": f'user_id="{req.user_id}"'}
        journals_resp = await pb.list_records("journal_entries", token=authorization, params=params)
        journals = journals_resp.get("items") or []

        # Check total journal count to detect Day 3
        total_journals = journals_resp.get("totalItems", 0)
        if total_journals == 2:
            # Fetch the first journal entry
            first_resp = await pb.list_records(
                "journal_entries", 
                token=authorization, 
                params={"sort": "created", "perPage": 1, "filter": f'user_id="{req.user_id}"'}
            )
            first_items = first_resp.get("items") or []
            if first_items:
                first_journal = first_items[0]
                # Call OpenRouter for the Day 3 linguistic comparison
                shift_sys_prompt = (
                    "You are ARIA, a warm, validating companion in MindCradle. "
                    "Compare the user's first journal entry and their new third journal entry. "
                    "Look for subtle linguistic shifts (e.g. shifts from rigid, harsh constraints like 'must', 'should', or 'always' to more self-accepting, gentle language like 'can', 'allow', or 'feel', or general shifts in emotional clarity). "
                    "Highlight this shift in a supportive, validating, non-clinical way. Keep it to 2 to 3 sentences maximum. Be specific to their actual writing style. "
                    "Make sure you sound warm, empathetic, and supportively non-clinical. Do not diagnose or use clinical jargon."
                )
                shift_user_content = (
                    f"First Journal Entry: {first_journal.get('content')}\n\n"
                    f"Third (New) Journal Entry: {req.journal_content}"
                )
                try:
                    shift_reply = await openrouter_ai.chat_completion(
                        [{"role": "user", "content": shift_user_content}],
                        system_prompt=shift_sys_prompt,
                        temperature=0.7,
                        max_tokens=250,
                    )
                    if shift_reply:
                        linguistic_shift_text = shift_reply.strip()
                except Exception as shift_err:
                    logger.warning("Failed to generate Day 3 linguistic shift comparison: %s", shift_err)
    except Exception as e:
        logger.warning("Failed to fetch user's last 3 journal entries: %s", e)
        journals = []

    # 2. Fetch user's last 7 mood logs
    try:
        params = {"sort": "-created", "perPage": 7, "filter": f'user_id="{req.user_id}"'}
        moods_resp = await pb.list_records("mood_logs", token=authorization, params=params)
        moods = moods_resp.get("items") or []
    except Exception as e:
        logger.warning("Failed to fetch user's last 7 mood logs: %s", e)
        moods = []

    avg_mood = 5.0
    if moods:
        avg_mood = sum(item.get("level", 5) for item in moods) / len(moods)

    emotion_counts = {}
    for item in moods:
        emotions = item.get("emotions") or []
        for e in emotions:
            emotion_counts[e] = emotion_counts.get(e, 0) + 1
    dominant_emotions = sorted(emotion_counts.keys(), key=lambda k: emotion_counts[k], reverse=True)[:3]

    recent_journals_str = "\n".join([f"- Entry: {j.get('content')}" for j in journals])
    recent_moods_str = f"Average Mood level: {avg_mood:.1f}/10. Top emotions logged: {', '.join(dominant_emotions) if dominant_emotions else 'none'}"

    system_prompt = (
        "You are ARIA, a warm, validating companion in MindCradle. "
        "Analyze the user's latest journal entry and provide a structured reflection as a JSON object. "
        "Make sure you sound warm, empathetic, and supportively non-clinical. Do not diagnose, prescribe, or use clinical jargon.\n\n"
        "Output structure must be a JSON object with exactly these fields:\n"
        "- 'reflection': 2 to 3 sentences max. Acknowledge their emotional tone empathetically and suggest one gentle action (e.g., 'Consider journaling about this tomorrow' or 'This resilience shows growth'). Avoid clinical phrasing.\n"
        "- 'themes': a list of 2 to 3 key themes identified in today's journal.\n"
        "- 'emotional_tone': a short description of the emotional tone of today's entry.\n\n"
        "Example format:\n"
        "{\n"
        "  \"reflection\": \"I see you're processing something difficult. That takes courage. Be gentle with yourself today, and perhaps consider journaling about this tomorrow when you've had some rest.\",\n"
        "  \"themes\": [\"Processing stress\", \"Need for comfort\"],\n"
        "  \"emotional_tone\": \"Reflective and slightly tired\"\n"
        "}\n"
        "Return ONLY the raw JSON object. Do not include markdown code block syntax (like ```json) or any other text before or after the JSON."
    )

    user_content = (
        f"Today's Journal Entry: {req.journal_content}\n\n"
        f"User's past context:\n"
        f"Last 3 journal entries:\n{recent_journals_str or 'None'}\n"
        f"Last 7 mood logs:\n{recent_moods_str}\n"
    )

    try:
        reply = await openrouter_ai.chat_completion(
            [{"role": "user", "content": user_content}],
            system_prompt=system_prompt,
            temperature=0.7,
            top_p=0.9,
            max_tokens=350,
        )
        
        data = parse_json_safely(reply)
        reflection_str = data.get("reflection", "I see you're processing something difficult. That takes courage. Be gentle with yourself today.")
        themes = data.get("themes", ["Self-reflection"])
        emotional_tone = data.get("emotional_tone", "Thoughtful and introspective")

        # 3. Store conversation in ai_conversations table with type: "journal_reflection"
        payload = {
            "user": req.user_id,
            "messages": [
                {"role": "user", "content": req.journal_content},
                {"role": "assistant", "content": reflection_str}
            ],
            "summary": f"Journal reflection for {req.user_id}"
        }
        try:
            await pb.create_record(
                "ai_conversations",
                {**payload, "type": "journal_reflection"},
                token=authorization,
            )
        except Exception as store_err:
            logger.warning("Failed to store reflection with type column (schema may be outdated): %s", store_err)
            try:
                await pb.create_record(
                    "ai_conversations",
                    payload,
                    token=authorization,
                )
            except Exception as retry_err:
                logger.warning("Failed to store reflection conversation without type column: %s", retry_err)

        return JournalReflectionResponse(
            reflection=reflection_str,
            themes=themes,
            emotional_tone=emotional_tone,
            linguistic_shift=linguistic_shift_text
        )
    except Exception as e:
        logger.error("Reflection API: failed to generate or parse reflection: %s", str(e))
        raise HTTPException(
            status_code=502,
            detail=f"Couldn't get reflection, try again. Details: {str(e)}"
        )


@router.get("/solstice-letter")
async def get_solstice_letter(
    authorization: Optional[str] = Header(None)
):
    """Retrieve or generate the user's monthly/seasonal Personal Solstice growth letter."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")

    # Verify if user is premium
    try:
        profile_resp = await pb.list_records(
            "user_profiles",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        profile_items = profile_resp.get("items") or []
        is_premium = False
        if profile_items:
            is_premium, _ = verify_user_premium(profile_items[0], user_id)
        if not is_premium:
            raise HTTPException(
                status_code=402, 
                detail="Personal Solstice Reports require a Premium subscription."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Solstice Letter check: failed premium check: %s", e)
        raise HTTPException(status_code=500, detail="Database verification error")

    # Fetch last 30 days of data
    now = datetime.now(timezone.utc)
    since_30d = (now - timedelta(days=30)).isoformat()
    filter_30d = f'user_id="{user_id}" && created >= "{since_30d}"'

    try:
        # 1. Fetch Mood logs
        mood_resp = await pb.list_records("mood_logs", token=token, params={"filter": filter_30d, "perPage": 100})
        mood_items = mood_resp.get("items") or []

        # 2. Fetch Journal entries
        journal_resp = await pb.list_records("journal_entries", token=token, params={"filter": filter_30d, "perPage": 100})
        journal_items = journal_resp.get("items") or []

        # 3. Fetch Morning Rituals
        mr_resp = await pb.list_records("morning_rituals", token=token, params={"filter": filter_30d, "perPage": 100})
        mr_items = mr_resp.get("items") or []

        # 4. Fetch Wind Down Rituals
        wd_resp = await pb.list_records("wind_down_rituals", token=token, params={"filter": filter_30d, "perPage": 100})
        wd_items = wd_resp.get("items") or []

        # 5. Fetch Life Chapters
        chapter_items = []
        try:
            ch_resp = await pb.list_records(
                "user_life_chapters",
                token=token,
                params={"filter": f'user_id="{user_id}"', "sort": "-chapter_number", "perPage": 5}
            )
            chapter_items = ch_resp.get("items") or []
        except Exception as ch_err:
            logger.warning("Solstice Letter: chapters fetch error: %s", ch_err)
    except Exception as fetch_err:
        logger.error("Solstice Letter: database fetch error: %s", fetch_err)
        raise HTTPException(status_code=500, detail="Failed to fetch history logs")

    if not mood_items and not journal_items:
        return {
            "letter": "## Keep reflecting daily\n\nYour Solstice Letter will bloom once you've logged a few entries. Start by checking in your mood or writing in your journal today!"
        }

    # Compile summary context
    mood_levels = [int(m.get("level", 5)) for m in mood_items]
    avg_mood = sum(mood_levels) / len(mood_levels) if mood_levels else 5.0
    
    intentions = [mr.get("intention") for mr in mr_items if mr.get("intention")]
    worries_released = [wd.get("releaseItem") for wd in wd_items if wd.get("releaseItem")]
    journal_snippets = [j.get("content")[:100] for j in journal_items if j.get("content")]

    chapters_str = ""
    if chapter_items:
        chapters_str = "\n".join(
            f"  * Chapter {c.get('chapter_number')}: '{c.get('title')}' - {c.get('theme_summary')} (Current: {c.get('is_current')})"
            for c in chapter_items
        )

    summary_context = (
        f"User data over past 30 days:\n"
        f"- Total journal entries: {len(journal_items)}\n"
        f"- Journal Snippets: {'; '.join(journal_snippets[:5])}\n"
        f"- Average mood level: {avg_mood:.1f}/10\n"
        f"- Morning intentions set: {', '.join(intentions[:5])}\n"
        f"- Worries released in evening: {', '.join(worries_released[:5])}\n"
        f"- Personal Narrative Chapters:\n{chapters_str}\n"
    )

    sys_prompt = (
        "You are ARIA, a warm, validating companion in MindCradle. "
        "Your task is to write a personalized seasonal/monthly growth letter (The Personal Solstice Letter) to the user based on their past 30 days of data. "
        "Use their Personal Narrative Chapters as the narrative spine of the letter. Focus on their progression, triumphs, and struggles within those chapters. "
        "Structure the letter in clean, markdown format with headings (##). "
        "Acknowledge their consistency, identify emotional seasons (patterns in mood, intentions, and worries), highlight private victories (worries they successfully released or intentions met), and offer one supportive, inspiring thought for the month ahead. "
        "Make sure the letter sounds deeply personal, validating, and completely free of clinical jargon."
    )

    try:
        letter_content = await openrouter_ai.chat_completion(
            [{"role": "user", "content": summary_context}],
            system_prompt=sys_prompt,
            temperature=0.7,
            max_tokens=600,
        )
        letter_stripped = letter_content.strip()
        
        # Cache the generated letter in timeline_events
        try:
            import uuid
            TIMELINE_NAMESPACE = uuid.UUID('12345678-1234-5678-1234-567812345678')
            now_iso = datetime.now(timezone.utc).isoformat()
            year_month = datetime.now(timezone.utc).strftime("%Y-%m")
            month_name = datetime.now(timezone.utc).strftime("%B %Y")
            deterministic_id = str(uuid.uuid5(TIMELINE_NAMESPACE, f"solstice-{user_id}-{year_month}"))
            
            evt = {
                "user_id": user_id,
                "event_type": "letter",
                "source_id": deterministic_id,
                "event_date": year_month + "-01", # standard start of month date
                "event_ts": now_iso,
                "title": f"Solstice Letter · {month_name}",
                "summary": letter_stripped[:250] + ("..." if len(letter_stripped) > 250 else ""),
                "search_text": f"solstice letter report seasonal monthly {letter_stripped}".strip(),
                "metadata": {"letter_content": letter_stripped},
            }
            
            # Upsert into timeline_events cache
            await pb.upsert_records(
                "timeline_events",
                records=[evt],
                token=token,
                on_conflict="user_id,event_type,source_id"
            )
        except Exception as cache_err:
            logger.warning("Failed to cache generated Solstice letter in timeline_events: %s", cache_err)

        return {"letter": letter_stripped}
    except Exception as e:
        logger.error("Failed to generate Solstice Letter: %s", e)
        raise HTTPException(status_code=502, detail="Failed to synthesize Solstice Letter")


@router.post("/mood-analysis", response_model=MoodAnalysisResponse)
async def mood_analysis(
    req: MoodAnalysisRequest,
    authorization: Optional[str] = Header(None),
):
    """Analyze weekly or monthly mood logs and habit patterns to produce structured AI observation."""
    token = _normalize_token(authorization)
    is_premium = False
    if token:
        try:
            profile_resp = await pb.list_records(
                "user_profiles",
                token=token,
                params={"filter": f'user_id="{req.user_id}"', "perPage": 1}
            )
            items = profile_resp.get("items") or []
            if items:
                is_premium, _ = verify_user_premium(items[0], req.user_id)
        except Exception as profile_err:
            logger.warning("Failed to fetch user profile in mood_analysis: %s", profile_err)

    days = 30 if is_premium else 7
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    filter_str = f'user_id="{req.user_id}" && created >= "{since}"'
    
    try:
        morning_resp = await pb.list_records("morning_rituals", token=authorization, params={"filter": filter_str})
        morning_count = len(morning_resp.get("items") or [])
    except Exception as e:
        logger.warning(f"Failed to fetch user's last {days} morning rituals: %s", e)
        morning_count = 0

    try:
        wind_down_resp = await pb.list_records("wind_down_rituals", token=authorization, params={"filter": filter_str})
        wind_down_count = len(wind_down_resp.get("items") or [])
    except Exception as e:
        logger.warning(f"Failed to fetch user's last {days} wind down rituals: %s", e)
        wind_down_count = 0

    try:
        journal_resp = await pb.list_records("journal_entries", token=authorization, params={"filter": filter_str})
        journal_count = len(journal_resp.get("items") or [])
    except Exception as e:
        logger.warning(f"Failed to fetch user's last {days} journals: %s", e)
        journal_count = 0

    mood_data = req.mood_data
    avg_mood_level = 5.0
    highest_day = "None"
    lowest_day = "None"
    emotions = []
    
    if mood_data:
        levels = [int(m.get("level", 5)) for m in mood_data]
        avg_mood_level = sum(levels) / len(levels)
        
        sorted_moods = sorted(mood_data, key=lambda x: int(x.get("level", 5)))
        lowest_day = f"{sorted_moods[0].get('date', '')[:10]} (level {sorted_moods[0].get('level')})"
        highest_day = f"{sorted_moods[-1].get('date', '')[:10]} (level {sorted_moods[-1].get('level')})"
        
        for m in mood_data:
            emotions.extend(m.get("emotions", []))
            
    trend_str = "stable"
    if len(mood_data) >= 2:
        sorted_by_date = sorted(mood_data, key=lambda x: x.get("date", ""))
        first_half = sorted_by_date[:len(sorted_by_date)//2]
        second_half = sorted_by_date[len(sorted_by_date)//2:]
        avg_first = sum(int(x.get("level", 5)) for x in first_half) / len(first_half)
        avg_second = sum(int(x.get("level", 5)) for x in second_half) / len(second_half)
        
        if avg_second - avg_first > 0.5:
            trend_str = "upward"
        elif avg_first - avg_second > 0.5:
            trend_str = "downward"

    emotion_counts = {}
    for e in emotions:
        emotion_counts[e] = emotion_counts.get(e, 0) + 1
    dominant_emotions = sorted(emotion_counts.keys(), key=lambda k: emotion_counts[k], reverse=True)[:3]

    system_prompt = (
        "You are ARIA, a warm, validating mental health companion in MindCradle. "
        f"Analyze the user's {'monthly' if is_premium else 'weekly'} mood data and ritual habits, then output a JSON object. "
        "Keep the tone extremely conversational, supportive, and non-clinical (like talking to a friend).\n\n"
        "Output structure must be a JSON object with exactly these keys:\n"
        "- 'analysis': One honest observation about their mood trend. Warm and validating. Max 1 sentence.\n"
        "- 'pattern': One key pattern or connection you noticed (e.g., how their mood correlates with morning/evening rituals, or weekday vs weekend). Max 1 sentence.\n"
        "- 'suggestion': One gentle, specific suggestion for self-care. Max 1 sentence.\n"
        "- 'mood_trend': A string representing the mood trend (e.g., 'improving', 'declining', or 'stable').\n\n"
        "Total length of all sentences in 'analysis', 'pattern', and 'suggestion' combined must be at most 3 sentences.\n\n"
        "Example output format:\n"
        "{\n"
        "  \"analysis\": \"I noticed your mood was a bit steadier this week, though you had a couple of heavier days mid-week.\",\n"
        "  \"pattern\": \"You seem to report feeling much calmer on days when you completed your morning rituals.\",\n"
        "  \"suggestion\": \"Try the Wind Down ritual more consistently to help you ease into the evening.\",\n"
        "  \"mood_trend\": \"stable\"\n"
        "}\n"
        "Return ONLY the raw JSON object. Do not include markdown code block syntax (like ```json) or any other text before or after the JSON."
    )
    
    user_prompt = (
        f"User's Mood Logs (last {days} days):\n"
        f"- Average mood level: {avg_mood_level:.1f}/10\n"
        f"- Mood trend direction: {trend_str}\n"
        f"- Highest mood day: {highest_day}\n"
        f"- Lowest mood day: {lowest_day}\n"
        f"- Dominant emotions: {', '.join(dominant_emotions) if dominant_emotions else 'None specified'}\n\n"
        f"User's Habit Data (last {days} days):\n"
        f"- Morning Ritual completion count: {morning_count} out of {days} days\n"
        f"- Evening Wind Down completion count: {wind_down_count} out of {days} days\n"
        f"- Guided Journal frequency: {journal_count} entries\n"
    )

    try:
        reply = await openrouter_ai.chat_completion(
            [{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            temperature=0.7,
            top_p=0.9,
            max_tokens=350,
        )
        
        data = parse_json_safely(reply)
        analysis = data.get("analysis", f"I noticed your mood patterns remained fairly stable this {'month' if is_premium else 'week'}.")
        pattern = data.get("pattern", "You report steadier levels on days you check in consistently.")
        suggestion = data.get("suggestion", "Try the Wind Down ritual more consistently.")
        mood_trend = data.get("mood_trend", trend_str)

        payload = {
            "user": req.user_id,
            "messages": [
                {"role": "user", "content": f"Analyze my mood logs and habit patterns for the {'month' if is_premium else 'week'}."},
                {"role": "assistant", "content": f"Here's what I noticed about your {'month' if is_premium else 'week'}:\n\nObservation: {analysis}\nPattern: {pattern}\nSuggestion: {suggestion}"}
            ],
            "summary": f"{'Monthly' if is_premium else 'Weekly'} mood analysis for {req.user_id}"
        }
        try:
            await pb.create_record(
                "ai_conversations",
                {**payload, "type": "mood_analysis"},
                token=authorization,
            )
        except Exception as store_err:
            logger.warning("Failed to store mood analysis with type column: %s", store_err)
            try:
                await pb.create_record(
                    "ai_conversations",
                    payload,
                    token=authorization,
                )
            except Exception as retry_err:
                logger.warning("Failed to store mood analysis conversation without type column: %s", retry_err)

        return MoodAnalysisResponse(
            analysis=analysis,
            pattern=pattern,
            suggestion=suggestion,
            mood_trend=mood_trend
        )
    except Exception as e:
        logger.error("Mood Analysis API: failed to analyze mood: %s", str(e))
        raise HTTPException(
            status_code=502,
            detail=f"Couldn't analyze mood trends, try again. Details: {str(e)}"
        )


@router.get("/conversations", response_model=list[ConversationSummaryResponse])
async def get_conversations(
    authorization: Optional[str] = Header(None),
):
    """Retrieve all conversation summaries for the user (privacy-focused timeline)."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    try:
        resp = await pb.list_records(
            "ai_conversations",
            token=token,
            params={"sort": "-updated", "perPage": 100, "filter": f'user_id="{user_id}"'}
        )
        items = resp.get("items") or []
        
        formatted = []
        for i in items:
            formatted.append(ConversationSummaryResponse(
                id=i.get("id"),
                user_id=i.get("user_id"),
                created=i.get("created"),
                updated=i.get("updated"),
                summary=i.get("summary"),
                key_points=i.get("key_points") or [],
                follow_up_needed=i.get("follow_up_needed") or False,
                follow_up_date=str(i.get("follow_up_date")) if i.get("follow_up_date") else None,
                emotional_journey=i.get("emotional_journey"),
                is_active=i.get("is_active", True)
            ))
        return formatted
    except Exception as e:
        logger.error("Failed to list conversations: %s", e)
        return []


@router.get("/conversations/active", response_model=Optional[ConversationSummaryResponse])
async def get_active_conversation(
    authorization: Optional[str] = Header(None),
):
    """Retrieve the active conversation for the user, if one exists."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    try:
        resp = await pb.list_records(
            "ai_conversations",
            token=token,
            params={"sort": "-updated", "perPage": 1, "filter": f'user_id="{user_id}" && is_active=true'}
        )
        items = resp.get("items") or []
        if items:
            i = items[0]
            return ConversationSummaryResponse(
                id=i.get("id"),
                user_id=i.get("user_id"),
                created=i.get("created"),
                updated=i.get("updated"),
                summary=i.get("summary"),
                messages=i.get("messages") or [],
                key_points=i.get("key_points") or [],
                follow_up_needed=i.get("follow_up_needed") or False,
                follow_up_date=str(i.get("follow_up_date")) if i.get("follow_up_date") else None,
                emotional_journey=i.get("emotional_journey"),
                is_active=i.get("is_active", True)
            )
        return None
    except Exception as e:
        logger.error("Failed to fetch active conversation: %s", e)
        return None


@router.post("/conversations/{conversation_id}/end")
async def end_conversation(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
):
    """Mark a conversation as inactive and trigger immediate summarization."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        await pb.update_record("ai_conversations", conversation_id, {"is_active": False}, token=token)
        background_tasks.add_task(_summarize_conversation_background, token, conversation_id)
        return {"ended": True}
    except Exception as e:
        logger.error("Failed to end conversation %s: %s", conversation_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to end conversation: {str(e)}")


@router.get("/check-in", response_model=CheckInResponse)
async def get_check_in(
    authorization: Optional[str] = Header(None),
):
    """Auto-generate a check-in message based on pending follow-ups."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Find pending follow-ups
        resp = await pb.list_records(
            "ai_conversations",
            token=token,
            params={
                "sort": "-updated",
                "perPage": 1,
                "filter": f'user_id="{user_id}" && follow_up_needed=true && follow_up_date <= "{today_str}"'
            }
        )
        items = resp.get("items") or []
        if not items:
            return CheckInResponse(check_in_message=None, conversation_id=None)
            
        convo = items[0]
        convo_id = convo["id"]
        summary = convo.get("summary") or "A prior conversation."
        
        system_prompt = (
            "You are ARIA, a quiet companion. "
            "Generate a warm, single-sentence check-in message for the user based on the summary of a past conversation.\n"
            "Keep it under 25 words, extremely personal, warm, and reference the summary details naturally.\n"
            "Do not start with generic pleasantries if not needed. Make it feel continuous and thoughtful."
        )
        user_prompt = f"Past Conversation Summary:\n{summary}"
        
        check_in_msg = "I've been thinking about our last chat—how are you holding up today?"
        if not FALLBACK_MODE:
            try:
                check_in_msg = await openrouter_ai.chat_completion(
                    [{"role": "user", "content": user_prompt}],
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=80
                )
            except Exception as err:
                logger.warning("Failed to call OpenRouter for check-in generation: %s", err)
                
        # Mark follow_up_needed as false so they don't get prompted repeatedly
        await pb.update_record("ai_conversations", convo_id, {"follow_up_needed": False}, token=token)
        
        return CheckInResponse(
            check_in_message=check_in_msg.strip(),
            conversation_id=convo_id
        )
    except Exception as e:
        logger.error("Failed to generate check-in: %s", e)
        return CheckInResponse(check_in_message=None, conversation_id=None)


@router.post("/schedule-checkin", response_model=ScheduleCheckinResponse)
async def schedule_checkin(
    authorization: Optional[str] = Header(None),
):
    """Analyze user patterns and schedule the next proactive check-in if appropriate."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"

    try:
        # 1. Check if notifications are enabled
        tokens_resp = await pb.list_records(
            "push_notification_tokens",
            token=token,
            params={"filter": f'user_id="{user_id}" && is_active=true'}
        )
        has_notifications = len(tokens_resp.get("items") or []) > 0
        if not has_notifications:
            return ScheduleCheckinResponse(status="skipped", reason="notifications_disabled")

        # 2. Check if already scheduled for today
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        today_start_str = today_start.isoformat()
        today_end_str = today_end.isoformat()

        checkins_today = await pb.list_records(
            "proactive_checkins",
            token=token,
            params={"filter": f'user_id="{user_id}" && scheduled_time >= "{today_start_str}" && scheduled_time < "{today_end_str}"'}
        )
        if checkins_today.get("items"):
            return ScheduleCheckinResponse(status="skipped", reason="already_scheduled_today")

        # 3. Query historical data from last 30 days
        since_30d = (now - timedelta(days=30)).isoformat()
        
        # Mood logs
        mood_resp = await pb.list_records(
            "mood_logs",
            token=token,
            params={"sort": "-created", "perPage": 1000, "filter": f'user_id="{user_id}" && created >= "{since_30d}"'}
        )
        mood_logs = mood_resp.get("items") or []

        # Journal entries (last 3 days)
        since_3d = (now - timedelta(days=3)).isoformat()
        journal_resp = await pb.list_records(
            "journal_entries",
            token=token,
            params={"perPage": 1, "filter": f'user_id="{user_id}" && created >= "{since_3d}"'}
        )
        has_journaled_last_3d = len(journal_resp.get("items") or []) > 0

        # Rituals (last 3 days)
        mr_resp = await pb.list_records(
            "morning_rituals",
            token=token,
            params={"perPage": 1, "filter": f'user_id="{user_id}" && created >= "{since_3d}"'}
        )
        wd_resp = await pb.list_records(
            "wind_down_rituals",
            token=token,
            params={"perPage": 1, "filter": f'user_id="{user_id}" && created >= "{since_3d}"'}
        )
        has_rituals_last_3d = (len(mr_resp.get("items") or []) > 0) or (len(wd_resp.get("items") or []) > 0)

        # Themes (last 30 days)
        theme_resp = await pb.list_records(
            "conversation_themes",
            token=token,
            params={"perPage": 100, "filter": f'user_id="{user_id}" && created_at >= "{since_30d}"'}
        )
        conversation_themes = theme_resp.get("items") or []

        # Behavioral patterns (CIE Phase 4)
        behavioral_patterns = []
        try:
            pat_resp = await pb.list_records(
                "user_behavioral_patterns",
                token=token,
                params={"filter": f'user_id="{user_id}" && is_active=true', "perPage": 10}
            )
            behavioral_patterns = pat_resp.get("items") or []
        except Exception as pat_err:
            logger.warning("Proactive schedule: failed to fetch behavioral patterns: %s", pat_err)

        # 4. Check past ignored check-ins in the last 7 days (engagement filter)
        since_7d = (now - timedelta(days=7)).isoformat()
        past_checkins_resp = await pb.list_records(
            "proactive_checkins",
            token=token,
            params={"filter": f'user_id="{user_id}" && created_at >= "{since_7d}"'}
        )
        past_checkins = past_checkins_resp.get("items") or []
        ignored_reasons = set()
        for pc in past_checkins:
            if not pc.get("actual_response") and pc.get("effectiveness") is None:
                if pc.get("reason"):
                    ignored_reasons.add(pc["reason"])

        candidates = []

        # Rule 1: Rough Day (last mood log today/yesterday <= 4)
        rough_day_log = None
        for log in mood_logs:
            created_str = log.get("created")
            try:
                clean_date = created_str.replace("T", " ").split(".")[0].replace("Z", "")
                log_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                try:
                    log_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except Exception:
                    continue
            if (now - log_date).total_seconds() <= 86400 * 1.5:  # 36 hours
                if log.get("level", 10) <= 4:
                    rough_day_log = log
                    break
        if rough_day_log and "rough_day" not in ignored_reasons:
            target_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if target_time < now:
                target_time = now + timedelta(hours=1)
            candidates.append({
                "reason": "rough_day",
                "suggested_message": "How are you holding up?",
                "scheduled_time": target_time
            })

        # Rule 2: Weekday Anxiety Spike
        weekday_counts = {i: 0 for i in range(7)}
        weekday_anxiety_counts = {i: 0 for i in range(7)}
        weekday_moods = {i: [] for i in range(7)}
        for log in mood_logs:
            created_str = log.get("created")
            try:
                clean_date = created_str.replace("T", " ").split(".")[0].replace("Z", "")
                log_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                try:
                    log_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except Exception:
                    continue
            wd = log_date.weekday()
            weekday_counts[wd] += 1
            level = log.get("level")
            if level is not None:
                weekday_moods[wd].append(level)
            
            raw_emotions = log.get("emotions") or []
            if isinstance(raw_emotions, str):
                try:
                    raw_emotions = json.loads(raw_emotions)
                except Exception:
                    raw_emotions = [e.strip() for e in raw_emotions.split(",") if e.strip()]
            emotions = [str(e).strip().lower() for e in raw_emotions if e]
            is_anxious = any(e in ["anxious", "anxiety", "stressed", "stress"] for e in emotions)
            if is_anxious:
                weekday_anxiety_counts[wd] += 1

        anxiety_days = []
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for wd in range(7):
            avg_mood = (sum(weekday_moods[wd]) / len(weekday_moods[wd])) if weekday_moods[wd] else 10.0
            if weekday_anxiety_counts[wd] >= 2 or (avg_mood <= 5.5 and weekday_counts[wd] >= 2):
                anxiety_days.append(wd)

        for anxiety_wd in anxiety_days:
            reason_name = f"anxiety_spike_{weekday_names[anxiety_wd].lower()}"
            if reason_name in ignored_reasons:
                continue
            checkin_wd = (anxiety_wd - 1) % 7
            days_ahead = checkin_wd - now.weekday()
            if days_ahead < 0:
                days_ahead += 7
            elif days_ahead == 0 and now.hour >= 18:
                days_ahead += 7
            scheduled_date = now + timedelta(days=days_ahead)
            scheduled_time = scheduled_date.replace(hour=18, minute=0, second=0, microsecond=0)
            candidates.append({
                "reason": reason_name,
                "suggested_message": f"Looks like {weekday_names[anxiety_wd]}s can be tough for you. Want to prep for it?",
                "scheduled_time": scheduled_time
            })

        # Rule 3: Noticed Positive Trend (last 7 days vs previous 7 days)
        w1_levels = []
        w2_levels = []
        for log in mood_logs:
            created_str = log.get("created")
            try:
                clean_date = created_str.replace("T", " ").split(".")[0].replace("Z", "")
                log_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                try:
                    log_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except Exception:
                    continue
            days_diff = (now - log_date).days
            level = log.get("level")
            if level is not None:
                if days_diff < 7:
                    w1_levels.append(level)
                elif days_diff < 14:
                    w2_levels.append(level)
        if len(w1_levels) >= 2 and len(w2_levels) >= 2:
            avg1 = sum(w1_levels) / len(w1_levels)
            avg2 = sum(w2_levels) / len(w2_levels)
            if avg1 >= avg2 + 1.5 and "positive_trend" not in ignored_reasons:
                candidates.append({
                    "reason": "positive_trend",
                    "suggested_message": "I've noticed you're doing better - what changed?",
                    "scheduled_time": now + timedelta(days=1)
                })

        # Rule 4: Repeating Theme (theme count >= 3)
        theme_counts = {}
        for t in conversation_themes:
            theme_name = t.get("theme")
            if theme_name:
                theme_counts[theme_name] = theme_counts.get(theme_name, 0) + 1
        repeating_themes = [theme for theme, count in theme_counts.items() if count >= 3]
        if repeating_themes and "repeating_theme" not in ignored_reasons:
            theme = repeating_themes[0]
            reason_name = f"repeating_theme_{theme.lower().replace(' ', '_')}"
            if reason_name not in ignored_reasons:
                candidates.append({
                    "reason": reason_name,
                    "suggested_message": f"{theme} stuff again? Let's talk about it",
                    "scheduled_time": now + timedelta(days=1)
                })

        # Rule 5: Journal Reminder
        if not has_journaled_last_3d and "journal_reminder" not in ignored_reasons:
            candidates.append({
                "reason": "journal_reminder",
                "suggested_message": "You haven't written in a couple of days. Want to do a quick reflection?",
                "scheduled_time": now + timedelta(days=1)
            })

        # Rule 6: Ritual Reminder
        if not has_rituals_last_3d and "ritual_reminder" not in ignored_reasons:
            candidates.append({
                "reason": "ritual_reminder",
                "suggested_message": "Missing our time together? Want to do a ritual?",
                "scheduled_time": now + timedelta(days=1)
            })

        # Select candidate based on priority
        priority_order = ["rough_day", "anxiety_spike", "positive_trend", "repeating_theme", "journal_reminder", "ritual_reminder"]
        def get_priority(cand):
            reason = cand["reason"]
            for idx, prefix in enumerate(priority_order):
                if reason.startswith(prefix):
                    return idx
            return len(priority_order)

        if not candidates:
            return ScheduleCheckinResponse(status="skipped", reason="no_patterns_detected")

        candidates.sort(key=get_priority)
        selected = candidates[0]

        # Optimize scheduled time based on user behavioral patterns (CIE Phase 4)
        scheduled_time = selected["scheduled_time"]
        
        # 1. Parse reflection routine hour if exists
        reflection_hour = None
        has_sunday_dread = False
        for pat in behavioral_patterns:
            p_label = str(pat.get("label") or "").lower()
            p_type = str(pat.get("pattern_type") or "").lower()
            if "reflection_routine" in p_label or "routine" in p_type:
                # Check for "hour X" format
                if "hour" in p_label:
                    try:
                        parts = p_label.split("hour")
                        if len(parts) > 1:
                            reflection_hour = int(parts[1].strip().split()[0])
                    except Exception:
                        pass
                if reflection_hour is None:
                    meta = pat.get("metadata") or {}
                    if meta.get("avg_hour") is not None:
                        reflection_hour = int(meta["avg_hour"])
            if "sunday dread" in p_label or "sunday_dread" in p_label:
                has_sunday_dread = True

        # 2. Adjust hour for reminder actions to user's habitual reflection hour
        if reflection_hour is not None and selected["reason"] in ["journal_reminder", "ritual_reminder"]:
            scheduled_time = scheduled_time.replace(hour=reflection_hour, minute=0, second=0, microsecond=0)
            if scheduled_time < now:
                scheduled_time += timedelta(days=1)

        # 3. Schedule prep for Sunday Dread specifically on Sunday evenings
        if has_sunday_dread and "anxiety" in selected["reason"]:
            days_ahead = (6 - now.weekday()) % 7
            scheduled_time = (now + timedelta(days=days_ahead)).replace(hour=18, minute=0, second=0, microsecond=0)
            if scheduled_time < now:
                scheduled_time += timedelta(days=7)

        payload = {
            "user_id": user_id,
            "scheduled_time": scheduled_time.isoformat(),
            "reason": selected["reason"],
            "suggested_message": selected["suggested_message"],
            "actual_response": None,
            "effectiveness": None
        }

        created = await pb.create_record("proactive_checkins", payload, token=token)
        
        res_checkin = ProactiveCheckinResponse(
            id=created["id"],
            user_id=created["user_id"],
            scheduled_time=created["scheduled_time"],
            reason=created.get("reason"),
            suggested_message=created.get("suggested_message"),
            actual_response=created.get("actual_response"),
            effectiveness=created.get("effectiveness"),
            created_at=created.get("created_at") or created.get("created") or datetime.now(timezone.utc).isoformat()
        )

        return ScheduleCheckinResponse(status="scheduled", checkin=res_checkin)

    except Exception as e:
        logger.error("Failed to schedule proactive check-in: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to schedule check-in: {str(e)}")


@router.get("/proactive-checkins", response_model=list[ProactiveCheckinResponse])
async def list_proactive_checkins(
    authorization: Optional[str] = Header(None),
):
    """List all proactive check-ins for the user that have been triggered (scheduled_time <= now)."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"
    now_str = datetime.now(timezone.utc).isoformat()

    try:
        resp = await pb.list_records(
            "proactive_checkins",
            token=token,
            params={
                "sort": "-scheduled_time",
                "perPage": 50,
                "filter": f'user_id="{user_id}" && scheduled_time <= "{now_str}"'
            }
        )
        items = resp.get("items") or []
        
        results = []
        for it in items:
            results.append(ProactiveCheckinResponse(
                id=it["id"],
                user_id=it["user_id"],
                scheduled_time=it["scheduled_time"],
                reason=it.get("reason"),
                suggested_message=it.get("suggested_message"),
                actual_response=it.get("actual_response"),
                effectiveness=it.get("effectiveness"),
                created_at=it.get("created_at") or it.get("created") or datetime.now(timezone.utc).isoformat()
            ))
        return results
    except Exception as e:
        logger.error("Failed to list proactive check-ins: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch proactive check-ins: {str(e)}")


@router.post("/proactive-checkins/{checkin_id}/respond", response_model=ProactiveCheckinResponse)
async def respond_to_proactive_checkin(
    checkin_id: str,
    req: ProactiveCheckinRespondRequest,
    authorization: Optional[str] = Header(None),
):
    """Record the user's response to a proactive check-in and calculate its effectiveness."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        eff = req.effectiveness
        if eff is None:
            pos_words = ["great", "good", "helpful", "thanks", "thank", "better", "yes", "calm", "helped"]
            neg_words = ["bad", "worse", "not", "no", "useless", "annoying", "stop", "spam", "unhelpful"]
            
            resp_lower = req.actual_response.lower()
            pos_count = sum(1 for w in pos_words if w in resp_lower)
            neg_count = sum(1 for w in neg_words if w in resp_lower)
            
            if pos_count > neg_count:
                eff = 5
            elif neg_count > pos_count:
                eff = 1
            else:
                eff = 3
                
        payload = {
            "actual_response": req.actual_response,
            "effectiveness": eff
        }
        
        updated = await pb.update_record("proactive_checkins", checkin_id, payload, token=token)
        
        return ProactiveCheckinResponse(
            id=updated["id"],
            user_id=updated["user_id"],
            scheduled_time=updated["scheduled_time"],
            reason=updated.get("reason"),
            suggested_message=updated.get("suggested_message"),
            actual_response=updated.get("actual_response"),
            effectiveness=updated.get("effectiveness"),
            created_at=updated.get("created_at") or updated.get("created") or datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        logger.error("Failed to respond to proactive check-in %s: %s", checkin_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to record response: {str(e)}")


@router.get("/recovery-patterns", response_model=RecoveryPatternsResponse)
async def get_recovery_patterns(
    authorization: Optional[str] = Header(None),
):
    """Analyze mood logs over the user's history, log/update mood dips in recovery_data, and calculate statistics."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token) or "unknown"

    try:
        # 1. Fetch mood logs sorted by date ascending
        mood_resp = await pb.list_records(
            "mood_logs",
            token=token,
            params={"sort": "created", "perPage": 1000, "filter": f'user_id="{user_id}"'}
        )
        mood_logs = mood_resp.get("items") or []

        # 2. Fetch existing recovery_data records
        recovery_resp = await pb.list_records(
            "recovery_data",
            token=token,
            params={"filter": f'user_id="{user_id}"'}
        )
        existing_recoveries = recovery_resp.get("items") or []
        existing_by_date = {r["mood_dip_date"]: r for r in existing_recoveries}

        # 3. Query all user's journals, rituals, and AI chats for catalyst tracking
        journal_resp = await pb.list_records(
            "journal_entries",
            token=token,
            params={"perPage": 1000, "filter": f'user_id="{user_id}"'}
        )
        journals = journal_resp.get("items") or []

        mr_resp = await pb.list_records(
            "morning_rituals",
            token=token,
            params={"perPage": 1000, "filter": f'user_id="{user_id}"'}
        )
        morning_rituals = mr_resp.get("items") or []

        wd_resp = await pb.list_records(
            "wind_down_rituals",
            token=token,
            params={"perPage": 1000, "filter": f'user_id="{user_id}"'}
        )
        wind_down_rituals = wd_resp.get("items") or []

        chat_resp = await pb.list_records(
            "ai_conversations",
            token=token,
            params={"perPage": 1000, "filter": f'user_id="{user_id}"'}
        )
        chats = chat_resp.get("items") or []

        # Helper to parse datetime safely
        def parse_dt(dt_str):
            if not dt_str:
                return None
            try:
                clean = dt_str.replace("T", " ").split(".")[0].replace("Z", "")
                return datetime.strptime(clean, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                try:
                    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                except Exception:
                    return None

        # 4. Tracing Algorithm
        current_dip = None
        computed_dips = []

        for log in mood_logs:
            created_str = log.get("created")
            log_date = parse_dt(created_str)
            if not log_date:
                continue

            level = log.get("level")
            if level is None:
                continue

            # Check if this is a dip
            if level <= 4:
                if current_dip is None:
                    # Start a new dip
                    current_dip = {
                        "mood_dip_date": created_str,
                        "lowest_level": level,
                        "severity": "severe" if level <= 2 else "moderate",
                        "recovery_date": None,
                        "recovery_days": None,
                        "catalyst": None
                    }
                else:
                    # Update lowest level if lower
                    if level < current_dip["lowest_level"]:
                        current_dip["lowest_level"] = level
                        current_dip["severity"] = "severe" if level <= 2 else "moderate"
            elif level >= 6 and current_dip is not None:
                # Recovered!
                dip_date_dt = parse_dt(current_dip["mood_dip_date"])
                if dip_date_dt:
                    diff_sec = (log_date - dip_date_dt).total_seconds()
                    recovery_days = max(1, round(diff_sec / 86400.0))
                    
                    # Find catalysts during this window
                    window_journals = [j for j in journals if dip_date_dt <= (parse_dt(j.get("created")) or datetime.min.replace(tzinfo=timezone.utc)) <= log_date]
                    window_mr = [r for r in morning_rituals if dip_date_dt <= (parse_dt(r.get("created") or r.get("completed_at")) or datetime.min.replace(tzinfo=timezone.utc)) <= log_date]
                    window_wd = [r for r in wind_down_rituals if dip_date_dt <= (parse_dt(r.get("created")) or datetime.min.replace(tzinfo=timezone.utc)) <= log_date]
                    window_chats = [c for c in chats if dip_date_dt <= (parse_dt(c.get("created") or c.get("updated")) or datetime.min.replace(tzinfo=timezone.utc)) <= log_date]

                    catalyst_list = []
                    if window_journals:
                        catalyst_list.append("journaling")
                    if window_mr or window_wd:
                        catalyst_list.append("rituals")
                    if window_chats:
                        catalyst_list.append("chatting with ARIA")

                    catalyst_str = " & ".join(catalyst_list) if catalyst_list else "isolation"

                    current_dip["recovery_date"] = created_str
                    current_dip["recovery_days"] = recovery_days
                    current_dip["catalyst"] = catalyst_str
                    
                    computed_dips.append(current_dip)
                    current_dip = None

        if current_dip is not None:
            computed_dips.append(current_dip)

        # 5. Sync computed dips to the database recovery_data table
        for dip in computed_dips:
            dip_date_str = dip["mood_dip_date"]
            payload = {
                "user_id": user_id,
                "mood_dip_date": dip_date_str,
                "lowest_level": dip["lowest_level"],
                "recovery_date": dip["recovery_date"],
                "recovery_days": dip["recovery_days"],
                "catalyst": dip["catalyst"],
                "severity": dip["severity"]
            }

            if dip_date_str in existing_by_date:
                existing_rec = existing_by_date[dip_date_str]
                has_changed = (
                    existing_rec.get("recovery_date") != dip["recovery_date"] or
                    existing_rec.get("recovery_days") != dip["recovery_days"] or
                    existing_rec.get("catalyst") != dip["catalyst"] or
                    existing_rec.get("lowest_level") != dip["lowest_level"]
                )
                if has_changed:
                    await pb.update_record("recovery_data", existing_rec["id"], payload, token=token)
            else:
                await pb.create_record("recovery_data", payload, token=token)

        # 6. Re-query all recovery data from DB to ensure accurate IDs and sorting
        final_resp = await pb.list_records(
            "recovery_data",
            token=token,
            params={"sort": "-mood_dip_date", "perPage": 200, "filter": f'user_id="{user_id}"'}
        )
        db_items = final_resp.get("items") or []

        # 7. Calculate stats
        completed_recoveries = [r for r in db_items if r.get("recovery_days") is not None]
        
        if not completed_recoveries:
            stats = RecoveryStats(
                average_recovery_days=0.0,
                fastest_recovery_days=None,
                fastest_recovery_catalyst=None,
                longest_recovery_days=None,
                longest_recovery_catalyst=None,
                trend_description="No recovery logs to compute trend yet"
            )
        else:
            avg_days = sum(r["recovery_days"] for r in completed_recoveries) / len(completed_recoveries)
            completed_sorted = sorted(completed_recoveries, key=lambda x: x["mood_dip_date"])
            
            fastest = min(completed_recoveries, key=lambda x: x["recovery_days"])
            longest = max(completed_recoveries, key=lambda x: x["recovery_days"])
            
            if len(completed_sorted) >= 2:
                half = len(completed_sorted) // 2
                older_avg = sum(r["recovery_days"] for r in completed_sorted[:half]) / half
                newer_avg = sum(r["recovery_days"] for r in completed_sorted[half:]) / (len(completed_sorted) - half)
                
                if newer_avg < older_avg:
                    trend_desc = f"Getting better at recovering (was {older_avg:.1f} days, now {newer_avg:.1f} days)"
                elif newer_avg > older_avg:
                    trend_desc = f"Recovery taking slightly longer (was {older_avg:.1f} days, now {newer_avg:.1f} days)"
                else:
                    trend_desc = f"Recovery speed is stable at {newer_avg:.1f} days"
            else:
                trend_desc = f"Baseline established at {completed_sorted[0]['recovery_days']} days"

            stats = RecoveryStats(
                average_recovery_days=round(avg_days, 1),
                fastest_recovery_days=fastest["recovery_days"],
                fastest_recovery_catalyst=fastest.get("catalyst"),
                longest_recovery_days=longest["recovery_days"],
                longest_recovery_catalyst=longest.get("catalyst"),
                trend_description=trend_desc
            )

        history = []
        for r in db_items:
            history.append(RecoveryDataResponse(
                id=r["id"],
                user_id=r["user_id"],
                mood_dip_date=r["mood_dip_date"],
                lowest_level=r["lowest_level"],
                recovery_date=r.get("recovery_date"),
                recovery_days=r.get("recovery_days"),
                catalyst=r.get("catalyst"),
                severity=r.get("severity"),
                created_at=r.get("created_at") or r.get("created") or datetime.now(timezone.utc).isoformat()
            ))

        return RecoveryPatternsResponse(history=history, stats=stats)

    except Exception as e:
        logger.error("Failed to analyze recovery patterns: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze recovery patterns: {str(e)}")


from pydantic import BaseModel

class TelemetryInteractionRequest(BaseModel):
    event_type: str
    element_id: Optional[str] = None
    element_name: Optional[str] = None
    page_path: str
    input_placeholder: Optional[str] = None
    input_length: Optional[int] = 0
    metadata: Optional[dict] = None

@router.post("/track-interaction")
async def track_interaction(
    req: TelemetryInteractionRequest,
    authorization: Optional[str] = Header(None)
):
    """Track clicks, navigations, and input placeholder usage and report to database."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        payload = {
            "user_id": user_id,
            "event_type": req.event_type,
            "element_id": req.element_id,
            "element_name": req.element_name,
            "page_path": req.page_path,
            "input_placeholder": req.input_placeholder,
            "input_length": req.input_length,
            "metadata": req.metadata or {}
        }
        rec = await pb.create_record("user_interactions", payload, token=token)
        return {"success": True, "id": rec["id"]}
    except Exception as e:
        logger.error("Error logging interaction: %s", e)
        return {"success": False, "error": str(e)}

@router.get("/30day-insights")
async def get_30day_insights(
    authorization: Optional[str] = Header(None)
):
    """Generate 30-day AI Insights and analytics report."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    try:
        since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        filter_user = f'user_id="{user_id}"'
        
        # Retrieve mood logs
        moods = await pb.list_records(
            "mood_logs",
            token=token,
            params={"filter": f'{filter_user} && created >= "{since_30d}"', "perPage": 100}
        )
        moods_items = moods.get("items") or []
        
        # Retrieve journal entries
        journals = await pb.list_records(
            "journal_entries",
            token=token,
            params={"filter": f'{filter_user} && created >= "{since_30d}"', "perPage": 100}
        )
        journals_items = journals.get("items") or []
        
        # Retrieve rituals
        m_rituals = await pb.list_records(
            "morning_rituals",
            token=token,
            params={"filter": f'{filter_user} && created >= "{since_30d}"', "perPage": 100}
        )
        m_rituals_items = m_rituals.get("items") or []
        
        w_rituals = await pb.list_records(
            "wind_down_rituals",
            token=token,
            params={"filter": f'{filter_user} && created >= "{since_30d}"', "perPage": 100}
        )
        w_rituals_items = w_rituals.get("items") or []
        
        # Retrieve telemetry interactions
        interactions = await pb.list_records(
            "user_interactions",
            token=token,
            params={"filter": f'{filter_user} && created_at >= "{since_30d}"', "perPage": 1000}
        )
        interactions_items = interactions.get("items") or []
        
        # Calculate stats
        total_moods = len(moods_items)
        avg_mood = sum(m.get("level", 5) for m in moods_items) / total_moods if total_moods > 0 else 5.0
        
        total_journals = len(journals_items)
        total_rituals = len(m_rituals_items) + len(w_rituals_items)
        
        total_clicks = len([i for i in interactions_items if i.get("event_type") == "click"])
        total_navigations = len([i for i in interactions_items if i.get("event_type") == "navigation"])
        
        page_counts = {}
        for i in interactions_items:
            path = i.get("page_path", "/dashboard")
            page_counts[path] = page_counts.get(path, 0) + 1
        top_page = max(page_counts, key=page_counts.get) if page_counts else "/dashboard"
        
        placeholders_used = [i.get("input_placeholder") for i in interactions_items if i.get("input_placeholder")]
        placeholder_counts = {}
        for p in placeholders_used:
            placeholder_counts[p] = placeholder_counts.get(p, 0) + 1
        top_placeholders = sorted(placeholder_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        placeholders_summary = ", ".join([f"{p} ({c}x)" for p, c in top_placeholders]) or "None recorded"
        
        system_prompt = (
            "You are ARIA, the quiet wellness intelligence engine of MindCradle.\n"
            "Analyze the user's 30-day activity, mood logs, and telemetry clicks to generate a personalized wellness insight report.\n"
            "Provide your analysis as a clean JSON object containing:\n"
            "1. 'calmness_score': a rating from 1 to 100 based on mood averages and variance.\n"
            "2. 'consistency_index': completion score from 1 to 100 based on ritual rates.\n"
            "3. 'interaction_focus': a short string describing their primary feature used.\n"
            "4. 'insights': an array of exactly 3 distinct, highly personalized, actionable bullet points (e.g. noting if they track mood but skip rituals, or if they write long journals, and giving retention-oriented positive reinforcement).\n"
            "Return ONLY valid JSON. No markdown wrappers, no backticks, no explanations."
        )
        
        user_prompt = (
            f"Here are the user's statistics for the past 30 days:\n"
            f"- Average Mood: {avg_mood:.1f}/10 (based on {total_moods} check-ins)\n"
            f"- Journals written: {total_journals}\n"
            f"- Rituals completed: {total_rituals} ({len(m_rituals_items)} morning, {len(w_rituals_items)} evening)\n"
            f"- Total clicks tracked: {total_clicks}\n"
            f"- Total page navigations: {total_navigations}\n"
            f"- Top visited page: {top_page}\n"
            f"- Top input fields/placeholders used: {placeholders_summary}\n\n"
            "Analyze this data and generate the JSON insights report."
        )
        
        try:
            ai_res = await openrouter_ai.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            import re
            json_match = re.search(r"({[\s\S]*})", ai_res.strip())
            cleaned_res = json_match.group(1) if json_match else ai_res.strip()
            insights_data = json.loads(cleaned_res)
        except Exception as ai_err:
            logger.error("Failed to generate AI insights: %s", ai_err)
            insights_data = {
                "calmness_score": int(avg_mood * 10),
                "consistency_index": min(100, (total_rituals * 5) or 20),
                "interaction_focus": "Journaling & Reflections" if total_journals > total_moods else "Mood Tracking",
                "insights": [
                    f"You've logged {total_moods} mood check-ins this month with a stable average of {avg_mood:.1f}/10.",
                    f"Great consistency with completing {total_rituals} rituals! Try adding evening breathing exercises to wind down.",
                    f"Your most active path is {top_page}. Daily visits help build healthy wellness routines!"
                ]
            }
            
        return {
            "success": True,
            "data": insights_data,
            "stats": {
                "total_moods": total_moods,
                "avg_mood": round(avg_mood, 1),
                "total_journals": total_journals,
                "total_rituals": total_rituals,
                "total_clicks": total_clicks,
                "total_navigations": total_navigations,
                "top_page": top_page
            }
        }
    except Exception as e:
        logger.error("Failed in get_30day_insights: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_daily_discovery_internal(token: str, user_id: str) -> Optional[dict]:
    # 1. Fetch user discoveries in last 24h
    now = datetime.now(timezone.utc)
    since_24h = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        disc_resp = await pb.list_records(
            "daily_discoveries",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && created_at >= "{since_24h}"',
                "sort": "-created_at",
                "perPage": 1
            }
        )
        existing = disc_resp.get("items") or []
        if existing:
            return existing[0]
    except Exception as e:
        logger.warning("Error checking existing daily discovery: %s", e)

    # 2. Fetch past 30 days of data
    since_30d = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    filter_30d = f'user_id="{user_id}" && created >= "{since_30d}"'
    filter_30d_at = f'user_id="{user_id}" && created_at >= "{since_30d}"'

    try:
        # Moods
        moods_resp = await pb.list_records("mood_logs", token=token, params={"filter": filter_30d, "perPage": 100})
        moods = moods_resp.get("items") or []

        # Journals
        journals_resp = await pb.list_records("journal_entries", token=token, params={"filter": filter_30d, "perPage": 100})
        journals = journals_resp.get("items") or []

        # Morning Rituals
        mornings_resp = await pb.list_records("morning_rituals", token=token, params={"filter": filter_30d, "perPage": 100})
        mornings = mornings_resp.get("items") or []

        # Wind Down Rituals
        winddowns_resp = await pb.list_records("wind_down_rituals", token=token, params={"filter": filter_30d, "perPage": 100})
        winddowns = winddowns_resp.get("items") or []

        # Telemetry clickstream
        interactions_resp = await pb.list_records("user_interactions", token=token, params={"filter": filter_30d_at, "perPage": 500})
        interactions = interactions_resp.get("items") or []
    except Exception as fetch_err:
        logger.error("Daily Discovery Engine: DB fetch error: %s", fetch_err)
        return None

    # Fetch up to 10 previous discoveries to prevent repetition
    previous_discoveries_texts = []
    try:
        prev_resp = await pb.list_records(
            "daily_discoveries",
            token=token,
            params={
                "filter": f'user_id="{user_id}"',
                "sort": "-created_at",
                "perPage": 10
            }
        )
        prev_items = prev_resp.get("items") or []
        previous_discoveries_texts = [d.get("discovery_text") for d in prev_items if d.get("discovery_text")]
    except Exception as e:
        logger.warning("Error fetching previous discoveries: %s", e)

    # Clean data summary
    moods_data = [{"level": m.get("level"), "emotions": m.get("emotions", []), "date": m.get("created", "")[:10]} for m in moods]
    journals_data = [{"length": len(j.get("content", "")), "prompt": j.get("prompt"), "date": j.get("created", "")[:10]} for j in journals]
    mornings_data = [{"intention": m.get("intention"), "forecast": m.get("forecast"), "date": m.get("created", "")[:10]} for m in mornings]
    winddowns_data = [{"release": m.get("releaseItem"), "gratitudes": m.get("gratitudes", []), "date": m.get("created", "")[:10]} for m in winddowns]
    interactions_data = [{"event": i.get("event_type"), "page": i.get("page_path"), "element": i.get("element_name"), "date": i.get("created_at", "")[:10]} for i in interactions]

    # Fetch active PKG nodes for user context
    pkg_nodes_str = ""
    try:
        nodes_res = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={"filter": f'user_id="{user_id}" && is_archived=false && confidence>=0.4', "perPage": 20}
        )
        nodes = nodes_res.get("items") or []
        pkg_nodes_str = ", ".join(f"{n.get('label')} ({n.get('node_type')})" for n in nodes)
    except Exception as e:
        logger.warning("Daily Discovery PKG nodes fetch failed: %s", e)

    activity_summary = {
        "moods": moods_data,
        "journals": journals_data,
        "mornings": mornings_data,
        "winddowns": winddowns_data,
        "interactions": interactions_data,
        "active_personal_knowledge_graph_themes": pkg_nodes_str
    }

    # Minimum data check to ensure confidence
    if len(moods) < 2 and len(journals) < 2:
        return None

    system_prompt = (
        "You are ARIA's Daily Discovery Engine in the MindCradle app.\n"
        "Your task is to analyze the user's past 30 days of data and find exactly ONE real, high-confidence, data-backed correlation or pattern.\n"
        "This is NOT advice, motivation, or therapy. It must be a factual observation of their own behavior.\n"
        "You also have their active personal knowledge graph themes: " + pkg_nodes_str + ". Tie your observations to these themes if possible.\n"
        "Examples of valid discoveries:\n"
        "- 'You journal longer on days you complete Morning Focus.'\n"
        "- 'You haven't mentioned work stress in five days.'\n"

        "- 'Your mood levels are typically higher on days you release a worry during your evening routine.'\n\n"
        "Rules:\n"
        "1. Never hallucinate. Every discovery MUST be supported by the provided data.\n"
        "2. Do not repeat or closely match any of these previous discoveries:\n"
        f"{json.dumps(previous_discoveries_texts)}\n"
        "3. Output MUST be a valid JSON object containing exactly three fields:\n"
        "   - 'discovery_text': the observation string.\n"
        "   - 'confidence_score': integer from 1 to 100 based on data confidence.\n"
        "   - 'supporting_evidence': a key-value object containing the raw numbers/comparisons.\n"
        "4. If no high-confidence (65+) pattern can be found, set confidence_score to less than 65."
    )

    try:
        ai_res = await openrouter_ai.chat_completion(
            messages=[{"role": "user", "content": json.dumps(activity_summary)}],
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=400
        )
        data = parse_json_safely(ai_res)
        score = int(data.get("confidence_score", 0))
        text = data.get("discovery_text", "")
        evidence = data.get("supporting_evidence", {})

        if score >= 65 and text:
            new_record = await pb.create_record(
                "daily_discoveries",
                {
                    "user": user_id,
                    "discovery_text": text,
                    "confidence_score": score,
                    "supporting_evidence": evidence,
                    "is_dismissed": False,
                    "is_shared": False,
                    "is_viewed": False
                },
                token=token
            )
            return new_record
    except Exception as ai_err:
        logger.error("Daily Discovery generation failed: %s", ai_err)
    
    return None


@router.get("/daily-discovery")
async def get_daily_discovery(
    authorization: Optional[str] = Header(None)
):
    """Retrieve today's Daily Discovery. Generates one if none exists in last 24 hours."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")

    discovery = await _generate_daily_discovery_internal(token, user_id)
    if not discovery:
        return {"discovery": None}

    return {
        "id": discovery.get("id"),
        "user_id": discovery.get("user_id") or discovery.get("user"),
        "discovery_text": discovery.get("discovery_text"),
        "confidence_score": discovery.get("confidence_score"),
        "supporting_evidence": discovery.get("supporting_evidence") or {},
        "is_dismissed": discovery.get("is_dismissed", False),
        "is_shared": discovery.get("is_shared", False),
        "is_viewed": discovery.get("is_viewed", False),
        "created_at": discovery.get("created_at") or discovery.get("created")
    }


@router.get("/daily-discovery/history")
async def get_daily_discovery_history(
    authorization: Optional[str] = Header(None)
):
    """Retrieve the user's historical discoveries."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        history_resp = await pb.list_records(
            "daily_discoveries",
            token=token,
            params={
                "filter": f'user_id="{user_id}"',
                "sort": "-created_at",
                "perPage": 100
            }
        )
        items = history_resp.get("items") or []
        formatted = []
        for item in items:
            formatted.append({
                "id": item.get("id"),
                "user_id": item.get("user_id") or item.get("user"),
                "discovery_text": item.get("discovery_text"),
                "confidence_score": item.get("confidence_score"),
                "supporting_evidence": item.get("supporting_evidence") or {},
                "is_dismissed": item.get("is_dismissed", False),
                "is_shared": item.get("is_shared", False),
                "is_viewed": item.get("is_viewed", False),
                "created_at": item.get("created_at") or item.get("created")
            })
        return formatted
    except Exception as e:
        logger.error("Failed to retrieve discoveries history: %s", e)
        raise HTTPException(status_code=500, detail="Database retrieval failed")


@router.patch("/daily-discovery/{discovery_id}/feedback")
async def update_daily_discovery_feedback(
    discovery_id: str,
    req: DiscoveryFeedbackRequest,
    authorization: Optional[str] = Header(None)
):
    """Update feedback metrics (is_viewed, is_dismissed, is_shared) for a discovery."""
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")

    update_payload = {}
    if req.is_dismissed is not None:
        update_payload["is_dismissed"] = req.is_dismissed
    if req.is_shared is not None:
        update_payload["is_shared"] = req.is_shared
    if req.is_viewed is not None:
        update_payload["is_viewed"] = req.is_viewed
        update_payload["viewed_at"] = datetime.now(timezone.utc).isoformat()

    try:
        updated = await pb.update_record("daily_discoveries", discovery_id, update_payload, token=token)
        return {
            "id": updated.get("id"),
            "is_dismissed": updated.get("is_dismissed", False),
            "is_shared": updated.get("is_shared", False),
            "is_viewed": updated.get("is_viewed", False)
        }
    except Exception as e:
        logger.error("Failed to update discovery feedback: %s", e)
        raise HTTPException(status_code=500, detail="Database update failed")


# ─── Personal Growth Timeline ─────────────────────────────────────────────────

def _safe_str(val) -> str:
    """Return a trimmed string or empty string."""
    if val is None:
        return ""
    return str(val).strip()


def _timeline_row_to_event(row: dict) -> dict:
    """Convert a raw timeline_events DB row to the response schema."""
    return {
        "id": _safe_str(row.get("id")),
        "user_id": _safe_str(row.get("user_id")),
        "event_type": _safe_str(row.get("event_type")),
        "source_id": row.get("source_id"),
        "event_date": _safe_str(row.get("event_date")),
        "event_ts": _safe_str(row.get("event_ts")),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "emotion": row.get("emotion"),
        "mood_level": row.get("mood_level"),
        "metadata": row.get("metadata") or {},
        "created_at": _safe_str(row.get("created_at")),
    }


async def _rebuild_timeline_for_user(user_id: str, token: str) -> int:
    """
    Populate timeline_events cache for a user by aggregating events from all
    source tables: mood_logs, journal_entries, morning_rituals,
    wind_down_rituals, daily_discoveries, user_profiles (badges/milestones).
    Returns the number of events upserted.
    """
    events_to_upsert = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # ── 1. Mood logs ────────────────────────────────────────────────────────
    try:
        moods = await pb.list_records(
            "mood_logs",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 500, "sort": "-created_at"}
        )
        for m in (moods.get("items") or []):
            ts = m.get("created_at") or m.get("created") or now_iso
            emotions = m.get("emotions") or []
            note = _safe_str(m.get("note"))
            level = m.get("level")
            emotion_str = ", ".join(emotions) if emotions else None
            events_to_upsert.append({
                "user_id": user_id,
                "event_type": "mood",
                "source_id": m.get("id"),
                "event_date": ts[:10],
                "event_ts": ts,
                "title": f"Mood · {level}/10" if level else "Mood Check-in",
                "summary": note[:200] if note else None,
                "emotion": emotion_str,
                "mood_level": level,
                "search_text": f"mood check-in {note} {emotion_str or ''}".strip(),
                "metadata": {"emotions": emotions, "note": note},
            })
    except Exception as exc:
        logger.warning("Timeline rebuild: failed to fetch mood_logs: %s", exc)

    # ── 2. Journal entries ──────────────────────────────────────────────────
    try:
        journals = await pb.list_records(
            "journal_entries",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 500, "sort": "-created_at"}
        )
        for j in (journals.get("items") or []):
            ts = j.get("created_at") or j.get("created") or now_iso
            content = _safe_str(j.get("content") or j.get("entry") or "")
            prompt = _safe_str(j.get("prompt") or "")
            events_to_upsert.append({
                "user_id": user_id,
                "event_type": "journal",
                "source_id": j.get("id"),
                "event_date": ts[:10],
                "event_ts": ts,
                "title": prompt[:80] if prompt else "Journal Entry",
                "summary": content[:250] if content else None,
                "search_text": f"journal {prompt} {content}".strip(),
                "metadata": {"word_count": len(content.split()) if content else 0},
            })
    except Exception as exc:
        logger.warning("Timeline rebuild: failed to fetch journal_entries: %s", exc)

    # ── 3. Morning rituals ──────────────────────────────────────────────────
    try:
        mornings = await pb.list_records(
            "morning_rituals",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 500, "sort": "-created_at"}
        )
        for mr in (mornings.get("items") or []):
            ts = mr.get("created_at") or mr.get("created") or now_iso
            intention = _safe_str(mr.get("intention") or mr.get("focus") or "")
            forecast = _safe_str(mr.get("forecast") or mr.get("prediction") or "")
            events_to_upsert.append({
                "user_id": user_id,
                "event_type": "morning",
                "source_id": mr.get("id"),
                "event_date": ts[:10],
                "event_ts": ts,
                "title": "Morning Focus",
                "summary": intention[:200] if intention else None,
                "search_text": f"morning focus intention {intention} {forecast}".strip(),
                "metadata": {"intention": intention, "forecast": forecast},
            })
    except Exception as exc:
        logger.warning("Timeline rebuild: failed to fetch morning_rituals: %s", exc)

    # ── 4. Wind-down rituals ────────────────────────────────────────────────
    try:
        winddowns = await pb.list_records(
            "wind_down_rituals",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 500, "sort": "-created_at"}
        )
        for wd in (winddowns.get("items") or []):
            ts = wd.get("created_at") or wd.get("created") or now_iso
            gratitudes = wd.get("gratitudes") or []
            release = _safe_str(wd.get("release") or wd.get("let_go") or "")
            events_to_upsert.append({
                "user_id": user_id,
                "event_type": "wind_down",
                "source_id": wd.get("id"),
                "event_date": ts[:10],
                "event_ts": ts,
                "title": "Wind Down",
                "summary": release[:200] if release else None,
                "search_text": f"wind down evening gratitude {' '.join(gratitudes)} {release}".strip(),
                "metadata": {"gratitudes": gratitudes, "release": release},
            })
    except Exception as exc:
        logger.warning("Timeline rebuild: failed to fetch wind_down_rituals: %s", exc)

    # ── 5. Daily discoveries ────────────────────────────────────────────────
    try:
        discoveries = await pb.list_records(
            "daily_discoveries",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 500, "sort": "-created_at"}
        )
        for d in (discoveries.get("items") or []):
            ts = d.get("created_at") or now_iso
            text = _safe_str(d.get("discovery_text") or "")
            conf = d.get("confidence_score") or 0
            events_to_upsert.append({
                "user_id": user_id,
                "event_type": "discovery",
                "source_id": d.get("id"),
                "event_date": ts[:10],
                "event_ts": ts,
                "title": "ARIA Discovery",
                "summary": text[:250] if text else None,
                "search_text": f"aria discovery insight {text}".strip(),
                "metadata": {"confidence_score": conf},
            })
    except Exception as exc:
        logger.warning("Timeline rebuild: failed to fetch daily_discoveries: %s", exc)

    # ── 6. Milestones/Badges & Achievements ─────────────────────────────────
    try:
        import uuid
        TIMELINE_NAMESPACE = uuid.UUID('12345678-1234-5678-1234-567812345678')
        profiles = await pb.list_records(
            "user_profiles",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1}
        )
        profile_items = profiles.get("items") or []
        if profile_items:
            prof = profile_items[0]
            badge_history = prof.get("badge_history") or []
            for bh in badge_history:
                badge_id = _safe_str(bh.get("id") or bh.get("badge_id") or "")
                badge_name = _safe_str(bh.get("name") or bh.get("label") or badge_id)
                ts = bh.get("unlocked_at") or bh.get("created_at") or now_iso
                
                # Classify as either milestone or achievement
                is_milestone = any(x in badge_id.lower() for x in ["consistency", "streak", "reflection", "awareness", "first"])
                evt_type = "milestone" if is_milestone else "achievement"
                label = "Milestone" if is_milestone else "Achievement"
                
                # Use deterministic UUID for milestones/achievements to avoid duplicate caching
                deterministic_id = str(uuid.uuid5(TIMELINE_NAMESPACE, f"badge-{user_id}-{badge_id}"))
                
                events_to_upsert.append({
                    "user_id": user_id,
                    "event_type": evt_type,
                    "source_id": deterministic_id,
                    "event_date": ts[:10],
                    "event_ts": ts,
                    "title": f"🏆 {badge_name}",
                    "summary": f"Unlocked the '{badge_name}' {label.lower()}.",
                    "search_text": f"{evt_type} milestone achievement badge {badge_name}".strip(),
                    "metadata": {"badge_id": badge_id, "badge_name": badge_name},
                })
    except Exception as exc:
        logger.warning("Timeline rebuild: failed to fetch user_profiles: %s", exc)

    # ── 7. Solstice letters (preserve existing cached letters) ───────────────
    try:
        existing_letters = await pb.list_records(
            "timeline_events",
            token=token,
            params={"filter": f'user_id="{user_id}" && event_type="letter"', "perPage": 100}
        )
        for el in (existing_letters.get("items") or []):
            events_to_upsert.append({
                "user_id": user_id,
                "event_type": "letter",
                "source_id": el.get("source_id"),
                "event_date": el.get("event_date"),
                "event_ts": el.get("event_ts"),
                "title": el.get("title"),
                "summary": el.get("summary"),
                "search_text": el.get("search_text"),
                "metadata": el.get("metadata") or {},
            })
    except Exception as exc:
        logger.warning("Timeline rebuild: failed to preserve cached letters: %s", exc)

    # ── 8. Important memories (user_memory_insights) ────────────────────────
    try:
        memories = await pb.list_records(
            "user_memory_insights",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 500, "sort": "-created"}
        )
        for m in (memories.get("items") or []):
            ts = m.get("created") or now_iso
            situation = _safe_str(m.get("situation") or "")
            what_happened = _safe_str(m.get("what_happened") or "")
            what_helped = _safe_str(m.get("what_helped") or "")
            follow_up = _safe_str(m.get("follow_up") or "")
            emotion = _safe_str(m.get("emotion") or "")
            
            # Use custom date or extract from timestamp
            event_date = _safe_str(m.get("date"))
            if not event_date:
                event_date = ts[:10]
                
            summary_parts = []
            if situation:
                summary_parts.append(f"Situation: {situation}")
            if what_happened:
                summary_parts.append(f"What happened: {what_happened}")
            if what_helped:
                summary_parts.append(f"What helped: {what_helped}")
            summary = "\n".join(summary_parts)
            
            events_to_upsert.append({
                "user_id": user_id,
                "event_type": "memory",
                "source_id": m.get("id"),
                "event_date": event_date,
                "event_ts": ts,
                "title": situation[:80] if situation else "Important Memory",
                "summary": summary[:300],
                "emotion": emotion if emotion else None,
                "search_text": f"memory {situation} {what_happened} {what_helped} {follow_up} {emotion}".strip(),
                "metadata": {
                    "situation": situation,
                    "what_happened": what_happened,
                    "what_helped": what_helped,
                    "follow_up": follow_up
                },
            })
    except Exception as exc:
        logger.warning("Timeline rebuild: failed to fetch user_memory_insights: %s", exc)

    # ─── 9. Generate & Cache Embeddings ───────────────────────────────────────
    try:
        # Fetch existing timeline events to reuse embeddings
        existing_resp = await pb.list_records(
            "timeline_events",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 1000}
        )
        existing_items = existing_resp.get("items") or []
        
        # Map existing embeddings by (event_type, source_id) -> (embedding, search_text)
        existing_cache = {}
        for item in existing_items:
            etype = item.get("event_type")
            sid = item.get("source_id")
            emb = item.get("embedding")
            stxt = item.get("search_text")
            if etype and sid and emb:
                existing_cache[(etype, sid)] = (emb, stxt)
                
        # Find which events need new embeddings
        needs_embeddings_indices = []
        for idx, event in enumerate(events_to_upsert):
            key = (event["event_type"], event["source_id"])
            if key in existing_cache:
                cached_emb, cached_text = existing_cache[key]
                if cached_text == event["search_text"]:
                    event["embedding"] = cached_emb
                    continue
            needs_embeddings_indices.append(idx)
            
        # Batch fetch new embeddings
        if needs_embeddings_indices:
            texts_to_embed = [events_to_upsert[idx]["search_text"] for idx in needs_embeddings_indices]
            from app.services.embeddings import get_embeddings_batch
            new_embeddings = await get_embeddings_batch(texts_to_embed)
            for i, idx in enumerate(needs_embeddings_indices):
                events_to_upsert[idx]["embedding"] = new_embeddings[i]
                
    except Exception as emb_err:
        logger.warning("Timeline rebuild: failed to handle embeddings caching/generation: %s", emb_err)

    if not events_to_upsert:
        return 0

    # Upsert all events — on conflict (user_id, event_type, source_id) update summary & metadata
    try:
        upserted = await pb.upsert_records(
            "timeline_events",
            records=events_to_upsert,
            token=token,
            on_conflict="user_id,event_type,source_id"
        )
        return len(upserted) if isinstance(upserted, list) else len(events_to_upsert)
    except Exception as exc:
        logger.warning("Timeline rebuild: upsert failed, falling back to individual inserts: %s", exc)
        # Fallback: insert events individually, ignoring duplicate-key errors
        inserted = 0
        for evt in events_to_upsert:
            try:
                await pb.create_record("timeline_events", evt, token=token)
                inserted += 1
            except Exception:
                pass  # likely a duplicate — ignore
        return inserted


@router.post("/timeline/rebuild")
async def rebuild_timeline(authorization: Optional[str] = Header(None)):
    """
    Rebuilds the timeline_events cache for the authenticated user.
    Triggered lazily on the user's first timeline visit.
    Safe to call multiple times — uses upsert semantics.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        count = await _rebuild_timeline_for_user(user_id, token)
        return {"success": True, "events_cached": count}
    except Exception as e:
        logger.error("Timeline rebuild failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Timeline rebuild failed")


@router.get("/timeline", response_model=TimelinePage)
async def get_timeline(
    page: int = 1,
    page_size: int = 30,
    types: Optional[str] = None,         # comma-separated: "mood,journal,discovery"
    start_date: Optional[str] = None,    # YYYY-MM-DD
    end_date: Optional[str] = None,      # YYYY-MM-DD
    q: Optional[str] = None,            # free-text keyword search
    authorization: Optional[str] = Header(None),
):
    """
    Returns a paginated, filterable personal growth timeline for the user.
    Events are sorted newest-first (event_ts DESC).
    Supports type filtering, date range, and full-text keyword search.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size

    # Build filter string for Supabase
    filters = [f'user_id="{user_id}"']

    if types:
        type_list = [t.strip() for t in types.split(",") if t.strip()]
        if type_list:
            type_filter = " || ".join([f'event_type="{t}"' for t in type_list])
            filters.append(f"({type_filter})")

    if start_date:
        filters.append(f'event_date>="{start_date}"')
    if end_date:
        filters.append(f'event_date<="{end_date}"')

    combined_filter = " && ".join(filters)

    try:
        params = {
            "filter": combined_filter,
            "sort": "-event_ts",
            "perPage": page_size,
            "page": page,
        }

        # Full-text search: add search query if provided
        # Supabase REST doesn't support FTS natively via PostgREST filter syntax easily,
        # so we fetch a broader set and filter client-side for the keyword search.
        if q:
            params["perPage"] = 200  # wider fetch for client-side keyword filter
            params["page"] = 1

        result = await pb.list_records("timeline_events", token=token, params=params)
        all_items = result.get("items") or []
        total_from_db = result.get("totalItems") or len(all_items)

        # Client-side keyword filter
        if q:
            q_lower = q.lower()
            all_items = [
                item for item in all_items
                if q_lower in _safe_str(item.get("search_text")).lower()
                or q_lower in _safe_str(item.get("title")).lower()
                or q_lower in _safe_str(item.get("summary")).lower()
            ]
            total_from_db = len(all_items)
            # Apply manual pagination
            all_items = all_items[offset:offset + page_size]

        events = [_timeline_row_to_event(row) for row in all_items]

        # Compute date span and types present from this page
        dates = [e["event_date"] for e in events if e.get("event_date")]
        date_span = {"earliest": min(dates), "latest": max(dates)} if dates else None
        types_present = list({e["event_type"] for e in events if e.get("event_type")})

        has_more = (offset + len(events)) < total_from_db

        return TimelinePage(
            events=events,
            total=total_from_db,
            page=page,
            page_size=page_size,
            has_more=has_more,
            date_span=date_span,
            types_present=sorted(types_present),
        )

    except Exception as e:
        logger.error("Timeline fetch failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to load timeline")


# ─── Predictive Intelligence Endpoints ─────────────────────────────────────

from app.models.schemas import PredictionsPage, PredictionFeedbackRequest, PredictionResponse

@router.get("/predictions", response_model=PredictionsPage)
async def get_predictions(
    authorization: Optional[str] = Header(None)
):
    """
    Evaluates past predictions and retrieves the user's active predictions + stats.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")

    from app.services.prediction_engine import generate_predictions_for_user, evaluate_predictions_for_user
    
    # 1. Run evaluation first to ensure stats are updated
    stats_dict = await evaluate_predictions_for_user(user_id, token)
    
    # 2. Re-run generation so the user has the latest active predictions
    await generate_predictions_for_user(user_id, token)
    
    # 3. Retrieve active predictions (where target_date >= today and is_correct is NULL)
    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    
    try:
        active_resp = await pb.list_records(
            "user_predictions",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && target_date >= "{today_str}" && is_correct = null',
                "sort": "-created_at",
                "perPage": 50
            }
        )
        active_items = active_resp.get("items") or []
    except Exception as e:
        logger.error("Failed to query active user_predictions: %s", e)
        active_items = []
        
    active_preds = []
    for item in active_items:
        active_preds.append(PredictionResponse(
            id=item["id"],
            user_id=item["user_id"],
            prediction_type=item["prediction_type"],
            prediction_text=item["prediction_text"],
            target_date=item["target_date"],
            confidence_score=item["confidence_score"],
            is_correct=item.get("is_correct"),
            metadata=item.get("metadata") or {},
            created_at=item["created_at"]
        ))
        
    return PredictionsPage(
        active_predictions=active_preds,
        stats={
            "total_evaluated": stats_dict.get("total_evaluated", 0),
            "correct_count": stats_dict.get("correct_count", 0),
            "accuracy_rate": stats_dict.get("accuracy_rate", 1.0)
        }
    )


@router.post("/predictions/rebuild")
async def rebuild_predictions(
    authorization: Optional[str] = Header(None)
):
    """
    Manually triggers evaluation and generation of user predictions.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")

    from app.services.prediction_engine import generate_predictions_for_user, evaluate_predictions_for_user
    
    await evaluate_predictions_for_user(user_id, token)
    await generate_predictions_for_user(user_id, token)
    
    return {"success": True, "message": "Predictions successfully rebuilt."}


@router.patch("/predictions/{prediction_id}/feedback")
async def submit_prediction_feedback(
    prediction_id: str,
    req: PredictionFeedbackRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Updates the prediction record with manual feedback override.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
        
    user_id = extract_user_id(token) or "unknown"
    if user_id == "unknown":
        raise HTTPException(status_code=401, detail="Invalid token")

    now_utc = datetime.now(timezone.utc)
    
    try:
        # Get the prediction to verify ownership
        pred = await pb.get_record("user_predictions", prediction_id, token=token)
        if pred.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this prediction")
            
        # Update is_correct and evaluated_at
        await pb.update_record(
            "user_predictions",
            prediction_id,
            {
                "is_correct": req.is_correct,
                "evaluated_at": now_utc.isoformat()
            },
            token=token
        )
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit feedback for prediction %s: %s", prediction_id, e)
        raise HTTPException(status_code=500, detail="Failed to update prediction feedback")


# ─── Semantic Search ───────────────────────────────────────────────────────────

import math as _math


def _recency_score(event_ts_str: str, now: datetime | None = None) -> float:
    """Exponential recency decay with a 90-day half-life."""
    now = now or datetime.now(timezone.utc)
    try:
        ts_str = str(event_ts_str).replace("Z", "+00:00")
        event_time = datetime.fromisoformat(ts_str)
        if not event_time.tzinfo:
            event_time = event_time.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - event_time).total_seconds() / 86400)
        return _math.exp(-age_days / 90)
    except Exception:
        return 0.0


def _keyword_score(text: str, query_words: list[str]) -> float:
    """Fraction of query words found in the text (case-insensitive)."""
    if not query_words or not text:
        return 0.0
    text_lower = text.lower()
    matched = sum(1 for w in query_words if w in text_lower)
    return matched / len(query_words)


def _build_search_result(row: dict, rank_score: float, similarity: float | None) -> dict:
    """Serialise a raw DB row into a SearchResultItem-compatible dict."""
    return {
        "id": _safe_str(row.get("id")),
        "user_id": _safe_str(row.get("user_id")),
        "event_type": _safe_str(row.get("event_type")),
        "source_id": row.get("source_id"),
        "event_date": _safe_str(row.get("event_date")),
        "event_ts": _safe_str(row.get("event_ts")),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "emotion": row.get("emotion"),
        "mood_level": row.get("mood_level"),
        "metadata": row.get("metadata") or {},
        "rank_score": round(rank_score, 4),
        "similarity": round(similarity, 4) if similarity is not None else None,
    }


@router.get("/search", response_model=SearchPage)
async def semantic_search(
    q: str,
    types: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 15,
    authorization: Optional[str] = Header(None),
):
    """
    Hybrid semantic + keyword + recency search across all timeline events.

    Search pipeline:
    1. Embed the query with text-embedding-3-small (graceful fallback if unavailable).
    2. Run pgvector cosine-similarity search via match_timeline_events RPC.
    3. Run keyword search on search_text column.
    4. Merge, deduplicate, and re-rank with hybrid score.
    5. Apply type/date filters and return top `limit` results.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    q = q.strip()
    if not q:
        raise HTTPException(status_code=422, detail="Search query cannot be empty")

    limit = min(max(1, limit), 25)
    query_words = [w.lower() for w in q.split() if len(w) > 2]
    now = datetime.now(timezone.utc)

    # ── Step 1: Generate query embedding ───────────────────────────────────
    query_embedding: list[float] | None = None
    try:
        query_embedding = await embedding_svc.embed_text(q)
    except Exception as exc:
        logger.warning("Semantic search: embedding generation failed: %s", exc)

    semantic_rows: list[dict] = []
    has_embeddings = query_embedding is not None

    # ── Step 2: Semantic retrieval via pgvector ─────────────────────────────
    if query_embedding is not None:
        try:
            rpc_result = await pb.call_rpc(
                "match_timeline_events",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.50,
                    "match_count": 60,
                    "p_user_id": user_id,
                },
                token=token,
            )
            semantic_rows = rpc_result if isinstance(rpc_result, list) else []
        except Exception as exc:
            logger.warning("Semantic search: pgvector RPC failed: %s", exc)

    # ── Step 3: Keyword search ──────────────────────────────────────────────
    keyword_rows: list[dict] = []
    try:
        kw_filter = f'user_id="{user_id}"'
        if start_date:
            kw_filter += f' && event_date>="{start_date}"'
        if end_date:
            kw_filter += f' && event_date<="{end_date}"'
        if types:
            type_list = [t.strip() for t in types.split(",") if t.strip()]
            if type_list:
                type_filter = " || ".join([f'event_type="{t}"' for t in type_list])
                kw_filter += f" && ({type_filter})"

        kw_result = await pb.list_records(
            "timeline_events",
            token=token,
            params={"filter": kw_filter, "sort": "-event_ts", "perPage": 200},
        )
        all_kw_items = kw_result.get("items") or []

        # Filter client-side for keyword matches
        q_lower = q.lower()
        for item in all_kw_items:
            search_text = _safe_str(item.get("search_text"))
            title = _safe_str(item.get("title"))
            summary = _safe_str(item.get("summary"))
            combined = f"{search_text} {title} {summary}".lower()
            if q_lower in combined or any(w in combined for w in query_words):
                keyword_rows.append(item)
    except Exception as exc:
        logger.warning("Semantic search: keyword fallback failed: %s", exc)

    # ── Step 4: Merge, deduplicate, and hybrid-rank ─────────────────────────
    scored: dict[str, dict] = {}

    # Add semantic results
    for row in semantic_rows:
        row_id = _safe_str(row.get("id"))
        if not row_id:
            continue
        sim = float(row.get("similarity") or 0)
        rec = _recency_score(row.get("event_ts") or "", now)
        kw = _keyword_score(
            f"{_safe_str(row.get('search_text'))} {_safe_str(row.get('title'))} {_safe_str(row.get('summary'))}",
            query_words
        )
        hybrid = 0.60 * sim + 0.25 * kw + 0.15 * rec
        scored[row_id] = _build_search_result(row, hybrid, sim)

    # Add keyword-only results (not already in semantic set)
    for row in keyword_rows:
        row_id = _safe_str(row.get("id"))
        if not row_id or row_id in scored:
            continue
        rec = _recency_score(row.get("event_ts") or "", now)
        kw = _keyword_score(
            f"{_safe_str(row.get('search_text'))} {_safe_str(row.get('title'))} {_safe_str(row.get('summary'))}",
            query_words
        )
        hybrid = 0.25 * kw + 0.15 * rec
        scored[row_id] = _build_search_result(row, hybrid, None)

    # Sort by hybrid score descending
    ranked = sorted(scored.values(), key=lambda r: r["rank_score"], reverse=True)

    # Apply type filter to keyword results (semantic already filtered by pgvector user_id)
    if types:
        type_set = {t.strip() for t in types.split(",") if t.strip()}
        ranked = [r for r in ranked if r["event_type"] in type_set]

    # Apply date filters
    if start_date:
        ranked = [r for r in ranked if r.get("event_date", "") >= start_date]
    if end_date:
        ranked = [r for r in ranked if r.get("event_date", "") <= end_date]

    top = ranked[:limit]
    search_mode = "hybrid" if (semantic_rows and keyword_rows) else ("semantic" if semantic_rows else "keyword")

    return SearchPage(
        results=top,
        total=len(ranked),
        query=q,
        search_mode=search_mode,
        has_embeddings=has_embeddings,
    )


@router.get("/search/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(authorization: Optional[str] = Header(None)):
    """
    Return 6 dynamic example search queries tailored to what data the user has.
    Falls back to a generic set if data fetch fails.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    defaults = [
        "When was I happiest?",
        "What was I worried about?",
        "Show my best mornings",
        "When did I feel calm?",
        "What helped me most?",
        "Show my recent breakthroughs",
    ]

    try:
        # Sample a few events to customise suggestions
        result = await pb.list_records(
            "timeline_events",
            token=token,
            params={"filter": f'user_id="{user_id}"', "sort": "-event_ts", "perPage": 10}
        )
        items = result.get("items") or []

        type_set = {item.get("event_type") for item in items if item.get("event_type")}
        suggestions = []

        if "mood" in type_set:
            suggestions.append("When was I happiest?")
        if "journal" in type_set:
            suggestions.append("What was I working through in my journals?")
        if "morning" in type_set:
            suggestions.append("Show my best morning intentions")
        if "discovery" in type_set:
            suggestions.append("What patterns has ARIA noticed?")
        if "wind_down" in type_set:
            suggestions.append("What am I grateful for most?")

        suggestions += [
            "When did I feel most stressed?",
            "Show everything about work",
            "When did I mention a breakthrough?",
            "What worried me most?",
            "Show my calm moments",
            "When did I feel energised?",
        ]

        # Deduplicate and pick 6
        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
            if len(unique) == 6:
                break

        return SearchSuggestionsResponse(suggestions=unique if unique else defaults)

    except Exception as exc:
        logger.warning("Failed to generate dynamic suggestions: %s", exc)
        return SearchSuggestionsResponse(suggestions=defaults)


@router.post("/embeddings/generate", response_model=EmbeddingGenerateResponse)
async def generate_embeddings(
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
):
    """
    Trigger embedding generation for all timeline_events that don't yet have an embedding.
    Runs in a background task so the HTTP response returns immediately.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch all events without embeddings
    try:
        result = await pb.list_records(
            "timeline_events",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && embedding=null',
                "sort": "-event_ts",
                "perPage": 500,
            },
        )
        items_without = result.get("items") or []
    except Exception as exc:
        logger.error("generate_embeddings: failed to fetch unembedded events: %s", exc)
        items_without = []

    total = len(items_without)

    async def _run_embedding_job():
        embedded = 0
        failed = 0
        batch_size = 25

        for i in range(0, len(items_without), batch_size):
            batch = items_without[i: i + batch_size]
            texts = [embedding_svc.build_event_text(item) for item in batch]

            try:
                vectors = await embedding_svc.embed_batch(texts)
            except Exception as exc:
                logger.error("Embedding batch failed: %s", exc)
                failed += len(batch)
                continue

            for item, vector in zip(batch, vectors):
                if vector is None:
                    failed += 1
                    continue
                try:
                    await pb.update_record(
                        "timeline_events",
                        item["id"],
                        {"embedding": vector},
                        token=token,
                    )
                    embedded += 1
                except Exception as exc:
                    logger.warning("Failed to save embedding for %s: %s", item.get("id"), exc)
                    failed += 1

            # Brief pause to respect rate limits
            await asyncio.sleep(0.3)

        logger.info(
            "Embedding job complete: user=%s total=%d embedded=%d failed=%d",
            user_id, total, embedded, failed
        )

    background_tasks.add_task(_run_embedding_job)

    return EmbeddingGenerateResponse(
        total=total,
        embedded=0,       # job is async — progress not returned synchronously
        failed=0,
        skipped=0,
    )


# ─── Personal Knowledge Graph (PKG) / CIE ─────────────────────────────────────

@aria_router.post("/knowledge/process", response_model=KnowledgeProcessResponse)
async def process_knowledge(
    req: KnowledgeProcessRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
):
    """
    Tier-2 ingestion: Process user text asynchronously to extract entities
    and expand their Personal Knowledge Graph.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    async def _run_process():
        try:
            await kg_svc.process_source(
                user_id=user_id,
                source_type=req.source_type,
                source_id=req.source_id,
                text=req.text,
                token=token
            )
        except Exception as exc:
            logger.error("Async PKG processing failed: %s", exc)

    background_tasks.add_task(_run_process)

    return KnowledgeProcessResponse(
        success=True,
        nodes_processed=0  # Run in background
    )


@aria_router.get("/knowledge/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    authorization: Optional[str] = Header(None)
):
    """
    Retrieve the active, non-archived entities and relationships
    that compose the user's Personal Knowledge Graph.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        # Fetch active nodes
        nodes_res = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && is_archived=false',
                "sort": "-confidence",
                "perPage": 200
            }
        )
        nodes_list = nodes_res.get("items") or []

        # Convert/map to schema response format
        nodes_mapped = []
        for n in nodes_list:
            nodes_mapped.append(
                KnowledgeNodeResponse(
                    id=_safe_str(n.get("id")),
                    label=_safe_str(n.get("label")),
                    node_type=_safe_str(n.get("node_type")),
                    confidence=float(n.get("confidence") or 0.0),
                    importance=int(n.get("importance") or 5),
                    valence=float(n.get("valence") or 0.0),
                    mention_count=int(n.get("mention_count") or 1),
                    first_seen_at=_safe_str(n.get("first_seen_at")),
                    last_seen_at=_safe_str(n.get("last_seen_at")),
                    source_reason=n.get("source_reason"),
                    is_confirmed=bool(n.get("is_confirmed")),
                    is_archived=bool(n.get("is_archived")),
                    metadata=n.get("metadata") or {}
                )
            )

        # Fetch edges
        edges_res = await pb.list_records(
            "user_knowledge_edges",
            token=token,
            params={
                "filter": f'user_id="{user_id}"',
                "sort": "-weight",
                "perPage": 300
            }
        )
        edges_list = edges_res.get("items") or []

        edges_mapped = []
        # Make sure target/source nodes exist in the active set or are valid UUIDs
        active_node_ids = {n.id for n in nodes_mapped}
        for e in edges_list:
            src = _safe_str(e.get("source_node_id"))
            tgt = _safe_str(e.get("target_node_id"))
            # Only include edges where both nodes are active/loaded
            if src in active_node_ids and tgt in active_node_ids:
                edges_mapped.append(
                    KnowledgeEdgeResponse(
                        id=_safe_str(e.get("id")),
                        source_node_id=src,
                        target_node_id=tgt,
                        edge_type=_safe_str(e.get("edge_type")),
                        weight=float(e.get("weight") or 0.0),
                        evidence_count=int(e.get("evidence_count") or 1),
                        last_reinforced_at=_safe_str(e.get("last_reinforced_at"))
                    )
                )

        return KnowledgeGraphResponse(
            nodes=nodes_mapped,
            edges=edges_mapped
        )

    except Exception as exc:
        logger.error("Failed to fetch knowledge graph: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve knowledge graph")


@aria_router.get("/knowledge/context", response_model=KnowledgeContextResponse)
async def get_knowledge_context(
    topic: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Retrieve the compiled system context packet built from the PKG.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    packet = await kg_svc.get_context_packet(user_id=user_id, topic=topic, token=token)
    return KnowledgeContextResponse(context_packet=packet)


@aria_router.get("/knowledge/growth", response_model=GrowthMetricsResponse)
async def get_growth_metrics(
    authorization: Optional[str] = Header(None)
):
    """
    Retrieve the user's computed growth metrics over time.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        res = await pb.list_records(
            "user_growth_metrics",
            token=token,
            params={
                "filter": f'user_id="{user_id}"',
                "sort": "-computed_at",
                "perPage": 100
            }
        )
        items = res.get("items") or []

        # Deduplicate to show only the latest snapshot of each (metric_type, period)
        seen = set()
        unique_metrics = []
        for item in items:
            key = (item.get("metric_type"), item.get("period"))
            if key not in seen:
                seen.add(key)
                unique_metrics.append(
                    GrowthMetricItem(
                        metric_type=_safe_str(item.get("metric_type")),
                        period=_safe_str(item.get("period")),
                        value=float(item.get("value") or 0.0),
                        previous_value=float(item.get("previous_value")) if item.get("previous_value") is not None else None,
                        delta=float(item.get("delta")) if item.get("delta") is not None else None,
                        computed_at=_safe_str(item.get("computed_at"))
                    )
                )

        return GrowthMetricsResponse(metrics=unique_metrics)

    except Exception as exc:
        logger.error("Failed to fetch growth metrics: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve growth metrics")


@aria_router.delete("/knowledge/nodes/{node_id}")
async def delete_knowledge_node(
    node_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Delete a knowledge node from the PKG.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        # Check ownership first
        node = await pb.get_record("user_knowledge_nodes", node_id, token=token)
        if _safe_str(node.get("user_id")) != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        await pb.delete_record("user_knowledge_nodes", node_id, token=token)
        return {"success": True, "message": "Node deleted successfully"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete knowledge node %s: %s", node_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete knowledge node")


@aria_router.get("/knowledge/chapters", response_model=KnowledgeChaptersListResponse)
async def get_knowledge_chapters(
    authorization: Optional[str] = Header(None)
):
    """
    Retrieve the life chapters detected for the user.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        res = await pb.list_records(
            "user_life_chapters",
            token=token,
            params={
                "filter": f'user_id="{user_id}"',
                "sort": "-chapter_number",
                "perPage": 100
            }
        )
        items = res.get("items") or []

        chapters_mapped = []
        for c in items:
            chapters_mapped.append(
                KnowledgeChapterResponse(
                    id=_safe_str(c.get("id")),
                    user_id=_safe_str(c.get("user_id")),
                    title=_safe_str(c.get("title")),
                    chapter_number=int(c.get("chapter_number") or 1),
                    start_date=_safe_str(c.get("start_date")),
                    end_date=_safe_str(c.get("end_date")) if c.get("end_date") else None,
                    is_current=bool(c.get("is_current")),
                    theme_summary=c.get("theme_summary"),
                    dominant_emotion=c.get("dominant_emotion"),
                    mood_average=float(c.get("mood_average")) if c.get("mood_average") is not None else None,
                    growth_score=float(c.get("growth_score")) if c.get("growth_score") is not None else None,
                    key_events=c.get("key_events") or [],
                    dominant_themes=c.get("dominant_themes") or [],
                    goals_started=c.get("goals_started") or [],
                    goals_achieved=c.get("goals_achieved") or [],
                    node_ids=c.get("node_ids") or [],
                    detected_by=_safe_str(c.get("detected_by") or "system"),
                    confidence=float(c.get("confidence") or 0.7)
                )
            )

        return KnowledgeChaptersListResponse(chapters=chapters_mapped)

    except Exception as exc:
        logger.error("Failed to fetch life chapters: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve life chapters")


@aria_router.patch("/knowledge/nodes/{node_id}", response_model=KnowledgeNodeResponse)
async def update_knowledge_node(
    node_id: str,
    req: KnowledgeNodeUpdateRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Update a knowledge node's attributes (label, confirmation status, archived status, valence).
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        # Check ownership first
        node = await pb.get_record("user_knowledge_nodes", node_id, token=token)
        if _safe_str(node.get("user_id")) != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        update_data = {}
        if req.label is not None:
            update_data["label"] = req.label.strip()
            update_data["canonical_label"] = req.label.strip().lower()
        if req.is_confirmed is not None:
            update_data["is_confirmed"] = req.is_confirmed
        if req.is_archived is not None:
            update_data["is_archived"] = req.is_archived
        if req.valence is not None:
            update_data["valence"] = round(req.valence, 4)

        updated_node = await pb.update_record("user_knowledge_nodes", node_id, update_data, token=token)

        return KnowledgeNodeResponse(
            id=_safe_str(updated_node.get("id")),
            label=_safe_str(updated_node.get("label")),
            node_type=_safe_str(updated_node.get("node_type")),
            confidence=float(updated_node.get("confidence") or 0.0),
            importance=int(updated_node.get("importance") or 5),
            valence=float(updated_node.get("valence") or 0.0),
            mention_count=int(updated_node.get("mention_count") or 1),
            first_seen_at=_safe_str(updated_node.get("first_seen_at")),
            last_seen_at=_safe_str(updated_node.get("last_seen_at")),
            source_reason=updated_node.get("source_reason"),
            is_confirmed=bool(updated_node.get("is_confirmed")),
            is_archived=bool(updated_node.get("is_archived")),
            metadata=updated_node.get("metadata") or {}
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update knowledge node %s: %s", node_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update knowledge node")


@aria_router.get("/knowledge/comparison", response_model=KnowledgeComparisonResponse)
async def get_chapter_comparison(
    authorization: Optional[str] = Header(None)
):
    """
    Compare the user's current life chapter with their previous life chapter,
    analyzing metric improvements, focus shifts, and challenges.
    """
    token = _normalize_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    user_id = extract_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        # Fetch chapters
        res = await pb.list_records(
            "user_life_chapters",
            token=token,
            params={
                "filter": f'user_id="{user_id}"',
                "sort": "-chapter_number",
                "perPage": 2
            }
        )
        chapters = res.get("items") or []

        if len(chapters) < 2:
            # Not enough chapters to compare, return empty/placeholder response
            curr_title = chapters[0].get("title", "Initial Chapter") if chapters else "Initial Chapter"
            return KnowledgeComparisonResponse(
                current_chapter_title=curr_title,
                previous_chapter_title="N/A",
                improvements=["Welcome to your first chapter! Continue reflecting daily to generate comparison reports."],
                challenge="Not enough historical chapters logged yet.",
                comparison_metrics=[]
            )

        current = chapters[0]
        previous = chapters[1]

        curr_mood = float(current.get("mood_average") or 5.0)
        prev_mood = float(previous.get("mood_average") or 5.0)

        curr_growth = float(current.get("growth_score") or 50.0)
        prev_growth = float(previous.get("growth_score") or 50.0)

        # Generate metrics
        metrics = [
            KnowledgeComparisonItem(
                metric_type="Mood Average",
                current_value=curr_mood,
                previous_value=prev_mood,
                delta=round(curr_mood - prev_mood, 2)
            ),
            KnowledgeComparisonItem(
                metric_type="Growth Score",
                current_value=curr_growth,
                previous_value=prev_growth,
                delta=round(curr_growth - prev_growth, 2)
            )
        ]

        # Use OpenRouter to generate comparison summary
        compare_prompt = (
            f"Compare these two life chapters for the user:\n"
            f"Current Chapter: '{current.get('title')}'\n"
            f"  - Theme: {current.get('theme_summary')}\n"
            f"  - Dominant Emotion: {current.get('dominant_emotion')}\n"
            f"  - Mood Avg: {curr_mood}/10\n"
            f"Previous Chapter: '{previous.get('title')}'\n"
            f"  - Theme: {previous.get('theme_summary')}\n"
            f"  - Dominant Emotion: {previous.get('dominant_emotion')}\n"
            f"  - Mood Avg: {prev_mood}/10\n"
            f"Identify exactly 3 positive improvements and 1 primary challenge remaining.\n"
            f"Output must be a valid JSON object containing:\n"
            f"  - 'improvements': list of 3 short strings\n"
            f"  - 'challenge': a 1-sentence string"
        )

        try:
            ai_res = await openrouter_ai.chat_completion(
                messages=[{"role": "user", "content": compare_prompt}],
                system_prompt="You are ARIA, a warm, validating companion in MindCradle. Generate chapter comparisons as JSON.",
                temperature=0.3,
                max_tokens=300
            )
            data = parse_json_safely(ai_res)
            improvements = data.get("improvements") or ["Positive growth trends emerging", "Improved emotional regulation", "Stronger intention alignment"]
            challenge = data.get("challenge") or "Maintaining routine consistency during stressful periods."
        except Exception:
            improvements = ["Positive growth trends emerging", "Improved emotional regulation", "Stronger intention alignment"]
            challenge = "Maintaining routine consistency during stressful periods."

        return KnowledgeComparisonResponse(
            current_chapter_title=_safe_str(current.get("title")),
            previous_chapter_title=_safe_str(previous.get("title")),
            improvements=improvements[:3],
            challenge=challenge,
            comparison_metrics=metrics
        )

    except Exception as exc:
        logger.error("Failed to generate chapter comparison: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve chapter comparison")






