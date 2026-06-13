import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_select_response_type_requires_auth():
    response = client.post("/api/ai/select-response-type", json={"message": "hello"})
    assert response.status_code == 401


def test_rule_1_very_low_mood_lonely(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_1")

    async def fake_list_records(collection, token=None, params=None):
        if collection == "mood_logs":
            return {
                "items": [{"level": 2, "emotions": ["lonely", "sad"], "created": "2026-06-12 12:00:00"}],
                "totalItems": 1
            }
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/select-response-type", json={"message": "I feel isolated"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == "COMPANY"
    assert "lonely" in data["reason"]


def test_rule_2_anxious_morning(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_2")

    # Force local hour to be morning (e.g. 8 AM)
    class FakeDateTime:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 6, 12, 8, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.routers.ai.datetime", FakeDateTime)

    async def fake_list_records(collection, token=None, params=None):
        if collection == "mood_logs":
            return {
                "items": [{"level": 5, "emotions": ["anxious"], "created": "2026-06-12 12:00:00"}],
                "totalItems": 1
            }
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/select-response-type", json={"message": "I'm stressed out"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == "ACTION"
    assert "anxious" in data["reason"]


def test_rule_3_work_stress_theme(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_3")

    async def fake_list_records(collection, token=None, params=None):
        if collection == "conversation_themes":
            return {
                "items": [
                    {"theme": "Work Stress"},
                    {"theme": "Work Stress"},
                    {"theme": "Work Stress"}
                ],
                "totalItems": 3
            }
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/select-response-type", json={"message": "hello"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == "INSIGHT"
    assert "theme mentioned" in data["reason"]


def test_rule_4_similar_situation_reminder(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_4")

    async def fake_list_records(collection, token=None, params=None):
        if collection == "user_memory_insights":
            return {
                "items": [
                    {
                        "situation": "Sleep anxiety before exams",
                        "what_helped": "Wind Down meditation"
                    }
                ],
                "totalItems": 1
            }
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/select-response-type", json={"message": "I have exams coming up and cannot sleep"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == "REMINDER"
    assert "reminding user" in data["reason"]


def test_fallback_highest_rated_historic(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_5")

    async def fake_list_records(collection, token=None, params=None):
        if collection == "advice_effectiveness":
            return {
                "items": [
                    {"conversation_id": "c1", "help_rating": 3},
                    {"conversation_id": "c2", "help_rating": 1}
                ],
                "totalItems": 2
            }
        elif collection == "ai_conversations":
            return {
                "items": [
                    {"id": "c1", "type": "REFLECTION"},
                    {"id": "c2", "type": "ACTION"}
                ],
                "totalItems": 2
            }
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/select-response-type", json={"message": "hello"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == "REFLECTION"
    assert "highest rated" in data["reason"]


def test_chat_integration_auto_selection(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_6")

    captured_system_prompt = None

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        nonlocal captured_system_prompt
        if system_prompt and "personality profiler" in system_prompt:
            return '{"communication_style": "reflective", "preference_advice_type": "gentle_suggestions"}'
        if system_prompt and "memory processor" in system_prompt:
            return '{}'
        captured_system_prompt = system_prompt
        return "I remember you mentioned seeking calm earlier."

    async def fake_list_records(collection, token=None, params=None):
        # Force rule 1 (low mood + lonely) to select COMPANY
        if collection == "mood_logs":
            return {
                "items": [{"level": 2, "emotions": ["lonely"], "created": "2026-06-12 12:00:00"}],
                "totalItems": 1
            }
        return {"items": [], "totalItems": 0}

    created_records = {}
    async def fake_create_record(collection, data, token=None):
        created_records[collection] = data
        return {"id": "mock_id"}

    updated_records = {}
    async def fake_update_record(collection, record_id, data, token=None):
        updated_records[collection] = data
        return {"id": record_id, **data}

    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)
    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)

    headers = {"Authorization": "Bearer fake_token"}
    # Note: no response_type passed in json body
    response = client.post("/api/ai/chat", json={"message": "I feel lonely today"}, headers=headers)
    
    assert response.status_code == 200
    
    # Assert system prompt adapted to COMPANY
    assert captured_system_prompt is not None
    assert "COMPANY response style" in captured_system_prompt
    assert "Tell me more. I'm here." in captured_system_prompt
    
    # Assert saved conversation type is COMPANY
    assert updated_records["ai_conversations"]["type"] == "COMPANY"
