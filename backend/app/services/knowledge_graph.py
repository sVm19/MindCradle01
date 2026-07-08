"""
MindCradle Compounding Intelligence Engine
==========================================
Personal Knowledge Graph (PKG) service.

This module is the brain of ARIA's compounding intelligence. Every
interaction feeds into this graph; every ARIA response reads from it.

Public API
----------
process_source(user_id, source_type, source_id, text, token)
    Tier-2 entry point. Extracts entities from text, upserts nodes+edges,
    creates mention records. Call this from a BackgroundTask after any
    journal/mood/morning/wind-down save.

get_context_packet(user_id, topic, token) -> str
    Returns a structured ≤600-token Personal Context Packet for injection
    into ARIA's system prompt.

decay_confidence(user_id, token)
    Nightly: apply confidence decay to all nodes.

compute_growth_metrics(user_id, token) -> dict
    Nightly: compute 10 growth dimensions for 7d/30d/90d windows.

upsert_node(user_id, label, node_type, ..., token) -> str
    Find-or-create a knowledge node. Returns node id.

upsert_edge(user_id, source_id, target_id, edge_type, token)
    Find-or-create a knowledge edge, incrementing weight/evidence.

update_goal_threads(user_id, token)
    Nightly: analyse goal nodes, update progress signals.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import OPENROUTER_API_URL, OPENROUTER_API_KEY, OPENROUTER_MODEL
from app.services.supabase import pb

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

CONFIDENCE_DECAY_PER_DAY = 0.01
CONFIDENCE_FLOOR = 0.10
CONFIDENCE_BOOST_PER_MENTION = 0.08
CONFIDENCE_CAP = 0.95
EDGE_WEIGHT_BOOST = 0.10
EDGE_WEIGHT_CAP = 1.0
CONTEXT_PACKET_MAX_NODES = 8
CONTEXT_PACKET_MAX_GOALS = 4
CONTEXT_PACKET_MAX_PATTERNS = 3
MAX_ENTITIES_PER_EXTRACT = 5

EXTRACTION_SYSTEM_PROMPT = """You are an entity extraction engine for a personal growth AI.
Given a piece of personal writing, extract up to 5 meaningful entities.

Entity types: theme, entity, person, place, goal, habit, emotion, value, stressor, coping, achievement

Rules:
- Only extract entities that are genuinely meaningful and recurring themes, not passing mentions
- Be specific: "work stress" not "stress", "morning runs" not "exercise"
- For goals: extract only if there's clear intention language
- sentiment: float from -1.0 (very negative) to 1.0 (very positive) in the context of this writing
- Do NOT extract the user themselves, generic words like "day" or "time"

Respond with ONLY valid JSON. No explanation, no markdown.

