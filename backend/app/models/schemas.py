from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from enum import Enum
from app.utils.sanitizer import sanitize


# --- Auth ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    password_confirm: str = Field(alias="passwordConfirm")
    name: str
    age_verified: Optional[bool] = None

    @field_validator('name', mode='before')
    @classmethod
    def sanitize_name(cls, v):
        if isinstance(v, str):
            return sanitize(v)
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        from app.utils.security import validate_password as val_pwd
        err = val_pwd(v)
        if err:
            raise ValueError(err)
        return v


class AuthResponse(BaseModel):
    token: str
    refresh_token: str = ""
    user_id: str
    name: str
    email: str


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Change Password ---
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(alias="currentPassword")
    new_password: str = Field(alias="newPassword")


# --- Forgot / Reset Password ---
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLoginRequest(BaseModel):
    token: str




class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(alias="newPassword")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        from app.utils.security import validate_password as val_pwd
        err = val_pwd(v)
        if err:
            raise ValueError(err)
        return v




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

    @field_validator('note', mode='before')
    @classmethod
    def sanitize_note(cls, v):
        if isinstance(v, str):
            return sanitize(v)
        return v

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        if not (1 <= v <= 10):
            raise ValueError('Mood must be 1-10')
        return v

    @field_validator('note')
    @classmethod
    def validate_note(cls, v):
        if len(v) > 5000:
            raise ValueError('Notes too long')
        return v


