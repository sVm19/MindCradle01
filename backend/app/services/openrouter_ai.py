from openai import OpenAI, APITimeoutError, APIConnectionError, APIError
from fastapi import HTTPException
import logging
from app.config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL

logger = logging.getLogger(__name__)
OPENROUTER_TIMEOUT = 30.0

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


async def chat_completion(
    messages: list[dict],
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 180,
) -> str:
    """Send a chat completion request and return the full response."""
    client = _get_client()

    full_messages = messages
    if system_prompt:
        full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        completion = client.chat.completions.create(
            model=model or OPENROUTER_MODEL,
            messages=full_messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=False,
            timeout=OPENROUTER_TIMEOUT,
        )
        return completion.choices[0].message.content or ""
    except APITimeoutError as e:
        logger.error(f"OpenRouter timeout error: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail="AI service timeout. Please try again."
        )
    except (APIConnectionError, APIError) as e:
        logger.error(f"OpenRouter API error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail="AI service unavailable"
        )
    except Exception as e:
        logger.error(f"OpenRouter unexpected error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail="AI service unavailable"
        )


async def chat_completion_stream(messages: list[dict], *, system_prompt: str | None = None):
    """Stream a chat completion response. Yields content chunks."""
    client = _get_client()

    full_messages = messages
    if system_prompt:
        full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        completion = client.chat.completions.create(
            model=OPENROUTER_MODEL,
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
    except APITimeoutError as e:
        logger.error(f"OpenRouter stream timeout error: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail="AI service timeout. Please try again."
        )
    except (APIConnectionError, APIError) as e:
        logger.error(f"OpenRouter stream API error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail="AI service unavailable"
        )
    except Exception as e:
        logger.error(f"OpenRouter stream unexpected error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail="AI service unavailable"
        )


async def get_recommendation(mood_level: int, emotions: list[str], history_summary: str) -> str:
    """Generate a personalized resource recommendation based on mood data."""
    prompt = f"""Based on the following user mood data, recommend 2-3 specific resources from the available list:
- Current mood level: {mood_level}/10
- Current emotions: {', '.join(emotions) if emotions else 'not specified'}
- Recent history: {history_summary or 'no history available'}

Provide brief, warm explanations for each recommendation."""

    return await chat_completion([{"role": "user", "content": prompt}])