Format:
{"entities": [
  {"label": "...", "type": "...", "sentiment": 0.0, "context": "20-word quote from text"},
  ...
]}"""


# ── Utility ────────────────────────────────────────────────────────────────────

def _canonical(label: str) -> str:
    """Normalise a label for deduplication."""
    return label.lower().strip()


def _safe(val, default=""):
    return val if val is not None else default


# ── Entity Extraction (Tier 2) ─────────────────────────────────────────────────

async def _extract_entities(text: str) -> list[dict]:
    """
    Call the LLM to extract structured entities from user-generated text.
    Returns list of {label, type, sentiment, context} dicts.
    Falls back to [] on any failure.
    """
    import httpx

    if not OPENROUTER_API_KEY or len(text.strip()) < 50:
        return []

    # Use cheapest model for extraction (cost control)
    model = "google/gemini-3.1-flash-lite"
    url = f"{OPENROUTER_API_URL.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": text[:1500]},  # cap input length
        ],
        "temperature": 0.1,
        "max_tokens": 400,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "MindCradle-PKG",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        data = json.loads(content)
        entities = data.get("entities") or []
        # Validate and cap
        valid = []
        for e in entities[:MAX_ENTITIES_PER_EXTRACT]:
            if isinstance(e, dict) and e.get("label") and e.get("type"):
                valid.append(e)
        return valid

    except Exception as exc:
        logger.warning("PKG entity extraction failed: %s", exc)
        return []


# ── Node Operations ─────────────────────────────────────────────────────────────

async def upsert_node(
    user_id: str,
    label: str,
    node_type: str,
    sentiment: float = 0.0,
    context_snippet: str = "",
    source_reason: str = "",
    token: Optional[str] = None,
) -> Optional[str]:
    """
    Find an existing node with the same canonical label+type for this user,
    or create a new one. Returns the node id or None on failure.
    """
    canonical = _canonical(label)

    try:
        # Try to find existing node
        existing = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && canonical_label="{canonical}" && node_type="{node_type}"',
                "perPage": 1,
            },
        )
        items = existing.get("items") or []

        if items:
            node = items[0]
            node_id = node["id"]
            old_conf = float(node.get("confidence") or 0.5)
            new_conf = min(CONFIDENCE_CAP, old_conf + CONFIDENCE_BOOST_PER_MENTION)
            old_valence = float(node.get("valence") or 0.0)
            # Weighted rolling average for valence
            new_valence = round(old_valence * 0.7 + sentiment * 0.3, 4)
            new_count = int(node.get("mention_count") or 1) + 1

            await pb.update_record(
                "user_knowledge_nodes",
                node_id,
                {
                    "confidence": round(new_conf, 4),
                    "valence": new_valence,
                    "mention_count": new_count,
                    "last_seen_at": datetime.now(timezone.utc).isoformat(),
                    "is_archived": False,
                },
                token=token,
            )
            return node_id

        # Create new node
        new_node = await pb.create_record(
            "user_knowledge_nodes",
            {
                "user_id": user_id,
                "label": label.strip(),
                "canonical_label": canonical,
                "node_type": node_type,
                "confidence": 0.5,
                "importance": 5,
                "valence": round(sentiment, 4),
                "mention_count": 1,
                "first_seen_at": datetime.now(timezone.utc).isoformat(),
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
                "source_reason": source_reason or f"Detected in {node_type} content",
                "is_confirmed": False,
                "is_archived": False,
                "metadata": {},
            },
            token=token,
        )
        return new_node["id"]

    except Exception as exc:
        logger.error("PKG upsert_node failed for '%s': %s", label, exc)
        return None


async def upsert_edge(
    user_id: str,
    source_node_id: str,
    target_node_id: str,
    edge_type: str,
    token: Optional[str] = None,
) -> None:
    """
    Find-or-create a directed edge between two knowledge nodes,
    incrementing weight and evidence on each call.
    """
    if source_node_id == target_node_id:
        return

    try:
        existing = await pb.list_records(
            "user_knowledge_edges",
            token=token,
            params={
                "filter": (
                    f'user_id="{user_id}" && source_node_id="{source_node_id}" '
                    f'&& target_node_id="{target_node_id}" && edge_type="{edge_type}"'
                ),
                "perPage": 1,
            },
        )
        items = existing.get("items") or []

        if items:
            edge = items[0]
            new_weight = min(EDGE_WEIGHT_CAP, float(edge.get("weight") or 0.3) + EDGE_WEIGHT_BOOST)
            await pb.update_record(
                "user_knowledge_edges",
                edge["id"],
                {
                    "weight": round(new_weight, 4),
                    "evidence_count": int(edge.get("evidence_count") or 1) + 1,
                    "last_reinforced_at": datetime.now(timezone.utc).isoformat(),
                },
                token=token,
            )
        else:
            await pb.create_record(
                "user_knowledge_edges",
                {
                    "user_id": user_id,
                    "source_node_id": source_node_id,
                    "target_node_id": target_node_id,
                    "edge_type": edge_type,
                    "weight": 0.3,
                    "evidence_count": 1,
                    "last_reinforced_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {},
                },
                token=token,
            )
    except Exception as exc:
        logger.error("PKG upsert_edge failed: %s", exc)


async def _create_mention(
    user_id: str,
    node_id: str,
    source_type: str,
    source_id: str,
    context_snippet: str,
    sentiment: float,
    token: Optional[str] = None,
) -> None:
    """Log a single entity mention."""
    try:
        await pb.create_record(
            "user_entity_mentions",
            {
                "user_id": user_id,
                "node_id": node_id,
                "source_type": source_type,
                "source_id": source_id,
                "context_snippet": context_snippet[:200],
                "sentiment": round(sentiment, 4),
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            },
            token=token,
        )
    except Exception as exc:
        logger.warning("PKG create_mention failed: %s", exc)


# ── Main Tier-2 Pipeline ────────────────────────────────────────────────────────

async def process_source(
    user_id: str,
    source_type: str,
    source_id: str,
    text: str,
    token: Optional[str] = None,
) -> int:
    """
    Tier-2 entry point. Called from BackgroundTasks after any content save.

    1. Extract entities from text via LLM
    2. Upsert knowledge nodes
    3. Create co-occurrence edges between all pairs of extracted entities
    4. Log entity mentions

    Returns the number of nodes created/updated.
    """
    if not text or len(text.strip()) < 50:
        return 0

    entities = await _extract_entities(text)
    if not entities:
        return 0

    node_ids: list[str] = []

    for ent in entities:
        label = _safe(ent.get("label"))
        node_type = _safe(ent.get("type"), "theme")
        sentiment = float(ent.get("sentiment") or 0.0)
        context = _safe(ent.get("context"))

        if not label or not node_type:
            continue

        node_id = await upsert_node(
            user_id=user_id,
            label=label,
            node_type=node_type,
            sentiment=sentiment,
            context_snippet=context,
            source_reason=f"Mentioned in {source_type}",
            token=token,
        )

        if node_id:
            await _create_mention(
                user_id=user_id,
                node_id=node_id,
                source_type=source_type,
                source_id=source_id,
                context_snippet=context,
                sentiment=sentiment,
                token=token,
            )
            node_ids.append(node_id)

    # Create co-occurrence edges between all pairs
    # Infer edge type from node types
    for i, src_id in enumerate(node_ids):
        for tgt_id in node_ids[i + 1:]:
            await upsert_edge(
                user_id=user_id,
                source_node_id=src_id,
                target_node_id=tgt_id,
                edge_type="associated_with",
                token=token,
            )

    logger.info(
        "PKG process_source: user=%s source=%s/%s → %d nodes processed",
        user_id, source_type, source_id, len(node_ids)
    )
    return len(node_ids)


# ── Context Packet Assembly ─────────────────────────────────────────────────────

async def get_context_packet(
    user_id: str,
    topic: Optional[str] = None,
    token: Optional[str] = None,
) -> str:
    """
    Assemble a ≤600-token Personal Context Packet for injection into
    ARIA's system prompt. Draws from nodes, edges, chapters, patterns,
    and growth metrics.

    topic: optional semantic topic to bias node retrieval toward.
    """
    lines: list[str] = []
    lines.append("[ARIA PERSONAL CONTEXT — use to inform your tone and depth, do NOT repeat verbatim]")
    lines.append("")

    now = datetime.now(timezone.utc)

    try:
        # 1. Current life chapter
        chap_result = await pb.list_records(
            "user_life_chapters",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && is_current=true',
                "perPage": 1,
            },
        )
        chapters = chap_result.get("items") or []
        if chapters:
            ch = chapters[0]
            start = ch.get("start_date", "")
            weeks_ago = ""
            if start:
                try:
                    delta = now - datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
                    weeks = max(1, delta.days // 7)
                    weeks_ago = f" (started {weeks}w ago)"
                except Exception:
                    pass
            lines.append(f"Current chapter: \"{_safe(ch.get('title'))}\"{weeks_ago}")
            if ch.get("theme_summary"):
                lines.append(f"Chapter theme: {ch['theme_summary']}")
            if ch.get("dominant_emotion"):
                lines.append(f"Dominant emotion this chapter: {ch['dominant_emotion']}")
            lines.append("")

        # 2. Recent mood trend (30d growth metric)
        growth_result = await pb.list_records(
            "user_growth_metrics",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && metric_type="positive_momentum" && period="30d"',
                "sort": "-computed_at",
                "perPage": 1,
            },
        )
        growth_items = growth_result.get("items") or []
        if growth_items:
            g = growth_items[0]
            delta = g.get("delta")
            if delta is not None:
                direction = "↑" if float(delta) >= 0 else "↓"
                lines.append(f"Mood trend (30d): {direction} {abs(float(delta)):.1f} points avg")

        # 3. Active goals (goal nodes + goal threads)
        goals_result = await pb.list_records(
            "user_goal_threads",
            token=token,
            params={
                "filter": f'user_id="{user_id}"',
                "sort": "-last_mentioned_at",
                "perPage": CONTEXT_PACKET_MAX_GOALS,
            },
        )
        goal_items = goals_result.get("items") or []
        if goal_items:
            lines.append("\nActive goals:")
            for g in goal_items:
                progress = _safe(g.get("progress_signal"), "unknown")
                count = g.get("mention_count", 1)
                lines.append(f"  → \"{g['goal_label']}\" [{progress}, {count} mentions]")

        # 4. High-confidence stressors and coping patterns
        nodes_result = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={
                "filter": (
                    f'user_id="{user_id}" && is_archived=false && confidence>=0.5'
                    ' && (node_type="stressor" || node_type="coping")'
                ),
                "sort": "-confidence",
                "perPage": 6,
            },
        )
        node_items = nodes_result.get("items") or []

        stressors = [n for n in node_items if n.get("node_type") == "stressor"]
        coping = [n for n in node_items if n.get("node_type") == "coping"]

        if stressors:
            lines.append("\nKnown stressors:")
            for n in stressors[:3]:
                conf = float(n.get("confidence") or 0)
                lines.append(f"  → \"{n['label']}\" [confidence: {conf:.0%}]")

        if coping:
            lines.append("\nKnown coping patterns:")
            for n in coping[:3]:
                conf = float(n.get("confidence") or 0)
                lines.append(f"  → \"{n['label']}\" [confidence: {conf:.0%}]")

        # 5. Top active themes (high importance, high confidence)
        themes_result = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={
                "filter": (
                    f'user_id="{user_id}" && is_archived=false && confidence>=0.5'
                    ' && (node_type="theme" || node_type="emotion" || node_type="value")'
                ),
                "sort": "-confidence",
                "perPage": CONTEXT_PACKET_MAX_NODES,
            },
        )
        theme_items = themes_result.get("items") or []

        if theme_items:
            lines.append("\nPersistent themes:")
            for n in theme_items[:5]:
                valence = float(n.get("valence") or 0)
                v_str = "positive" if valence > 0.2 else ("negative" if valence < -0.2 else "neutral")
                lines.append(f"  → \"{n['label']}\" [{n['node_type']}, {v_str}]")

        # 6. Behavioral patterns
        patterns_result = await pb.list_records(
            "user_behavioral_patterns",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && confidence>=0.5',
                "sort": "-confidence",
                "perPage": CONTEXT_PACKET_MAX_PATTERNS,
            },
        )
        pattern_items = patterns_result.get("items") or []

        if pattern_items:
            lines.append("\nBehavioral patterns ARIA has detected:")
            for p in pattern_items:
                impact = "positive" if p.get("is_positive") else "worth noting"
                lines.append(f"  → {p['label']} [{impact}]")

        lines.append("")
        lines.append("Guidance: Do NOT recite this context to the user. Let it naturally")
        lines.append("shape your understanding, empathy, and the depth of your responses.")

    except Exception as exc:
        logger.error("PKG get_context_packet failed: %s", exc)
        lines.append("[Context unavailable — respond without personalisation]")

    packet = "\n".join(lines)

    # Hard cap at ~600 tokens (~2400 chars)
    if len(packet) > 2400:
        packet = packet[:2400] + "\n[...context truncated for length]"

    return packet


# ── Nightly Jobs ────────────────────────────────────────────────────────────────

async def decay_confidence(user_id: str, token: Optional[str] = None) -> int:
    """
    Apply daily confidence decay to all nodes not seen in the last 24 hours.
    Nodes that fall below CONFIDENCE_FLOOR are archived.
    Returns number of nodes updated.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    try:
        result = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={
                "filter": (
                    f'user_id="{user_id}" && is_archived=false '
                    f'&& is_confirmed=false && last_seen_at<"{cutoff}"'
                ),
                "perPage": 500,
            },
        )
        items = result.get("items") or []
        updated = 0

        for node in items:
            old_conf = float(node.get("confidence") or 0.5)
            new_conf = max(CONFIDENCE_FLOOR, old_conf - CONFIDENCE_DECAY_PER_DAY)
            should_archive = new_conf <= CONFIDENCE_FLOOR

            await pb.update_record(
                "user_knowledge_nodes",
                node["id"],
                {
                    "confidence": round(new_conf, 4),
                    "is_archived": should_archive,
                },
                token=token,
            )
            updated += 1

        logger.info("PKG decay_confidence: user=%s updated=%d", user_id, updated)
        return updated

    except Exception as exc:
        logger.error("PKG decay_confidence failed for user %s: %s", user_id, exc)
        return 0


