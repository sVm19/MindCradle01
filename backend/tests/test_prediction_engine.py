import pytest
from datetime import datetime, timezone
from app.services.prediction_engine import _parse_date, _get_date_string

def test_parse_date_isoformat():
    dt_str = "2026-07-08T02:30:00.123Z"
    dt = _parse_date(dt_str)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 7
    assert dt.day == 8
    assert dt.hour == 2

def test_parse_date_simple():
    dt_str = "2026-07-08 02:30:00"
    dt = _parse_date(dt_str)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 7
    assert dt.day == 8
    assert dt.hour == 2

def test_get_date_string():
    dt = datetime(2026, 7, 8, 2, 30, tzinfo=timezone.utc)
    assert _get_date_string(dt) == "2026-07-08"

from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch("app.services.prediction_engine.pb.list_records")
@patch("app.services.prediction_engine.pb.upsert_records")
async def test_generate_predictions_pkg_stressors_coping(mock_upsert, mock_list):
    # Mock return values for list_records:
    # 1. wind_down_rituals (empty)
    # 2. mood_logs (empty)
    # 3. journal_entries (empty)
    # 4. user_knowledge_nodes (active stressors + active coping)
    # 5. user_entity_mentions (mentions of stressors)
    mock_list.side_effect = [
        {"items": []}, # wind_downs
        {"items": []}, # moods
        {"items": []}, # journals
        {"items": []}, # mornings
        {"items": []}, # moods_60d
        {"items": [
            {"id": "node-str-1", "label": "work stress", "node_type": "stressor", "confidence": 0.8},
            {"id": "node-cop-1", "label": "meditation", "node_type": "coping", "confidence": 0.7}
        ]}, # user_knowledge_nodes
        {"items": [
            {"node_id": "node-str-1", "created_at": "2026-07-08T02:00:00Z"}
        ]} # user_entity_mentions
    ]
    
    from app.services.prediction_engine import generate_predictions_for_user
    
    res = await generate_predictions_for_user("user-abc", token="mock-token")
    
    # We should have generated 3 predictions: 1 for skip friday, 1 for stressor trigger, 1 for coping recommendation
    assert len(res) == 3
    types = [p["prediction_type"] for p in res]
    assert "wind_down_skip_friday" in types
    assert "pkg_stressor_trigger" in types
    assert "pkg_coping_recommendation" in types
    
    # Verify mock upsert was called
    assert mock_upsert.call_count == 3

