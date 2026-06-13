from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# --- Auth ---
class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    password_confirm: str = Field(alias="passwordConfirm")
    name: str


class AuthResponse(BaseModel):
    token: str
    refresh_token: str = ""
    user_id: str
    name: str
    email: str


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Resources ---
class ResourceCategory(str, Enum):
    CRISIS = "crisis"
    MINDFULNESS = "mindfulness"
    THERAPY = "therapy"
    SELF_CARE = "self-care"
    PHYSICAL = "physical"
    CREATIVE = "creative"
    TOOLS = "tools"


class ResourceOut(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    color_class: str
    category: str
    order: int
    url: Optional[str] = None


# --- Mood ---
class MoodCreate(BaseModel):
    level: int = Field(ge=1, le=10)
    emotions: list[str] = []
    note: str = ""


class MoodOut(BaseModel):
    id: str
    level: int
    emotions: list[str]
    note: str
    created: str


# --- Journal ---
class JournalCreate(BaseModel):
    prompt: str
    content: str
    ai_reflection: Optional[str] = None


class JournalOut(BaseModel):
    id: str
    prompt: str
    content: str
    ai_reflection: Optional[str] = None
    created: str


# --- Rituals ---
class MorningRitualCreate(BaseModel):
    forecast: str
    intention: str
    activity_type: str = Field(alias="activityType")
    completed_at: str = Field(alias="completedAt")


class WindDownRitualCreate(BaseModel):
    release_item: str = Field(alias="releaseItem")
    gratitudes: list[str]
    audio_choice: str = Field(alias="audioChoice")
    timer: str


class ProfileMilestonesUpdate(BaseModel):
    unlocked_badges: list[str] = Field(alias="unlockedBadges")


# --- AI ---
class AIRecommendRequest(BaseModel):
    context: str = ""


class AIChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    response_type: Optional[str] = None
    context_data: Optional[dict] = None


class AIChatResponse(BaseModel):
    reply: str
    conversation_id: str
    crisis_detected: Optional[bool] = None
    crisis_severity: Optional[int] = None


class JournalReflectionRequest(BaseModel):
    journal_content: str
    user_id: str


class JournalReflectionResponse(BaseModel):
    reflection: str
    themes: list[str]
    emotional_tone: str


class MoodAnalysisRequest(BaseModel):
    mood_data: list[dict]
    user_id: str


class MoodAnalysisResponse(BaseModel):
    analysis: str
    pattern: str
    suggestion: str
    mood_trend: str


class RememberContextRequest(BaseModel):
    conversation_id: str
    user_id: str
    key_insight: str
    emotion: str
    context_type: str


class MemoryInsightUpdate(BaseModel):
    situation: Optional[str] = None
    emotion: Optional[str] = None
    what_helped: Optional[str] = None
    follow_up: Optional[str] = None


class MemoryInsightResponse(BaseModel):
    id: str
    user_id: str
    conversation_id: Optional[str] = None
    situation: Optional[str] = None
    what_happened: Optional[str] = None
    emotion: Optional[str] = None
    what_helped: Optional[str] = None
    follow_up: Optional[str] = None
    context_type: Optional[str] = None
    date: Optional[str] = None
    created: str


class EmotionTrendsResponse(BaseModel):
    dominant_emotions: list[str]
    trending_emotions: list[dict]
    emotion_patterns: dict


class ExtractThemesRequest(BaseModel):
    conversation_id: str


class ConversationThemesResponse(BaseModel):
    themes: list[dict]
    frequencies: list[dict]


class TrackHelpRequest(BaseModel):
    conversation_id: str
    advice_given: str
    help_rating: int
    follow_up_mood: Optional[int] = None


class TrackHelpResponse(BaseModel):
    id: str
    saved: bool


class LearnPersonalityResponse(BaseModel):
    saved: bool
    message: Optional[str] = None
    communication_style: Optional[str] = None
    preference_advice_type: Optional[str] = None
    response_length_preference: Optional[str] = None
    emotional_openness: Optional[str] = None


class SelectResponseTypeRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class SelectResponseTypeResponse(BaseModel):
    response_type: str
    reason: str


class ConversationSummaryResponse(BaseModel):
    id: str
    user_id: str
    created: str
    updated: str
    summary: Optional[str] = None
    messages: Optional[list[dict]] = None
    key_points: Optional[list[str]] = None
    follow_up_needed: Optional[bool] = None
    follow_up_date: Optional[str] = None
    emotional_journey: Optional[str] = None
    is_active: bool


class CheckInResponse(BaseModel):
    check_in_message: Optional[str] = None
    conversation_id: Optional[str] = None


class ProactiveCheckinResponse(BaseModel):
    id: str
    user_id: str
    scheduled_time: str
    reason: Optional[str] = None
    suggested_message: Optional[str] = None
    actual_response: Optional[str] = None
    effectiveness: Optional[int] = None
    created_at: str


class ProactiveCheckinRespondRequest(BaseModel):
    actual_response: str
    effectiveness: Optional[int] = None


class ScheduleCheckinResponse(BaseModel):
    status: str
    reason: Optional[str] = None
    checkin: Optional[ProactiveCheckinResponse] = None


class RecoveryDataResponse(BaseModel):
    id: str
    user_id: str
    mood_dip_date: str
    lowest_level: int
    recovery_date: Optional[str] = None
    recovery_days: Optional[int] = None
    catalyst: Optional[str] = None
    severity: Optional[str] = None
    created_at: str


class RecoveryStats(BaseModel):
    average_recovery_days: float
    fastest_recovery_days: Optional[int] = None
    fastest_recovery_catalyst: Optional[str] = None
    longest_recovery_days: Optional[int] = None
    longest_recovery_catalyst: Optional[str] = None
    trend_description: str


class RecoveryPatternsResponse(BaseModel):
    history: list[RecoveryDataResponse]
    stats: RecoveryStats


class TrackEngagementRequest(BaseModel):
    conversation_id: str


class TrackEngagementResponse(BaseModel):
    id: str
    user_id: str
    conversation_id: str
    user_response_time: Optional[int] = None
    suggestion_followed: Optional[bool] = None
    return_time_hours: Optional[int] = None
    sentiment_shift: Optional[int] = None
    created_at: str


class ABTestResult(BaseModel):
    test_name: str
    group_a_label: str
    group_a_metric: float
    group_b_label: str
    group_b_metric: float
    conclusion: str


class ConvoTypeEngagement(BaseModel):
    convo_type: str
    avg_response_time: float
    return_rate_24h: float
    total_convos: int


class EngagementStatsResponse(BaseModel):
    avg_response_time: float
    return_rate_24h: float
    convo_type_engagement: list[ConvoTypeEngagement]
    personalized_vs_generic: dict
    ab_tests: list[ABTestResult]


class DetectCrisisRequest(BaseModel):
    conversation_id: str
    message: str


class DetectCrisisResponse(BaseModel):
    severity_level: int
    red_flags_detected: list[str]
    action_taken: Optional[str] = None


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    unlocked_badges: Optional[list[str]] = None
    badge_history: Optional[list[dict]] = None
    emergency_contact: Optional[str] = None
    created: str


class ProfileUpdate(BaseModel):
    emergency_contact: Optional[str] = None




# --- Notifications ---
class DeviceRegister(BaseModel):
    push_token: str
    platform: str
    device_id: str