async def compute_growth_metrics(
    user_id: str,
    token: Optional[str] = None,
) -> dict:
    """
    Compute 10 growth dimensions for 7d / 30d / 90d windows.
    Returns a dict of {metric_type: {period: value}} for logging.
    """
    now = datetime.now(timezone.utc)
    results = {}

    def _window(days: int) -> str:
        return (now - timedelta(days=days)).isoformat()

    try:
        # Fetch data once for optimization
        mood_res = await pb.list_records(
            "mood_logs",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 200, "sort": "-created"}
        )
        all_moods = mood_res.get("items") or []

        journal_res = await pb.list_records(
            "journal_entries",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 100, "sort": "-created"}
        )
        all_journals = journal_res.get("items") or []

        ritual_res = await pb.list_records(
            "ritual_logs",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 200, "sort": "-created"}
        )
        all_rituals = ritual_res.get("items") or []

        goal_res = await pb.list_records(
            "user_goal_threads",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 100}
        )
        all_goals = goal_res.get("items") or []

        node_res = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 200}
        )
        all_nodes = node_res.get("items") or []

        pattern_res = await pb.list_records(
            "user_behavioral_patterns",
            token=token,
            params={"filter": f'user_id="{user_id}"', "perPage": 50}
        )
        all_patterns = pattern_res.get("items") or []

        for period, days in [("7d", 7), ("30d", 30), ("90d", 90)]:
            cutoff = _window(days)
            
            period_moods = [m for m in all_moods if m.get("created", "") >= cutoff]
            period_journals = [j for j in all_journals if j.get("created", "") >= cutoff]
            period_rituals = [r for r in all_rituals if r.get("created", "") >= cutoff]

            # 1. mood_average
            if period_moods:
                avg = sum(float(m.get("level") or m.get("mood_level") or 5) for m in period_moods) / len(period_moods)
                await _save_metric(user_id, "mood_average", period, avg, token)
                results.setdefault("mood_average", {})[period] = round(avg, 2)
            else:
                results.setdefault("mood_average", {})[period] = 5.0

            # 2. consistency_index
            expected = days
            index = min(1.0, len(period_rituals) / expected) if expected > 0 else 0.0
            await _save_metric(user_id, "consistency_index", period, index * 100, token)
            results.setdefault("consistency_index", {})[period] = round(index * 100, 1)

            # 3. journal_depth
            if period_journals:
                avg_words = sum(len(str(j.get("content") or "").split()) for j in period_journals) / len(period_journals)
                depth_score = min(100.0, (avg_words / 200) * 100)
                await _save_metric(user_id, "journal_depth", period, depth_score, token)
                results.setdefault("journal_depth", {})[period] = round(depth_score, 1)
            else:
                results.setdefault("journal_depth", {})[period] = 0.0

            # 4. emotional_regulation (% negative moods followed by journaling within 24h)
            neg_moods = [m for m in period_moods if float(m.get("level") or m.get("mood_level") or 5) <= 5]
            if neg_moods:
                regulated = 0
                for nm in neg_moods:
                    nm_time = datetime.fromisoformat(nm.get("created", "").replace("Z", "+00:00"))
                    for j in period_journals:
                        j_time = datetime.fromisoformat(j.get("created", "").replace("Z", "+00:00"))
                        diff_hours = (j_time - nm_time).total_seconds() / 3600
                        if 0 <= diff_hours <= 24:
                            regulated += 1
                            break
                reg_score = (regulated / len(neg_moods)) * 100
                await _save_metric(user_id, "emotional_regulation", period, reg_score, token)
                results.setdefault("emotional_regulation", {})[period] = round(reg_score, 1)
            else:
                await _save_metric(user_id, "emotional_regulation", period, 75.0, token)
                results.setdefault("emotional_regulation", {})[period] = 75.0

            # 5. self_awareness
            if period_journals:
                # Count themes/stressors/coping/goals/values nodes mentioned
                active_node_ids = {n["id"] for n in all_nodes if n.get("node_type") in ("theme", "stressor", "coping", "goal", "value")}
                # Count mentions
                mentions_res = await pb.list_records(
                    "user_entity_mentions",
                    token=token,
                    params={"filter": f'user_id="{user_id}" && extracted_at>="{cutoff}"', "perPage": 200}
                )
                mentions = mentions_res.get("items") or []
                journal_mentions = [m for m in mentions if m.get("node_id") in active_node_ids and m.get("source_type") == "journal"]
                
                avg_mentions = len(journal_mentions) / len(period_journals)
                sa_score = min(100.0, (avg_mentions / 3.0) * 100)
                await _save_metric(user_id, "self_awareness", period, sa_score, token)
                results.setdefault("self_awareness", {})[period] = round(sa_score, 1)
            else:
                await _save_metric(user_id, "self_awareness", period, 50.0, token)
                results.setdefault("self_awareness", {})[period] = 50.0

            # 6. stress_resilience
            if period_moods:
                # Calculate avg days from mood <= 5 to mood >= 6
                recoveries = []
                low_start = None
                for m in reversed(period_moods): # chronological
                    m_time = datetime.fromisoformat(m.get("created", "").replace("Z", "+00:00"))
                    lvl = float(m.get("level") or m.get("mood_level") or 5)
                    if lvl <= 5 and low_start is None:
                        low_start = m_time
                    elif lvl >= 6 and low_start is not None:
                        days = (m_time - low_start).total_seconds() / 86400
                        recoveries.append(days)
                        low_start = None
                
                if recoveries:
                    avg_days = sum(recoveries) / len(recoveries)
                    res_score = max(20.0, min(100.0, 100.0 - (avg_days * 15.0)))
                else:
                    res_score = 80.0
                await _save_metric(user_id, "stress_resilience", period, res_score, token)
                results.setdefault("stress_resilience", {})[period] = round(res_score, 1)
            else:
                await _save_metric(user_id, "stress_resilience", period, 80.0, token)
                results.setdefault("stress_resilience", {})[period] = 80.0

            # 7. goal_clarity
            active_goals = [g for g in all_goals if g.get("progress_signal") in ("growing", "achieved")]
            gc_score = min(100.0, len(active_goals) * 25.0)
            await _save_metric(user_id, "goal_clarity", period, gc_score, token)
            results.setdefault("goal_clarity", {})[period] = round(gc_score, 1)

            # 8. linguistic_growth
            if period_journals:
                avg_chars = sum(len(str(j.get("content") or "")) for j in period_journals) / len(period_journals)
                lg_score = min(100.0, (avg_chars / 600.0) * 100)
                await _save_metric(user_id, "linguistic_growth", period, lg_score, token)
                results.setdefault("linguistic_growth", {})[period] = round(lg_score, 1)
            else:
                await _save_metric(user_id, "linguistic_growth", period, 50.0, token)
                results.setdefault("linguistic_growth", {})[period] = 50.0

            # 9. pattern_awareness
            confirmed = [n for n in all_nodes if n.get("is_confirmed")]
            pa_score = min(100.0, (len(confirmed) * 20.0) + (len(all_patterns) * 15.0))
            await _save_metric(user_id, "pattern_awareness", period, pa_score, token)
            results.setdefault("pattern_awareness", {})[period] = round(pa_score, 1)

        # ── positive_momentum (delta between 7d and 30d average) ──────────────────
        mood_7d = results.get("mood_average", {}).get("7d")
        mood_30d = results.get("mood_average", {}).get("30d")
        if mood_7d is not None and mood_30d is not None:
            momentum = mood_7d - mood_30d
            await _save_metric(user_id, "positive_momentum", "7d", momentum, token)
            results["positive_momentum"] = {"7d": round(momentum, 2)}

        logger.info("PKG compute_growth_metrics: user=%s metrics=%s", user_id, list(results.keys()))
        return results

    except Exception as exc:
        logger.error("PKG compute_growth_metrics failed: %s", exc)
        return results


