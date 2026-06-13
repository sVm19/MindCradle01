from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_learn_personality_requires_auth():
    response = client.post("/api/ai/learn-personality")
    assert response.status_code == 401

def test_learn_personality_not_enough_conversations(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "ai_conversations"
        return {
            "items": [
                {"id": "c1", "messages": []},
                {"id": "c2", "messages": []}
            ],
            "totalItems": 2
        }

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/learn-personality", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is False
    assert "At least 5 conversations" in data["message"]

def test_learn_personality_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        if collection == "ai_conversations":
            return {
                "items": [
                    {"id": f"c{i}", "messages": [{"role": "user", "content": "I feel stressed"}]} for i in range(5)
                ],
                "totalItems": 5
            }
        elif collection == "user_personality":
            return {"items": [], "totalItems": 0}
        return {"items": [], "totalItems": 0}

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        assert "personality profiler" in system_prompt.lower()
        return '{"communication_style": "action-first, concise", "preference_advice_type": "direct_advice", "response_length_preference": "short", "emotional_openness": "medium"}'

    created_payload = {}
    async def fake_create_record(collection, data, token=None):
        assert collection == "user_personality"
        nonlocal created_payload
        created_payload = data
        return {"id": "profile_123"}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/learn-personality", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["communication_style"] == "action-first, concise"
    assert data["preference_advice_type"] == "direct_advice"
    assert data["response_length_preference"] == "short"
    assert data["emotional_openness"] == "medium"

    assert created_payload["user"] == "user_123"
    assert created_payload["communication_style"] == "action-first, concise"
    assert created_payload["preference_advice_type"] == "direct_advice"


def test_chat_route_adapts_to_personality(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    captured_system_prompt = None
    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        nonlocal captured_system_prompt
        if system_prompt and "memory processor assistant" in system_prompt:
            return "{}"
        captured_system_prompt = system_prompt
        return "concise directive reply"

    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)

    async def fake_list_records(collection, token=None, params=None):
        if collection == "user_personality":
            return {
                "items": [
                    {
                        "user_id": "user_123",
                        "communication_style": "action-oriented, brief",
                        "preference_advice_type": "direct_advice",
                        "response_length_preference": "short",
                        "emotional_openness": "low"
                    }
                ],
                "totalItems": 1
            }
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post(
        "/api/ai/chat",
        json={"message": "What should I do now?", "response_type": "calm_support"},
        headers=headers
    )
    assert response.status_code == 200
    
    assert captured_system_prompt is not None
    # Verify personality data is in system prompt
    assert "Here is what you know about this user's personality:" in captured_system_prompt
    assert "action-oriented, brief" in captured_system_prompt
    assert "direct_advice" in captured_system_prompt
    assert "short" in captured_system_prompt
    assert "CRITICAL TONE ADJUSTMENT:" in captured_system_prompt
    assert "The user prefers direct advice. Be direct, action-oriented" in captured_system_prompt


def test_learn_personality_success_with_existing_profile(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        if collection == "ai_conversations":
            return {
                "items": [
                    {"id": f"c{i}", "messages": [{"role": "user", "content": "I feel stressed"}]} for i in range(5)
                ],
                "totalItems": 5
            }
        elif collection == "user_personality":
            return {
                "items": [
                    {
                        "id": "profile_123",
                        "user_id": "user_123",
                        "communication_style": "reflective, casual",
                        "preference_advice_type": "gentle_suggestions",
                        "response_length_preference": "medium",
                        "emotional_openness": "high"
                    }
                ],
                "totalItems": 1
            }
        return {"items": [], "totalItems": 0}

    captured_system_prompt = ""
    captured_messages = []
    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        nonlocal captured_system_prompt, captured_messages
        captured_system_prompt = system_prompt
        captured_messages = messages
        return '{"communication_style": "reflective, casual, but opening up more", "preference_advice_type": "gentle_suggestions", "response_length_preference": "medium", "emotional_openness": "high"}'

    updated_payload = {}
    async def fake_update_record(collection, record_id, data, token=None):
        assert collection == "user_personality"
        assert record_id == "profile_123"
        nonlocal updated_payload
        updated_payload = data
        return {"id": "profile_123"}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)
    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/learn-personality", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["communication_style"] == "reflective, casual, but opening up more"
    assert "reflective, casual" in captured_messages[0]["content"]
    assert "Previous User Personality Profile" in captured_messages[0]["content"]
    assert updated_payload["communication_style"] == "reflective, casual, but opening up more"


def test_get_user_personality_requires_auth():
    response = client.get("/api/ai/user-personality")
    assert response.status_code == 401


def test_get_user_personality_not_found(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "user_personality"
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/api/ai/user-personality", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is False
    assert "No personality profile found" in data["message"]


def test_get_user_personality_found(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "user_personality"
        return {
            "items": [
                {
                    "id": "profile_123",
                    "user_id": "user_123",
                    "communication_style": "action-oriented",
                    "preference_advice_type": "direct_advice",
                    "response_length_preference": "short",
                    "emotional_openness": "medium"
                }
            ],
            "totalItems": 1
        }

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/api/ai/user-personality", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["communication_style"] == "action-oriented"
    assert data["preference_advice_type"] == "direct_advice"
    assert data["response_length_preference"] == "short"
    assert data["emotional_openness"] == "medium"

