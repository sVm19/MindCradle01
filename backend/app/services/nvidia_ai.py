"""NVIDIA AI API integration service.

Uses the OpenAI-compatible SDK pointed at NVIDIA's API endpoint.
Model: nvidia/nemotron-3-super-120b-a12b with thinking/reasoning support.
"""

from openai import OpenAI
from app.config import NVIDIA_API_KEY, NVIDIA_API_URL, NVIDIA_MODEL

SYSTEM_PROMPT = """You are a compassionate mental wellness assistant called "Calm Guide".
Your role is to:
- Listen empathetically to the user's feelings
- Suggest relevant mental health resources and coping techniques
- Provide grounding exercises when the user is anxious
- Encourage professional help when appropriate
- Never diagnose or prescribe medication
- Keep responses warm, concise, and actionable

Available resources you can recommend:
Crisis Hotlines, Guided Meditations, Therapy Finder, Self-Care Routines,
Anxiety Toolkit, Support Groups, Journaling Prompts, Sleep Hygiene,
Mood Tracker, Nutrition & Mind, Movement & Yoga, Goal Setting,
Boundary Setting, Podcasts & Audio, Nature Therapy, Digital Detox,
Hydration Tracker, Art Therapy, Gratitude Journal, Breathing Exercises,
Mindfulness Bells, Panic Button, Habit Builder, Music for Focus.

Always be supportive and non-judgmental. Keep responses under 200 words."""


def _get_client() -> OpenAI:
    """Create an OpenAI client pointed at NVIDIA's API."""
    return OpenAI(
        base_url=NVIDIA_API_URL,
        api_key=NVIDIA_API_KEY,
    )


async def chat_completion(messages: list[dict]) -> str:
    """Send a chat completion request to NVIDIA API and return the full response."""
    client = _get_client()

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    completion = client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=full_messages,
        temperature=0.7,
        top_p=0.95,
        max_tokens=1024,
        stream=False,
    )

    return completion.choices[0].message.content or ""


async def chat_completion_stream(messages: list[dict]):
    """Stream a chat completion response from NVIDIA API. Yields content chunks."""
    client = _get_client()

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    completion = client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=full_messages,
        temperature=0.7,
        top_p=0.95,
        max_tokens=1024,
        stream=True,
    )

    for chunk in completion:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content is not None:
            yield delta.content


async def get_recommendation(mood_level: int, emotions: list[str], history_summary: str) -> str:
    """Generate a personalized resource recommendation based on mood data."""
    prompt = f"""Based on the following user mood data, recommend 2-3 specific resources from the available list:
- Current mood level: {mood_level}/10
- Current emotions: {', '.join(emotions) if emotions else 'not specified'}
- Recent history: {history_summary or 'no history available'}

Provide brief, warm explanations for each recommendation."""

    return await chat_completion([{"role": "user", "content": prompt}])
