from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_morning_ritual_route_exists():
    response = client.post("/api/rituals/morning", json={})
    assert response.status_code != 404


def test_morning_ritual_payload_is_accepted(monkeypatch):
    async def fake_create_record(collection, data, token=None):
        assert collection == "morning_rituals"
        assert data["forecast"] == "good"
        assert data["activity_type"] == "coherence-breathing"
        return {"id": "ritual_1"}

    monkeypatch.setattr("app.routers.rituals.pb.create_record", fake_create_record)

    response = client.post(
        "/api/rituals/morning",
        json={
            "forecast": "good",
            "intention": "My lunch break",
            "activityType": "coherence-breathing",
            "completedAt": "2026-04-29T06:42:00",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"id": "ritual_1", "saved": True}


def test_winddown_ritual_payload_is_accepted(monkeypatch):
    async def fake_create_record(collection, data, token=None):
        assert collection == "wind_down_rituals"
        assert data["release_item"] == "Tomorrow&#x27;s to-do list"
        assert data["audio_choice"] == "story"
        return {"id": "ritual_2"}

    monkeypatch.setattr("app.routers.rituals.pb.create_record", fake_create_record)

    response = client.post(
        "/api/rituals/winddown",
        json={
            "releaseItem": "Tomorrow's to-do list",
            "gratitudes": ["Tea", "Music", "Rain"],
            "audioChoice": "story",
            "timer": "30 min",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"id": "ritual_2", "saved": True}