class MoodLogRequest(BaseModel):
    level: int
    notes: str

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        if not (1 <= v <= 10):
            raise ValueError('Mood must be 1-10')
        return v

    @field_validator('notes', mode='before')
    @classmethod
    def sanitize_notes(cls, v):
        if isinstance(v, str):
            return sanitize(v)
        return v

    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v):
        if len(v) > 5000:
            raise ValueError('Notes too long')
        return v


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

    @field_validator('prompt', 'content', 'ai_reflection', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return sanitize(v)
        return v

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if len(v) == 0:
            raise ValueError('Journal content cannot be empty')
        if len(v) > 5000:
            raise ValueError('Journal content too long')
        return v


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

    @field_validator('forecast', 'intention', 'activity_type', 'completed_at', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return sanitize(v)
        return v


class WindDownRitualCreate(BaseModel):
    release_item: str = Field(alias="releaseItem")
    gratitudes: list[str]
    audio_choice: str = Field(alias="audioChoice")
    timer: str

    @field_validator('release_item', 'audio_choice', 'timer', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return sanitize(v)
        return v

    @field_validator('gratitudes', mode='before')
    @classmethod
    def sanitize_gratitudes(cls, v):
        if isinstance(v, list):
            return [sanitize(item) if isinstance(item, str) else item for item in v]
        return v


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

    @field_validator('message', 'conversation_id', 'response_type', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return sanitize(v)
        return v

    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if len(v) == 0:
            raise ValueError('Message cannot be empty')
        if len(v) > 5000:
            raise ValueError('Message too long')
        return v


class CrisisResource(BaseModel):
    name: str
    phone: Optional[str] = None
    text: Optional[str] = None
    website: str


class AIChatResponse(BaseModel):
    reply: Optional[str] = None
    conversation_id: Optional[str] = None
    crisis_detected: Optional[bool] = None
    crisis_severity: Optional[int] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    type: Optional[str] = None
    reason: Optional[str] = None
    resources: Optional[list[CrisisResource]] = None
    encourage: Optional[str] = None
    contact_emergency: Optional[str] = None


class JournalReflectionRequest(BaseModel):
    journal_content: str
    user_id: str


class JournalReflectionResponse(BaseModel):
    reflection: str
    themes: list[str]
    emotional_tone: str
    linguistic_shift: Optional[str] = None


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


class AriaAgeVerifyRequest(BaseModel):
    age_verified: bool


class PrivacyAcceptanceRequest(BaseModel):
    privacy_accepted: bool


class WithdrawConsentRequest(BaseModel):
    password: str


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
    notify_on_crisis: Optional[bool] = False
    is_premium: bool = False
    subscription_expires_at: Optional[str] = None
    created: str


class ProfileUpdate(BaseModel):
    emergency_contact: Optional[str] = None
    notify_on_crisis: Optional[bool] = None

    @field_validator('emergency_contact', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return sanitize(v)
        return v


class SubscriptionCheckoutRequest(BaseModel):
    card_number: str
    cvc: str
    expiry: str


# --- Notifications ---
class DeviceRegister(BaseModel):
    push_token: str
    platform: str
    device_id: str


# --- Daily Discoveries ---
class DailyDiscoveryResponse(BaseModel):
    id: str
    user_id: str
    discovery_text: str
    confidence_score: int
    supporting_evidence: dict
    is_dismissed: bool
    is_shared: bool
    is_viewed: bool
    created_at: str


class DiscoveryFeedbackRequest(BaseModel):
    is_dismissed: Optional[bool] = None
    is_shared: Optional[bool] = None
    is_viewed: Optional[bool] = None


# --- Predictive Intelligence ---
class PredictionResponse(BaseModel):
    id: str
    user_id: str
    prediction_type: str
    prediction_text: str
    target_date: str
    confidence_score: int
    is_correct: Optional[bool] = None
    metadata: dict = {}
    created_at: str


class PredictionStats(BaseModel):
    total_evaluated: int
    correct_count: int
    accuracy_rate: float


class PredictionsPage(BaseModel):
    active_predictions: list[PredictionResponse]
    stats: PredictionStats


class PredictionFeedbackRequest(BaseModel):
    is_correct: bool = Field(alias="isCorrect")


# --- Semantic Search ---
class SearchResultItem(BaseModel):
    id: str
    user_id: str
    event_type: str
    source_id: Optional[str] = None
    event_date: str
    event_ts: str
    title: Optional[str] = None
    summary: Optional[str] = None
    emotion: Optional[str] = None
    mood_level: Optional[int] = None
    metadata: dict = {}
    rank_score: float
    similarity: Optional[float] = None


class SemanticSearchResponse(BaseModel):
    answer: str
    results: list[SearchResultItem]


# Updated richer search response
class SearchPage(BaseModel):
    results: list[SearchResultItem]
    total: int
    query: str
    search_mode: str   # "semantic" | "keyword" | "hybrid"
    has_embeddings: bool


class SearchSuggestionsResponse(BaseModel):
    suggestions: list[str]


class EmbeddingGenerateResponse(BaseModel):
    total: int
    embedded: int
    failed: int
    skipped: int


# --- Knowledge Graph / CIE ---
class KnowledgeNodeResponse(BaseModel):
    id: str
    label: str
    node_type: str
    confidence: float
    importance: int
    valence: float
    mention_count: int
    first_seen_at: str
    last_seen_at: str
    source_reason: Optional[str] = None
    is_confirmed: bool
    is_archived: bool
    metadata: dict = {}

class KnowledgeEdgeResponse(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    weight: float
    evidence_count: int
    last_reinforced_at: str

class KnowledgeGraphResponse(BaseModel):
    nodes: list[KnowledgeNodeResponse]
    edges: list[KnowledgeEdgeResponse]

class KnowledgeProcessRequest(BaseModel):
    source_type: str  # 'journal' | 'mood' | 'morning' | 'wind_down'
    source_id: str
    text: str

class KnowledgeProcessResponse(BaseModel):
    success: bool
    nodes_processed: int

class KnowledgeContextResponse(BaseModel):
    context_packet: str

class GrowthMetricItem(BaseModel):
    metric_type: str
    period: str
    value: float
    previous_value: Optional[float] = None
    delta: Optional[float] = None
    computed_at: str

class GrowthMetricsResponse(BaseModel):
    metrics: list[GrowthMetricItem]


class KnowledgeChapterResponse(BaseModel):
    id: str
    user_id: str
    title: str
    chapter_number: int
    start_date: str
    end_date: Optional[str] = None
    is_current: bool
    theme_summary: Optional[str] = None
    dominant_emotion: Optional[str] = None
    mood_average: Optional[float] = None
    growth_score: Optional[float] = None
    key_events: list = []
    dominant_themes: list[str] = []
    goals_started: list[str] = []
    goals_achieved: list[str] = []
    node_ids: list[str] = []
    detected_by: str
    confidence: float

class KnowledgeChaptersListResponse(BaseModel):
    chapters: list[KnowledgeChapterResponse]


class KnowledgeNodeUpdateRequest(BaseModel):
    label: Optional[str] = None
    is_confirmed: Optional[bool] = None
    is_archived: Optional[bool] = None
    valence: Optional[float] = None


class KnowledgeComparisonItem(BaseModel):
    metric_type: str
    current_value: float
    previous_value: float
    delta: float

class KnowledgeComparisonResponse(BaseModel):
    current_chapter_title: str
    previous_chapter_title: str
    improvements: list[str]
    challenge: str
    comparison_metrics: list[KnowledgeComparisonItem]


class TimelineEventResponse(BaseModel):
    id: str
    user_id: str
    event_type: str
    source_id: Optional[str] = None
    event_date: str
    event_ts: str
    title: Optional[str] = None
    summary: Optional[str] = None
    emotion: Optional[str] = None
    mood_level: Optional[int] = None
    metadata: dict = {}
    created_at: str

class TimelinePage(BaseModel):
    events: list[TimelineEventResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
    date_span: Optional[dict] = None
    types_present: list[str]


# ── Product Growth & Experimentation Engine Schemas ──────────────────────────

class TrackEventRequest(BaseModel):
    event_name: str
    properties: dict = {}


class ActiveAssignmentResponse(BaseModel):
    experiment_id: str
    experiment_name: str
    variant: str
    variants: list[str]


class ActiveAssignmentsList(BaseModel):
    assignments: list[ActiveAssignmentResponse]


class ExperimentVariantStats(BaseModel):
    variant: str
    sample_size: int
    conversions: int
    conversion_rate: float


class ExperimentAnalytics(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    variants: list[ExperimentVariantStats]
    p_value: float
    is_significant: bool
    improvement_delta: float
    conclusion: str


class FunnelStepAnalytics(BaseModel):
    step: int
    name: str
    count: int
    percent: float


class GrowthAnalyticsResponse(BaseModel):
    experiments: list[ExperimentAnalytics]
    funnel: list[FunnelStepAnalytics]


class CreateExperimentRequest(BaseModel):
    name: str
    description: str
    variants: list[str] = ["control", "treatment"]


class UpdateExperimentStatusRequest(BaseModel):
    status: str








