import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.routers.ai import _build_memory_insight_prompt

client = TestClient(app)

def test_recovery_patterns_requires_auth():
    response = client.get("/api/ai/recovery-patterns")
    assert response.status_code == 401

def test_recovery_patterns_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    now = datetime.now(timezone.utc)
    
    # Trace timeline:
    # Day -10: level 8 (Normal)
    # Day -8: level 3 (Dip starts, moderate/severe?) -> level 3 is severe if <= 2, otherwise moderate. So level 3 is moderate.
    # Day -6: level 2 (Lowest level updated -> severe)
    # Day -4: level 7 (Recovered! Took 4 days)
    mock_mood_logs = [
        {
            "id": "log_1",
            "level": 8,
            "created": (now - timedelta(days=10)).isoformat(),
            "emotions": []
        },
        {
            "id": "log_2",
            "level": 3,
            "created": (now - timedelta(days=8)).isoformat(),
            "emotions": ["anxious"]
        },
        {
            "id": "log_3",
            "level": 2,
            "created": (now - timedelta(days=6)).isoformat(),
            "emotions": ["stressed"]
        },
        {
            "id": "log_4",
            "level": 7,
            "created": (now - timedelta(days=4)).isoformat(),
            "emotions": ["calm"]
        }
    ]

    mock_journals = [
        {
            "id": "j_1",
            "user_id": "user_123",
            "prompt": "Morning reflection",
            "content": "Writing to process my thoughts.",
            "created": (now - timedelta(days=5)).isoformat() # falls inside dip window (-8 to -4)
        }
    ]

    mock_recovery_db = []

    async def fake_list_records(collection, token=None, params=None):
        if collection == "mood_logs":
            return {"items": mock_mood_logs, "totalItems": len(mock_mood_logs)}
        if collection == "recovery_data":
            return {"items": mock_recovery_db, "totalItems": len(mock_recovery_db)}
        if collection == "journal_entries":
            return {"items": mock_journals, "totalItems": len(mock_journals)}
        return {"items": [], "totalItems": 0}

    async def fake_create_record(collection, data, token=None):
        assert collection == "recovery_data"
        record = {
            "id": f"rec_mock_{len(mock_recovery_db)}",
            **data
        }
        mock_recovery_db.append(record)
        return record

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/api/ai/recovery-patterns", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "history" in data
    assert "stats" in data
    
    # 1 recovery completed
    assert len(mock_recovery_db) == 1
    rec = mock_recovery_db[0]
    assert rec["lowest_level"] == 2
    assert rec["severity"] == "severe"
    assert rec["recovery_days"] == 4
    assert rec["catalyst"] == "journaling"  # matched mock_journals

    stats = data["stats"]
    assert stats["average_recovery_days"] == 4.0
    assert stats["fastest_recovery_days"] == 4
    assert stats["fastest_recovery_catalyst"] == "journaling"
    assert "Baseline established" in stats["trend_description"]

@pytest.mark.anyio
async def test_recovery_patterns_prompt_injection(monkeypatch):
    # Test that _build_memory_insight_prompt pulls recovery_data and structures the prompt addition correctly
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    mock_recovery_records = [
        {
            "id": "rec_1",
            "user_id": "user_123",
            "mood_dip_date": "2026-06-01T12:00:00Z",
            "lowest_level": 3,
            "recovery_date": "2026-06-03T12:00:00Z",
            "recovery_days": 2,
            "catalyst": "journaling",
            "severity": "moderate"
        },
        {
            "id": "rec_2",
            "user_id": "user_123",
            "mood_dip_date": "2026-06-05T12:00:00Z",
            "lowest_level": 2,
            "recovery_date": "2026-06-10T12:00:00Z",
            "recovery_days": 5,
            "catalyst": "isolation",
            "severity": "severe"
        }
    ]

    async def fake_list_records(collection, token=None, params=None):
        if collection == "recovery_data":
            return {"items": mock_recovery_records, "totalItems": len(mock_recovery_records)}
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    prompt = await _build_memory_insight_prompt("fake_token", "user_123")
    
    # Verify stats are parsed and structured in prompt addition
    assert "recovery patterns" in prompt.lower()
    assert "average recovery time" in prompt.lower()
    assert "last mood dip recovery" in prompt.lower()
    assert "trend" in prompt.lower()
    assert "isolation makes it take longer" in prompt.lower()
