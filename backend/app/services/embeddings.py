"""
MindCradle Embedding Service
============================
Generates text embeddings using OpenRouter's text-embedding-3-small model
(1536 dimensions, OpenAI-compatible API).

Uses the same OPENROUTER_API_KEY as the chat service — no extra credentials needed.

Public API
----------
embed_text(text: str) -> list[float] | None
    Embed a single piece of text. Returns None on failure (graceful degradation).

embed_batch(texts: list[str]) -> list[list[float] | None]
    Embed a list of texts in one API call (max 100 per request).
    Returns a parallel list of embeddings; failed items are None.

build_event_text(event: dict) -> str
    Canonicalise a timeline_event dict into the text string that gets embedded.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from app.config import OPENROUTER_API_KEY, OPENROUTER_API_URL

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMS = 1536
MAX_TEXT_CHARS = 500       # Truncate text before embedding to control token cost
MAX_BATCH_SIZE = 50        # OpenRouter max inputs per call
_RETRY_DELAYS = [1.0, 2.5, 6.0]   # Exponential backoff for rate-limit errors


def build_event_text(event: dict) -> str:
    """
    Produce a concise, information-dense string from a timeline event dict.
    This is what gets embedded — optimised for semantic relevance.
    """
    parts = []

    event_type = (event.get("event_type") or "").replace("_", " ")
    if event_type:
        parts.append(event_type)

    title = (event.get("title") or "").strip()
    if title and title not in ("Morning Focus", "Wind Down", "ARIA Discovery", "Mood Check-in"):
        parts.append(title)

    summary = (event.get("summary") or "").strip()
    if summary:
        parts.append(summary)

    emotion = (event.get("emotion") or "").strip()
    if emotion:
        parts.append(f"emotions: {emotion}")

    level = event.get("mood_level")
    if level is not None:
        parts.append(f"mood level {level}/10")

    text = ". ".join(parts)
    # Truncate to MAX_TEXT_CHARS to keep tokens low
    return text[:MAX_TEXT_CHARS]


async def embed_text(text: str) -> Optional[list[float]]:
    """
    Embed a single text string.
    Returns None if the API call fails (search degrades to keyword-only).
    """
    results = await embed_batch([text])
    return results[0] if results else None


async def embed_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """
    Embed a batch of texts (max MAX_BATCH_SIZE per call).
    Returns a parallel list — failed items are None.
    Splits large batches automatically.
    """
    if not texts:
        return []

    if not OPENROUTER_API_KEY:
        logger.warning("Embeddings: OPENROUTER_API_KEY not set — skipping embedding")
        return [None] * len(texts)

    # Sanitise inputs
    cleaned = [t.strip()[:MAX_TEXT_CHARS] if t else "" for t in texts]

    # Split into MAX_BATCH_SIZE chunks
    all_results: list[Optional[list[float]]] = []
    for i in range(0, len(cleaned), MAX_BATCH_SIZE):
        chunk = cleaned[i: i + MAX_BATCH_SIZE]
        chunk_results = await _embed_chunk(chunk)
        all_results.extend(chunk_results)

    return all_results


async def _embed_chunk(texts: list[str]) -> list[Optional[list[float]]]:
    """Call the embedding API for one chunk (≤ MAX_BATCH_SIZE texts)."""
    url = f"{OPENROUTER_API_URL.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "MindCradle",
    }
    payload = {
        "model": EMBEDDING_MODEL,
        "input": texts,
    }

    for attempt, delay in enumerate([0.0] + _RETRY_DELAYS):
        if delay:
            await asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)

            if resp.status_code == 429:
                logger.warning("Embeddings: rate limited (attempt %d)", attempt + 1)
                continue   # retry with backoff

            resp.raise_for_status()
            data = resp.json()

            # OpenAI-compatible response: data.data[i].embedding
            items = data.get("data") or []
            # items are not guaranteed to be in order — sort by index
            items_sorted = sorted(items, key=lambda x: x.get("index", 0))

            results: list[Optional[list[float]]] = []
            for idx, item in enumerate(items_sorted):
                emb = item.get("embedding")
                if isinstance(emb, list) and len(emb) == EMBEDDING_DIMS:
                    results.append(emb)
                else:
                    logger.warning("Embeddings: unexpected embedding at index %d", idx)
                    results.append(None)

            # Pad if fewer results than inputs
            while len(results) < len(texts):
                results.append(None)

            return results

        except httpx.HTTPStatusError as exc:
            logger.error("Embeddings: HTTP %d — %s", exc.response.status_code, exc.response.text[:200])
        except Exception as exc:
            logger.error("Embeddings: unexpected error: %s", exc)

        if attempt == len(_RETRY_DELAYS):
            break   # exhausted retries

    # All retries failed
    return [None] * len(texts)
