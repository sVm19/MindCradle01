from datetime import datetime, timedelta, timezone

from app.services.relationship_memory import (
    format_relationship_memory_context,
    rank_relationship_memories,
    relationship_memory_score,
)


def test_relationship_memory_ranking_prioritizes_importance_over_chronology():
    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    old_important = {
        "id": "old",
        "title": "Overcame project anxiety",
        "type": "growth",
        "importance": 10,
        "confidence": 90,
        "last_occurrence": (now - timedelta(days=80)).isoformat(),
        "times_referenced": 3,
        "supporting_evidence": {"source_messages": ["I got through this before."]},
    }
    new_minor = {
        "id": "new",
        "title": "Felt tired today",
        "type": "relationship_pattern",
        "importance": 2,
        "confidence": 80,
        "last_occurrence": now.isoformat(),
        "times_referenced": 0,
        "supporting_evidence": {"source_messages": ["I feel tired."]},
    }

    ranked = rank_relationship_memories([new_minor, old_important], now=now)

    assert ranked[0]["id"] == "old"


def test_relationship_significance_increases_score():
    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    base = {
        "title": "Work presentations worry them",
        "type": "stressor",
        "importance": 6,
        "confidence": 75,
        "last_occurrence": now.isoformat(),
        "times_referenced": 0,
    }
    significant = {
        **base,
        "times_referenced": 5,
        "related_journal": "journal-id",
        "supporting_evidence": {"source_messages": ["Presentations still worry me."], "conversation_ids": ["c1"]},
    }

    assert relationship_memory_score(significant, now=now) > relationship_memory_score(base, now=now)


def test_empty_memory_context_forbids_fake_memories():
    context = format_relationship_memory_context([])

    assert "none yet" in context
    assert "Do not invent" in context
