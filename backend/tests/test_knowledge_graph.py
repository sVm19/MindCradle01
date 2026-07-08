import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from app.services.knowledge_graph import (
    _canonical,
    _safe,
    _extract_entities,
)

def test_canonical_labels():
    assert _canonical("Work Stress ") == "work stress"
    assert _canonical(" Morning Runs") == "morning runs"
    assert _canonical("PROJECT ALPHA") == "project alpha"

def test_safe_helper():
    assert _safe("hello") == "hello"
    assert _safe(None) == ""
    assert _safe(None, "default") == "default"

@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_extract_entities_empty_or_short(mock_client):
    res = await _extract_entities("short")
    assert res == []

@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_extract_entities_failure_fallback(mock_client):
    mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("API offline")
    res = await _extract_entities("This is a very long journal entry about my manager and how morning meditation has helped with anxiety.")
    assert res == []

@pytest.mark.asyncio
@patch("app.services.supabase.pb.list_records")
async def test_detect_behavioral_patterns_sunday_dread(mock_list):
    # Mock listing 50 mood logs (some Sunday evenings with level 3, weekdays with level 7)
    sunday_moods = [
        {"created": "2026-07-05T19:00:00Z", "level": 3},
        {"created": "2026-06-28T19:30:00Z", "level": 2},
        {"created": "2026-06-21T18:00:00Z", "level": 3},
    ]
    weekday_moods = [
        {"created": f"2026-07-0{d}T12:00:00Z", "level": 7} for d in range(1, 5)
    ] * 3 # 12 weekday mood logs
    
    # Return moods on first call, empty journals on second, empty existing check on third
    mock_list.side_effect = [
        {"items": sunday_moods + weekday_moods},
        {"items": []},
        {"items": []}
    ]
    
    from app.services.knowledge_graph import detect_behavioral_patterns
    
    with patch("app.services.supabase.pb.create_record", new_callable=AsyncMock) as mock_create:
        detected = await detect_behavioral_patterns("user-123", token="mock-token")
        # Sunday dread cycle pattern should be detected and saved
        assert detected == 1
        assert mock_create.call_count == 1
        created_data = mock_create.call_args[0][1]
        assert created_data["pattern_type"] == "cycle"
        assert "Sunday dread" in created_data["label"]

@pytest.mark.asyncio
@patch("app.services.supabase.pb.list_records")
async def test_detect_life_chapters_first_time(mock_list):
    # Mock listing:
    # 1. current chapter (returns empty, meaning no chapters exist yet)
    # 2. active nodes
    # 3. past 30d moods
    mock_list.side_effect = [
        {"items": []},
        {"items": [{"id": "n1", "label": "work stress", "node_type": "stressor"}]},
        {"items": [{"level": 6}, {"level": 7}]}
    ]
    
    from app.services.knowledge_graph import detect_life_chapters
    
    with patch("app.services.supabase.pb.create_record", new_callable=AsyncMock) as mock_create:
        new_ch = await detect_life_chapters("user-123", token="mock-token")
        assert new_ch is not None
        assert mock_create.call_count == 1
        created_data = mock_create.call_args[0][1]
        assert created_data["chapter_number"] == 1
        assert created_data["is_current"] is True