async def _save_metric(
    user_id: str,
    metric_type: str,
    period: str,
    value: float,
    token: Optional[str] = None,
) -> None:
    """Save a growth metric, looking up the previous value for delta calculation."""
    try:
        prev_result = await pb.list_records(
            "user_growth_metrics",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && metric_type="{metric_type}" && period="{period}"',
                "sort": "-computed_at",
                "perPage": 1,
            },
        )
        prev_items = prev_result.get("items") or []
        previous_value = float(prev_items[0]["value"]) if prev_items else None
        delta = (value - previous_value) if previous_value is not None else None

        await pb.create_record(
            "user_growth_metrics",
            {
                "user_id": user_id,
                "metric_type": metric_type,
                "period": period,
                "value": round(value, 4),
                "previous_value": round(previous_value, 4) if previous_value is not None else None,
                "delta": round(delta, 4) if delta is not None else None,
                "computed_at": datetime.now(timezone.utc).isoformat(),
            },
            token=token,
        )
    except Exception as exc:
        logger.warning("PKG _save_metric failed for %s/%s: %s", metric_type, period, exc)


async def update_goal_threads(user_id: str, token: Optional[str] = None) -> None:
    """
    Nightly: scan goal-type nodes and journal entries for goal language.
    Update progress signals on goal threads.
    """
    GROWING_SIGNALS = ["making progress", "closer to", "achieved", "did it", "completed", "finished"]
    STALLED_SIGNALS = ["haven't", "still haven't", "stuck", "gave up", "not working"]
    ACHIEVED_SIGNALS = ["achieved", "accomplished", "finished", "completed", "did it"]

    try:
        # Get all goal nodes for this user
        goal_nodes = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && node_type="goal" && is_archived=false',
                "perPage": 50,
            },
        )
        nodes = goal_nodes.get("items") or []

        # Get recent journal entries (30 days)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        journals = await pb.list_records(
            "journal_entries",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && created>="{cutoff}"',
                "perPage": 100,
            },
        )
        journal_items = journals.get("items") or []
        combined_text = " ".join(
            str(j.get("content") or "") for j in journal_items
        ).lower()

        for node in nodes:
            goal_label = node.get("label", "").lower()
            if not goal_label:
                continue

            # Check if goal is mentioned in recent journals
            is_mentioned = goal_label in combined_text

            # Determine progress signal
            signal = "unknown"
            if is_mentioned:
                if any(s in combined_text for s in ACHIEVED_SIGNALS):
                    signal = "achieved"
                elif any(s in combined_text for s in GROWING_SIGNALS):
                    signal = "growing"
                elif any(s in combined_text for s in STALLED_SIGNALS):
                    signal = "stalled"
                else:
                    signal = "growing"  # default if mentioned but unclear

            # Upsert into goal_threads
            existing = await pb.list_records(
                "user_goal_threads",
                token=token,
                params={
                    "filter": f'user_id="{user_id}" && goal_label="{node["label"]}"',
                    "perPage": 1,
                },
            )
            existing_items = existing.get("items") or []
            now_str = datetime.now(timezone.utc).isoformat()

            if existing_items:
                thread = existing_items[0]
                await pb.update_record(
                    "user_goal_threads",
                    thread["id"],
                    {
                        "last_mentioned_at": now_str,
                        "mention_count": int(thread.get("mention_count") or 1) + (1 if is_mentioned else 0),
                        "progress_signal": signal,
                        "related_node_ids": [node["id"]],
                    },
                    token=token,
                )
            else:
                await pb.create_record(
                    "user_goal_threads",
                    {
                        "user_id": user_id,
                        "goal_label": node["label"],
                        "first_mentioned_at": _safe(node.get("first_seen_at"), now_str),
                        "last_mentioned_at": now_str,
                        "mention_count": node.get("mention_count", 1),
                        "progress_signal": signal,
                        "related_node_ids": [node["id"]],
                        "evidence": [],
                    },
                    token=token,
                )

    except Exception as exc:
        logger.error("PKG update_goal_threads failed: %s", exc)


