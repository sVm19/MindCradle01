import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.ai import _summarize_conversation_background

client = TestClient(app)

def test_conversations_timeline_requires_auth():
    response = client.get("/api/ai/conversations")
    assert response.status_code == 401

def test_active_conversation_requires_auth():
    response = client.get("/api/ai/conversations/active")
    assert response.status_code == 401

def test_end_conversation_requires_auth():
    response = client.post("/api/ai/conversations/convo_123/end")
    assert response.status_code == 401

def test_check_in_requires_auth():
    response = client.get("/api/ai/check-in")
    assert response.status_code == 401

def test_get_conversations_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "ai_conversations"
        assert 'user_id="user_123"' in params["filter"]
        return {
            "items": [
                {
                    "id": "convo_1",
                    "user_id": "user_123",
                    "created": "2026-06-13T00:00:00Z",
                    "updated": "2026-06-13T01:00:00Z",
                    "summary": "- Struggled with stress.\n- Breathing helped.",
                    "key_points": ["stress", "breathing"],
                    "follow_up_needed": True,
                    "follow_up_date": "2026-06-14",
                    "emotional_journey": "stressed → grounded",
                    "is_active": False
                }
            ],
            "totalItems": 1
        }

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/api/ai/conversations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "convo_1"
    assert data[0]["summary"] == "- Struggled with stress.\n- Breathing helped."
    assert data[0]["emotional_journey"] == "stressed → grounded"
    assert data[0]["is_active"] is False

def test_get_active_conversation_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "ai_conversations"
        assert "is_active=true" in params["filter"]
        return {
            "items": [
                {
                    "id": "convo_active",
                    "user_id": "user_123",
                    "created": "2026-06-13T00:00:00Z",
                    "updated": "2026-06-13T01:00:00Z",
                    "summary": "Active session",
                    "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there"}],
                    "is_active": True
                }
            ],
            "totalItems": 1
        }

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/api/ai/conversations/active", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert data["id"] == "convo_active"
    assert data["messages"] == [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there"}]
    assert data["is_active"] is True

def test_end_conversation_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    updated_record_id = None
    updated_payload = None

    async def fake_update_record(collection, record_id, data, token=None):
        assert collection == "ai_conversations"
        nonlocal updated_record_id, updated_payload
        updated_record_id = record_id
        updated_payload = data
        return {"id": record_id}

    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)

    # Mock background task itself to not execute or do anything
    monkeypatch.setattr("app.routers.ai._summarize_conversation_background", lambda token, convo_id: None)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/conversations/convo_abc/end", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"ended": True}
    assert updated_record_id == "convo_abc"
    assert updated_payload == {"is_active": False}

def test_check_in_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "ai_conversations"
        assert "follow_up_needed=true" in params["filter"]
        return {
            "items": [
                {
                    "id": "convo_follow",
                    "user_id": "user_123",
                    "summary": "User had work stress. Breathing exercise helped.",
                    "follow_up_needed": True,
                    "follow_up_date": "2026-06-13"
                }
            ],
            "totalItems": 1
        }

    updated_data = {}
    async def fake_update_record(collection, record_id, data, token=None):
        assert collection == "ai_conversations"
        assert record_id == "convo_follow"
        nonlocal updated_data
        updated_data = data
        return {"id": record_id}

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        return "I've been thinking about your work stress—how did the breathing exercises help you?"

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)
    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/api/ai/check-in", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["check_in_message"] == "I've been thinking about your work stress—how did the breathing exercises help you?"
    assert data["conversation_id"] == "convo_follow"
    assert updated_data == {"follow_up_needed": False}

@pytest.mark.anyio
async def test_summarize_conversation_background(monkeypatch):
    async def fake_get_record(collection, record_id, token=None):
        assert collection == "ai_conversations"
        return {
            "id": record_id,
            "messages": [
                {"role": "user", "content": "I am anxious about my meeting tomorrow"},
                {"role": "assistant", "content": "I hear you. Let's try box breathing."},
                {"role": "user", "content": "That breathing exercise helped me calm down."}
            ]
        }

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.3, max_tokens=400):
        return """{
            "summary": "- User struggled with meeting anxiety.\\n- Box breathing helped them calm down.\\n- Check in on Friday.",
            "key_points": ["meeting anxiety", "box breathing"],
            "follow_up_needed": true,
            "follow_up_date": "2026-06-19",
            "emotional_journey": "anxious → calm"
        }"""

    updated_payload = None
    async def fake_update_record(collection, record_id, data, token=None):
        assert collection == "ai_conversations"
        assert record_id == "convo_xyz"
        nonlocal updated_payload
        updated_payload = data
        return {"id": record_id}

    monkeypatch.setattr("app.routers.ai.pb.get_record", fake_get_record)
    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)
    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)

    await _summarize_conversation_background("fake_token", "convo_xyz")

    assert updated_payload is not None
    assert "box breathing" in updated_payload["summary"].lower()
    assert updated_payload["key_points"] == ["meeting anxiety", "box breathing"]
    assert updated_payload["follow_up_needed"] is True
    assert updated_payload["follow_up_date"] == "2026-06-19"
    assert updated_payload["emotional_journey"] == "anxious → calm"
