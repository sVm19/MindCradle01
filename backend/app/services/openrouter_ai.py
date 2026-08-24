from openai import OpenAI, APITimeoutError, APIConnectionError, APIError, APIStatusError
from fastapi import HTTPException
import asyncio
import logging
from app.config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL

logger = logging.getLogger(__name__)
OPENROUTER_TIMEOUT = 30.0
PRIMARY_OPENROUTER_MODEL = OPENROUTER_MODEL


def _get_client() -> OpenAI:
    """Create an OpenAI client pointed at OpenRouter's API."""
    return OpenAI(
        base_url=OPENROUTER_API_URL,
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "MindCradle",
        },
    )


# Fallback models ordered by priority if the primary model is rate limited
# Restrained to only the primary model as requested: google/gemini-3.5-flash-lite
FALLBACK_MODELS = [
    PRIMARY_OPENROUTER_MODEL,
]


async def chat_completion(
    messages: list[dict],
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 180,
) -> str:
    """Send a chat completion request with automatic fallback models if rate-limited."""
    client = _get_client()

    full_messages = messages
    if system_prompt:
        full_messages = [{"role": "system", "content": system_prompt}] + messages

    candidate_models = [model] if model else FALLBACK_MODELS
    # Ensure no duplicates while preserving order
    candidate_models = list(dict.fromkeys(candidate_models))

    last_err = None
    for candidate in candidate_models:
        try:
            completion = client.chat.completions.create(
                model=candidate,
                messages=full_messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=False,
                timeout=OPENROUTER_TIMEOUT,
            )
            return completion.choices[0].message.content or ""
        except (APIConnectionError, APIError) as e:
            last_err = e
            logger.warning(
                f"OpenRouter model {candidate} failed ({str(e)}). Trying fallback if available..."
            )
            await asyncio.sleep(0.5)
            continue
        except APITimeoutError as e:
            last_err = e
            logger.warning(f"OpenRouter timeout on {candidate}. Trying fallback...")
            continue
        except Exception as e:
            last_err = e
            logger.error(f"OpenRouter unexpected error on {candidate}: {str(e)}")
            continue

    # If all candidates failed
    if isinstance(last_err, APITimeoutError):
        raise HTTPException(
            status_code=504, detail="AI service timeout. Please try again."
        )
    elif isinstance(last_err, APIStatusError):
        err_msg = "AI service unavailable"
        if (
            last_err.body
            and isinstance(last_err.body, dict)
            and "message" in last_err.body
        ):
            err_msg = last_err.body["message"]
        elif getattr(last_err, "message", None):
            err_msg = last_err.message

        if last_err.status_code == 402:
            raise HTTPException(
                status_code=402, detail=f"OpenRouter credits exhausted: {err_msg}"
            )
        raise HTTPException(status_code=last_err.status_code, detail=err_msg)

    raise HTTPException(status_code=502, detail="AI service unavailable")


async def chat_completion_stream(
    messages: list[dict],
    *,
    system_prompt: str | None = None,
    model: str | None = None,
):
    """Stream a chat completion response with automatic model fallbacks."""
    client = _get_client()

    full_messages = messages
    if system_prompt:
        full_messages = [{"role": "system", "content": system_prompt}] + messages

    candidate_models = [model] if model else FALLBACK_MODELS
    candidate_models = list(dict.fromkeys(candidate_models))

    last_err = None
    for candidate in candidate_models:
        try:
            completion = client.chat.completions.create(
                model=candidate,
                messages=full_messages,
                temperature=0.7,
                top_p=0.9,
                max_tokens=180,
                stream=True,
                timeout=OPENROUTER_TIMEOUT,
            )

            for chunk in completion:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content is not None:
                    yield delta.content
            return  # Stream finished successfully
        except Exception as e:
            last_err = e
            logger.warning(
                f"OpenRouter stream error on {candidate} ({str(e)}). Trying fallback..."
            )
            await asyncio.sleep(0.5)
            continue

    # If all candidates fail during stream initialization
    if isinstance(last_err, APITimeoutError):
        raise HTTPException(
            status_code=504, detail="AI service timeout. Please try again."
        )
    elif isinstance(last_err, APIStatusError):
        err_msg = "AI service unavailable"
        if (
            last_err.body
            and isinstance(last_err.body, dict)
            and "message" in last_err.body
        ):
            err_msg = last_err.body["message"]
        elif getattr(last_err, "message", None):
            err_msg = last_err.message

        if last_err.status_code == 402:
            raise HTTPException(
                status_code=402, detail=f"OpenRouter credits exhausted: {err_msg}"
            )
        raise HTTPException(status_code=last_err.status_code, detail=err_msg)

    raise HTTPException(status_code=502, detail="AI service unavailable")


async def get_recommendation(
    mood_level: int, emotions: list[str], history_summary: str
) -> str:
    """Generate a personalized resource recommendation based on mood data."""
    prompt = f"""Based on the following user mood data, recommend 2-3 specific resources from the available list:
- Current mood level: {mood_level}/10
- Current emotions: {', '.join(emotions) if emotions else 'not specified'}
- Recent history: {history_summary or 'no history available'}

Provide brief, warm explanations for each recommendation."""

    return await chat_completion([{"role": "user", "content": prompt}])