# ─── Life Chapters Detection (Tier 3) ─────────────────────────────────────────

async def detect_life_chapters(
    user_id: str,
    token: Optional[str] = None,
) -> Optional[dict]:
    """
    Cluster themes, mood average, goals, dominant emotions from past 30 days.
    If theme similarity shifted, or mood average shifted > 1.5, or 3+ new goals:
    Close current chapter and open new chapter with an LLM-generated title & summary.
    """
    import httpx
    now = datetime.now(timezone.utc)
    today_str = now.date().isoformat()

    try:
        # 1. Fetch current chapter
        chap_res = await pb.list_records(
            "user_life_chapters",
            token=token,
            params={"filter": f'user_id="{user_id}" && is_current=true', "perPage": 1}
        )
        current_chap = chap_res.get("items")[0] if chap_res.get("items") else None

        # 2. Get past 30d entries
        cutoff_30d = (now - timedelta(days=30)).isoformat()

        # Fetch top active themes/emotions
        nodes_res = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && last_seen_at>="{cutoff_30d}" && confidence>=0.4',
                "sort": "-confidence",
                "perPage": 15
            }
        )
        nodes = nodes_res.get("items") or []
        themes = [n.get("label") for n in nodes if n.get("node_type") in ("theme", "stressor", "coping")]
        emotions = [n.get("label") for n in nodes if n.get("node_type") == "emotion"]
        goals = [n.get("label") for n in nodes if n.get("node_type") == "goal"]

        # Average mood in past 30d
        moods_res = await pb.list_records(
            "mood_logs",
            token=token,
            params={"filter": f'user_id="{user_id}" && created>="{cutoff_30d}"', "perPage": 200}
        )
        moods = moods_res.get("items") or []
        avg_mood = sum(float(m.get("level") or m.get("mood_level") or 5) for m in moods) / len(moods) if moods else 5.0

        # Determine shift triggers
        is_first_chapter = current_chap is None
        mood_shift = False
        new_goals_trigger = False

        if current_chap:
            # Check mood shift
            old_avg = float(current_chap.get("mood_average") or 5.0)
            if abs(avg_mood - old_avg) > 1.5:
                mood_shift = True

            # Check goals trigger (3+ goals started in this chapter)
            new_goals_count = sum(
                1 for n in nodes
                if n.get("node_type") == "goal" and n.get("first_seen_at", "") >= cutoff_30d
            )
            if new_goals_count >= 3:
                new_goals_trigger = True

        should_transition = is_first_chapter or mood_shift or new_goals_trigger

        if not should_transition:
            return None

        # Generate new chapter details via LLM
        title = "A New Horizon"
        summary = "A period of transition and setting new intentions."

        if OPENROUTER_API_KEY:
            url = f"{OPENROUTER_API_URL.rstrip('/')}/chat/completions"
            prompt = f"""You are a poetic biographer. Based on this person's recent themes, mood, and goals, identify the next chapter of their life.
Recent Themes: {', '.join(themes[:6]) if themes else 'General reflection'}
Recent Emotions: {', '.join(emotions[:4]) if emotions else 'Varying emotions'}
Recent Goals: {', '.join(goals[:4]) if goals else 'None specific'}
Mood average: {avg_mood:.1f}/10

Provide a JSON output with the following format:
{{"title": "poetic title here", "theme_summary": "2-sentence description here"}}"""

            payload = {
                "model": "google/gemini-3.1-flash-lite",
                "messages": [
                    {"role": "system", "content": "You must respond with ONLY valid JSON. Do not include markdown code blocks."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 200
            }
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    if content.startswith("```"):
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                    data = json.loads(content)
                    title = data.get("title") or title
                    summary = data.get("theme_summary") or summary
            except Exception as exc:
                logger.warning("LLM chapter generation failed, using defaults: %s", exc)

        # Sequence number
        chap_num = 1
        if current_chap:
            chap_num = int(current_chap.get("chapter_number") or 1) + 1
            # Close old chapter
            await pb.update_record(
                "user_life_chapters",
                current_chap["id"],
                {"end_date": today_str, "is_current": False},
                token=token
            )

        # Create new chapter
        new_ch = await pb.create_record(
            "user_life_chapters",
            {
                "user_id": user_id,
                "title": title,
                "chapter_number": chap_num,
                "start_date": today_str,
                "is_current": True,
                "theme_summary": summary,
                "dominant_emotion": emotions[0] if emotions else "calm",
                "mood_average": round(avg_mood, 2),
                "growth_score": 50.0,
                "dominant_themes": themes[:3],
                "node_ids": [n["id"] for n in nodes[:10]]
            },
            token=token
        )
        return new_ch

    except Exception as exc:
        logger.error("PKG detect_life_chapters failed: %s", exc)
        return None


# ─── Behavioral Pattern Detection (Tier 3) ────────────────────────────────────

async def detect_behavioral_patterns(
    user_id: str,
    token: Optional[str] = None,
) -> int:
    """
    Scan user's mood/journal timings and text to identify routines or cycles,
    saving them to user_behavioral_patterns.
    """
    try:
        # Fetch last 50 mood logs & journals
        moods_res = await pb.list_records(
            "mood_logs",
            token=token,
            params={"filter": f'user_id="{user_id}"', "sort": "-created", "perPage": 50}
        )
        moods = moods_res.get("items") or []

        journals_res = await pb.list_records(
            "journal_entries",
            token=token,
            params={"filter": f'user_id="{user_id}"', "sort": "-created", "perPage": 50}
        )
        journals = journals_res.get("items") or []

        detected = 0

        # Pattern 1: Sunday Dread Cycle
        sunday_moods = []
        weekday_moods = []
        for m in moods:
            created_str = m.get("created")
            if not created_str:
                continue
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                level = float(m.get("level") or m.get("mood_level") or 5)
                # Sunday (weekday=6 in python datetime starting Monday=0)
                if dt.weekday() == 6 and dt.hour >= 17:
                    sunday_moods.append(level)
                else:
                    weekday_moods.append(level)
            except Exception:
                pass

        if len(sunday_moods) >= 3 and len(weekday_moods) >= 10:
            avg_sun = sum(sunday_moods) / len(sunday_moods)
            avg_week = sum(weekday_moods) / len(weekday_moods)
            if avg_sun < avg_week - 1.0:
                await _save_behavioral_pattern(
                    user_id=user_id,
                    pattern_type="cycle",
                    label="Sunday dread pattern",
                    description="Your mood tends to dip on Sunday evenings compared to the rest of the week.",
                    is_positive=False,
                    mood_impact=round(avg_sun - avg_week, 2),
                    confidence=0.8,
                    token=token
                )
                detected += 1

        # Pattern 2: Consistent Reflection Routine
        journal_hours = []
        for j in journals:
            created_str = j.get("created")
            if not created_str:
                continue
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                journal_hours.append(dt.hour)
            except Exception:
                pass

        if len(journal_hours) >= 5:
            # Check standard deviation of writing hours
            mean_h = sum(journal_hours) / len(journal_hours)
            variance = sum((h - mean_h) ** 2 for h in journal_hours) / len(journal_hours)
            std_dev = math.sqrt(variance)
            if std_dev < 2.5:
                time_label = "morning" if mean_h < 12 else ("afternoon" if mean_h < 17 else "evening")
                await _save_behavioral_pattern(
                    user_id=user_id,
                    pattern_type="routine",
                    label=f"Consistent {time_label} reflection",
                    description=f"You consistently journal in the {time_label} around {int(mean_h)}:00.",
                    is_positive=True,
                    mood_impact=0.2,
                    confidence=0.75,
                    token=token
                )
                detected += 1

        return detected
    except Exception as exc:
        logger.error("PKG detect_behavioral_patterns failed: %s", exc)
        return 0


async def _save_behavioral_pattern(
    user_id: str,
    pattern_type: str,
    label: str,
    description: str,
    is_positive: bool,
    mood_impact: float,
    confidence: float,
    token: Optional[str] = None,
):
    try:
        # Check if already exists
        existing = await pb.list_records(
            "user_behavioral_patterns",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && label="{label}" && pattern_type="{pattern_type}"',
                "perPage": 1
            }
        )
        items = existing.get("items") or []

        if items:
            p = items[0]
            await pb.update_record(
                "user_behavioral_patterns",
                p["id"],
                {
                    "confidence": round(confidence, 4),
                    "mood_impact": round(mood_impact, 2),
                    "last_occurrence": datetime.now(timezone.utc).isoformat()
                },
                token=token
            )
        else:
            await pb.create_record(
                "user_behavioral_patterns",
                {
                    "user_id": user_id,
                    "pattern_type": pattern_type,
                    "label": label,
                    "description": description,
                    "is_positive": is_positive,
                    "mood_impact": round(mood_impact, 2),
                    "confidence": round(confidence, 4),
                    "streak_current": 1,
                    "streak_best": 1,
                    "last_occurrence": datetime.now(timezone.utc).isoformat(),
                    "metadata": {}
                },
                token=token
            )
    except Exception as exc:
        logger.warning("Failed to save behavioral pattern: %s", exc)

