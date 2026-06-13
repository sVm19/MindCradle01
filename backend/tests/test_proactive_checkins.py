import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_schedule_checkin_requires_auth():
    response = client.post("/api/ai/schedule-checkin")
    assert response.status_code == 401

def test_list_proactive_checkins_requires_auth():
    response = client.get("/api/ai/proactive-checkins")
    assert response.status_code == 401

def test_respond_to_checkin_requires_auth():
    response = client.post("/api/ai/proactive-checkins/checkin_123/respond", json={"actual_response": "Thanks"})
    assert response.status_code == 401

def test_schedule_checkin_notifications_disabled(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        if collection == "push_notification_tokens":
            # Return no tokens to simulate notifications disabled
            return {"items": [], "totalItems": 0}
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/schedule-checkin", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "skipped"
    assert data["reason"] == "notifications_disabled"

def test_schedule_checkin_already_scheduled_today(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        if collection == "push_notification_tokens":
            return {"items": [{"id": "token_1", "push_token": "abc", "is_active": True}], "totalItems": 1}
        if collection == "proactive_checkins":
            # Return a check-in scheduled for today
            return {
                "items": [{
                    "id": "checkin_1",
                    "user_id": "user_123",
                    "scheduled_time": datetime.now(timezone.utc).isoformat(),
                    "reason": "rough_day",
                    "suggested_message": "How are you?"
                }],
                "totalItems": 1
            }
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/schedule-checkin", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "skipped"
    assert data["reason"] == "already_scheduled_today"

def test_schedule_checkin_wednesday_anxiety_spike(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    # Mock mood logs having Wed anxiety spikes
    now = datetime.now(timezone.utc)
    # Find a Wednesday date in the last 30 days
    wednesdays = []
    for i in range(30):
        d = now - timedelta(days=i)
        if d.weekday() == 2:  # Wednesday
            wednesdays.append(d)

    mock_mood_logs = []
    for idx, wed in enumerate(wednesdays):
        mock_mood_logs.append({
            "id": f"log_wed_{idx}",
            "level": 3,
            "emotions": ["anxiety", "stressed"],
            "created": wed.strftime("%Y-%m-%d %H:%M:%S")
        })

    async def fake_list_records(collection, token=None, params=None):
        if collection == "push_notification_tokens":
            return {"items": [{"id": "token_1", "push_token": "abc", "is_active": True}], "totalItems": 1}
        if collection == "proactive_checkins":
            return {"items": [], "totalItems": 0}
        if collection == "mood_logs":
            return {"items": mock_mood_logs, "totalItems": len(mock_mood_logs)}
        return {"items": [], "totalItems": 0}

    created_checkin = None
    async def fake_create_record(collection, data, token=None):
        nonlocal created_checkin
        assert collection == "proactive_checkins"
        created_checkin = data
        return {
            "id": "new_checkin_123",
            "user_id": data["user_id"],
            "scheduled_time": data["scheduled_time"],
            "reason": data["reason"],
            "suggested_message": data["suggested_message"],
            "actual_response": None,
            "effectiveness": None,
            "created_at": now.isoformat()
        }

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/schedule-checkin", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scheduled"
    assert data["checkin"]["reason"] == "anxiety_spike_wednesday"
    assert "Wednesday" in data["checkin"]["suggested_message"]
    
    # Scheduled for Tuesday (weekday 1) at 18:00
    sched_dt = datetime.fromisoformat(data["checkin"]["scheduled_time"])
    assert sched_dt.weekday() == 1
    assert sched_dt.hour == 18

def test_list_proactive_checkins(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    now = datetime.now(timezone.utc)
    mock_checkins = [
        {
            "id": "checkin_active",
            "user_id": "user_123",
            "scheduled_time": (now - timedelta(hours=2)).isoformat(),
            "reason": "rough_day",
            "suggested_message": "How are you holding up?",
            "actual_response": "Doing okay",
            "effectiveness": 4,
            "created": (now - timedelta(hours=3)).isoformat()
        }
    ]

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "proactive_checkins"
        assert "scheduled_time <=" in params["filter"]
        return {"items": mock_checkins, "totalItems": 1}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/api/ai/proactive-checkins", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "checkin_active"
    assert data[0]["actual_response"] == "Doing okay"
    assert data[0]["effectiveness"] == 4

def test_respond_to_proactive_checkin_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    updated_payload = None
    async def fake_update_record(collection, record_id, data, token=None):
        assert collection == "proactive_checkins"
        assert record_id == "checkin_xyz"
        nonlocal updated_payload
        updated_payload = data
        return {
            "id": record_id,
            "user_id": "user_123",
            "scheduled_time": "2026-06-13T12:00:00Z",
            "reason": "rough_day",
            "suggested_message": "How are you holding up?",
            "actual_response": data["actual_response"],
            "effectiveness": data["effectiveness"],
            "created": "2026-06-13T10:00:00Z"
        }

    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)

    headers = {"Authorization": "Bearer fake_token"}
    # Test positive reply text estimating effectiveness = 5
    response = client.post(
        "/api/ai/proactive-checkins/checkin_xyz/respond",
        json={"actual_response": "I feel much better and calm, thank you!"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["actual_response"] == "I feel much better and calm, thank you!"
    assert data["effectiveness"] == 5
    assert updated_payload == {"actual_response": "I feel much better and calm, thank you!", "effectiveness": 5}
