from __future__ import annotations

from datetime import datetime, timezone
from math import exp, log1p
from typing import Any


def parse_memory_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            parsed = datetime.strptime(str(value).replace("T", " ").split(".")[0], "%Y-%m-%d %H:%M:%S")
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)


def relationship_memory_score(memory: dict[str, Any], *, now: datetime | None = None) -> float:
    """Rank by importance, recency, and relationship significance, not chronology."""
    now = now or datetime.now(timezone.utc)
    importance = max(0, min(int(memory.get("importance") or 0), 10)) / 10
    confidence = max(0, min(int(memory.get("confidence") or 0), 100)) / 100
    times_referenced = max(0, int(memory.get("times_referenced") or 0))

    last_seen = parse_memory_datetime(
        memory.get("last_occurrence") or memory.get("updated_at") or memory.get("created_at") or memory.get("created")
    )
    age_days = max(0.0, (now - last_seen).total_seconds() / 86400)
    recency = exp(-age_days / 45)

    evidence = memory.get("supporting_evidence") or {}
    if not isinstance(evidence, dict):
        evidence = {}
    evidence_count = len(evidence.get("conversation_ids") or []) + len(evidence.get("source_messages") or [])
    has_relation = 1 if memory.get("related_journal") or memory.get("related_mood") else 0
    relationship_significance = min(1.0, (log1p(times_referenced) / 3) + (evidence_count * 0.08) + (has_relation * 0.15))

    return round((importance * 0.45) + (recency * 0.25) + (relationship_significance * 0.20) + (confidence * 0.10), 6)


def rank_relationship_memories(memories: list[dict[str, Any]], *, now: datetime | None = None, limit: int = 6) -> list[dict[str, Any]]:
    ranked = []
    for memory in memories:
        item = dict(memory)
        item["rank_score"] = relationship_memory_score(item, now=now)
        ranked.append(item)
    return sorted(ranked, key=lambda item: item["rank_score"], reverse=True)[:limit]


def format_relationship_memory_context(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return (
            "Verified relationship memories: none yet.\n"
            "Do not invent past events. If no verified memory applies, respond without saying you remember."
        )

    lines = [
        "Verified relationship memories. Use only these when referencing the past; do not invent memories."
    ]
    for memory in memories:
        title = memory.get("title") or "Untitled memory"
        memory_type = memory.get("type") or "relationship"
        emotion = memory.get("emotion") or "unspecified"
        first = str(memory.get("first_occurrence") or "")[:10]
        last = str(memory.get("last_occurrence") or "")[:10]
        refs = int(memory.get("times_referenced") or 0)
        lines.append(
            f"- {title} | type={memory_type}; emotion={emotion}; importance={memory.get('importance')}; "
            f"confidence={memory.get('confidence')}; first={first}; last={last}; referenced={refs}x"
        )
    return "\n".join(lines)
