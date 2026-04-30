"""NVIDIA AI API integration service."""

from openai import OpenAI
from app.config import NVIDIA_API_KEY, NVIDIA_API_URL, NVIDIA_MODEL


def _get_client() -> OpenAI:
    """Create an OpenAI client pointed at NVIDIA's API."""
    return OpenAI(
        base_url=NVIDIA_API_URL,
        api_key=NVIDIA_API_KEY,
    )


async def chat_completion(
    messages: list[dict],
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 180,
) -> str:
    """Send a chat completion request to NVIDIA API and return the full response."""
    client = _get_client()

    full_messages = messages
    if system_prompt:
        full_messages = [{"role": "system", "content": system_prompt}] + messages

    completion = client.chat.completions.create(
        model=model or NVIDIA_MODEL,
        messages=full_messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=False,
    )

    return completion.choices[0].message.content or ""


async def chat_completion_stream(messages: list[dict], *, system_prompt: str | None = None):
    """Stream a chat completion response from NVIDIA API. Yields content chunks."""
    client = _get_client()

    full_messages = messages
    if system_prompt:
        full_messages = [{"role": "system", "content": system_prompt}] + messages

    completion = client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=full_messages,
        temperature=0.7,
        top_p=0.9,
        max_tokens=180,
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
