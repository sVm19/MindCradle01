from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_track_help_requires_auth():
    response = client.post("/api/ai/track-help", json={
        "conversation_id": "convo_123",
        "advice_given": "breathing exercise",
        "help_rating": 3
    })
    assert response.status_code == 401

def test_track_help_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    created_payload = {}
    async def fake_create_record(collection, data, token=None):
        assert collection == "advice_effectiveness"
        nonlocal created_payload
        created_payload = data
        return {"id": "log_abc_123"}

    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post(
        "/api/ai/track-help",
        json={
            "conversation_id": "convo_123",
            "advice_given": "You should try coherence breathing exercises to calm your heart rate.",
            "help_rating": 3,
            "follow_up_mood": 8
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "log_abc_123"
    assert data["saved"] is True

    assert created_payload["user"] == "user_123"
    assert created_payload["conversation_id"] == "convo_123"
    assert created_payload["advice_given"] == "You should try coherence breathing exercises to calm your heart rate."
    assert created_payload["help_rating"] == 3
    assert created_payload["follow_up_mood"] == 8


def test_chat_route_includes_effective_advice(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    captured_system_prompt = None
    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        nonlocal captured_system_prompt
        if system_prompt and "memory processor assistant" in system_prompt:
            return "{}"
        captured_system_prompt = system_prompt
        return "Supportive response"

    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)

    async def fake_list_records(collection, token=None, params=None):
        if collection == "advice_effectiveness":
            return {
                "items": [
                    {
                        "advice_given": "coherence breathing exercise",
                        "help_rating": 3,
                        "user_id": "user_123"
                    },
                    {
                        "advice_given": "try journaling about this in your private entry",
                        "help_rating": 2,
                        "user_id": "user_123"
                    }
                ],
                "totalItems": 2
            }
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post(
        "/api/ai/chat",
        json={"message": "I feel stressed again", "response_type": "rough_day_support"},
        headers=headers
    )
    assert response.status_code == 200
    
    assert captured_system_prompt is not None
    # Verify that advice history was injected
    assert "Techniques that have helped this user in the past:" in captured_system_prompt
    assert "breathing exercise" in captured_system_prompt
    assert "journaling" in captured_system_prompt
    assert "success rate: 100%" in captured_system_prompt
