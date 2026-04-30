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
    user_id: str
    name: str
    email: str


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


class AIChatResponse(BaseModel):
    reply: str
    conversation_id: str
