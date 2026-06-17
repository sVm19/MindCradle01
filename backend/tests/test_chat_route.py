from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_route_requires_auth():
    response = client.post("/api/ai/chat", json={"message": "hello"})
    assert response.status_code == 401

def test_chat_route_crisis_handoff(monkeypatch):
    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/chat", json={"message": "I want to kill myself"}, headers=headers)
    assert response.status_code == 200
    reply = response.json()["reply"]
    assert "988" in reply or "741741" in reply

def test_chat_route_success(monkeypatch):
    # Mock extract_user_id to return a fixed mock user ID
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    # Mock openrouter chat completion to test prompt handling
    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        if not system_prompt:
            return "Standard response"
        if "rough day" in system_prompt.lower():
            return "I'm sorry to hear that. I'm here for you."
        elif "vent" in system_prompt.lower():
            return "It sounds like you're carrying a lot. What is making it different today?"
        elif "calm" in system_prompt.lower():
            return "Take a deep breath. Let's do a quick breathing exercise."
        return "Standard response"

    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)

    # Track collections queried
    queried_collections = []

    # Mock pocketbase service calls
    async def fake_list_records(collection, token=None, params=None):
        queried_collections.append(collection)
        if collection == "user_memory_insights":
            return {
                "items": [
                    {
                        "created": "2026-06-12 12:00:00",
                        "situation": "Had work stress",
                        "emotion": "anxious",
                        "what_helped": "breathing",
                        "follow_up": "Check in about work"
                    }
                ],
                "totalItems": 1
            }
        return {"items": [], "totalItems": 0}

    async def fake_create_record(collection, data, token=None):
        return {"id": "mock_convo_123"}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    headers = {"Authorization": "Bearer fake_token"}

    # 1. Standard chat message
    response = client.post("/api/ai/chat", json={"message": "hello"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["reply"] == "Standard response"
    assert response.json()["conversation_id"] == "mock_convo_123"
    assert "user_memory_insights" in queried_collections

    # 2. Rough day prompt
    response = client.post(
        "/api/ai/chat",
        json={"message": "I had a rough day", "response_type": "rough_day_support"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "I'm sorry to hear that. I'm here for you."

    # 3. Vent prompt
    response = client.post(
        "/api/ai/chat",
        json={"message": "I need to vent", "response_type": "active_listening"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "It sounds like you're carrying a lot. What is making it different today?"

    # 4. Calm prompt
    response = client.post(
        "/api/ai/chat",
        json={"message": "Help me calm down", "response_type": "calm_support"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "Take a deep breath. Let's do a quick breathing exercise."


def test_remember_context_route(monkeypatch):
    headers = {"Authorization": "Bearer fake_token"}
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_get_record(collection, record_id, token=None):
        return {"id": record_id, "messages": [{"role": "user", "content": "I had a hard day at work"}]}

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=250):
        return '{"situation": "Had a hard day at work", "emotion": "stressed", "what_helped": "evening ritual", "follow_up": "Check in about work"}'

    async def fake_create_record(collection, data, token=None):
        assert collection == "user_memory_insights"
        user_val = data.get("user") or data.get("user_id")
        assert user_val == "user_123"
        assert data["situation"] == "Had a hard day at work"
        assert data["emotion"] == "stressed"
        return {"id": "mock_insight_123"}

    monkeypatch.setattr("app.routers.ai.pb.get_record", fake_get_record)
    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    response = client.post(
        "/api/ai/remember-context",
        json={
            "conversation_id": "convo_123",
            "user_id": "user_123",
            "key_insight": "Had a hard day at work",
            "emotion": "stressed",
            "context_type": "rough_day_support"
        },
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["saved"] is True
    assert response.json()["id"] == "mock_insight_123"


def test_get_memory_insights(monkeypatch):
    headers = {"Authorization": "Bearer fake_token"}
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "user_memory_insights"
        assert 'user_id="user_123"' in params["filter"]
        return {
            "items": [
                {
                    "id": "insight_1",
                    "user_id": "user_123",
                    "conversation_id": "convo_1",
                    "situation": "Stressed about tests",
                    "what_happened": "Stressed about tests",
                    "emotion": "anxious",
                    "what_helped": "deep breathing",
                    "follow_up": "Check back later",
                    "context_type": "rough_day_support",
                    "date": "2026-06-12",
                    "created": "2026-06-12 12:00:00"
                }
            ]
        }

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    response = client.get("/api/ai/memory-insights", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "insight_1"
    assert data[0]["situation"] == "Stressed about tests"
    assert data[0]["emotion"] == "anxious"


def test_update_memory_insight(monkeypatch):
    headers = {"Authorization": "Bearer fake_token"}
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    updated_payload = {}
    async def fake_update_record(collection, record_id, data, token=None):
        assert collection == "user_memory_insights"
        assert record_id == "insight_1"
        nonlocal updated_payload
        updated_payload = data
        return {"id": record_id}

    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)

    response = client.put(
        "/api/ai/memory-insights/insight_1",
        json={"situation": "New situation", "emotion": "calmer"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["saved"] is True
    assert updated_payload["situation"] == "New situation"
    assert updated_payload["emotion"] == "calmer"
    assert updated_payload["what_happened"] == "New situation"


def test_delete_memory_insight(monkeypatch):
    headers = {"Authorization": "Bearer fake_token"}
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    deleted_id = None
    async def fake_delete_record(collection, record_id, token=None):
        assert collection == "user_memory_insights"
        nonlocal deleted_id
        deleted_id = record_id
        return True

    monkeypatch.setattr("app.routers.ai.pb.delete_record", fake_delete_record)

    response = client.delete("/api/ai/memory-insights/insight_1", headers=headers)
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert deleted_id == "insight_1"


def test_chat_route_memory_injection(monkeypatch):
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
        if collection == "user_memory_insights":
            return {
                "items": [
                    {
                        "id": "insight_1",
                        "user_id": "user_123",
                        "conversation_id": "convo_123",
                        "situation": "Felt overwhelmed about work",
                        "emotion": "overwhelmed, anxious",
                        "what_helped": "evening ritual",
                        "follow_up": "Follow up on work stress",
                        "context_type": "rough_day_support",
                        "created": "2026-06-12 12:00:00"
                    },
                    {
                        "id": "insight_2",
                        "user_id": "user_123",
                        "conversation_id": "convo_123",
                        "situation": "Felt overwhelmed about work again",
                        "emotion": "anxious",
                        "what_helped": "breathing",
                        "follow_up": "Check back later",
                        "context_type": "rough_day_support",
                        "created": "2026-06-12 13:00:00"
                    }
                ],
                "totalItems": 2
            }
        elif collection == "ai_conversations":
            return {
                "items": [
                    {
                        "id": "convo_123",
                        "messages": [
                            {"role": "user", "content": "I had a hard day"},
                            {"role": "assistant", "content": "Tell me more"}
                        ],
                        "updated": "2026-06-12 12:00:00"
                    }
                ],
                "totalItems": 1
            }
        elif collection == "mood_logs":
            return {
                "items": [
                    {
                        "level": 3,
                        "emotions": ["stressed", "anxious"],
                        "created": "2026-06-12 12:00:00"
                    }
                ],
                "totalItems": 1
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
    assert response.json()["reply"] == "Supportive response"
    
    assert captured_system_prompt is not None
    assert "Here's what you know about this user from past conversations:" in captured_system_prompt
    assert "anxious" in captured_system_prompt
    assert "overwhelmed" in captured_system_prompt
    assert "stressed" in captured_system_prompt
    assert "evening ritual" in captured_system_prompt
    assert "Felt overwhelmed about work" in captured_system_prompt
    assert "Struggles with occasional rough days" in captured_system_prompt


def test_chat_route_wellness_guardrail(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        return "Standard response"

    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)

    async def fake_list_records(collection, token=None, params=None):
        return {"items": [], "totalItems": 0}

    async def fake_create_record(collection, data, token=None):
        return {"id": "mock_convo_123"}

    async def fake_update_record(collection, record_id, data, token=None):
        return {"id": record_id}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)
    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)

    headers = {"Authorization": "Bearer fake_token"}

    # 1. ✅ "I'm feeling anxious" -> Allow
    response = client.post("/api/ai/chat", json={"message": "I'm feeling anxious"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["reply"] == "Standard response"
    assert "type" not in response.json() or response.json()["type"] != "rejected"

    # 2. ✅ "Help me sleep better" -> Allow
    response = client.post("/api/ai/chat", json={"message": "Help me sleep better"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["reply"] == "Standard response"

    # 3. ❌ "How do I write Python?" -> Reject
    response = client.post("/api/ai/chat", json={"message": "How do I write Python?"}, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert "support your mental wellness" in res_data["reply"]
    assert res_data["type"] == "rejected"
    assert res_data["reason"] == "off_topic"

    # 4. ❌ "What's the capital of France?" -> Reject
    response = client.post("/api/ai/chat", json={"message": "What's the capital of France?"}, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["type"] == "rejected"
    assert res_data["reason"] == "off_topic"

    # 5. ❌ "How do I build an app?" -> Reject and Trigger Rate Limit (3rd consecutive off-topic)
    response = client.post("/api/ai/chat", json={"message": "How do I build an app?"}, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert "paused" in res_data["reply"]
    assert res_data["type"] == "rate_limited"
    assert res_data["reason"] == "consecutive_off_topic"

    # 6. ❌ "I feel overwhelmed about work" -> Blocked because rate limit is active
    response = client.post("/api/ai/chat", json={"message": "I feel overwhelmed about work"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["type"] == "rate_limited"
    assert response.json()["reason"] == "consecutive_off_topic"

    # 7. Clear rate limit, then verify "I feel overwhelmed about work" is allowed
    from app.routers.ai import OFF_TOPIC_LIMITS
    OFF_TOPIC_LIMITS.clear()
    
    response = client.post("/api/ai/chat", json={"message": "I feel overwhelmed about work"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["reply"] == "Standard response"


def test_verify_age_endpoint_success(monkeypatch):
    headers = {"Authorization": "Bearer fake_token"}
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "user_age_verification"
        return {"items": []}

    created_payload = None
    async def fake_create_record(collection, data, token=None):
        nonlocal created_payload
        assert collection == "user_age_verification"
        created_payload = data
        return {"id": "record_123", **data}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    response = client.post("/api/aria/verify-age", json={"age_verified": True}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "age_verified": True}
    assert created_payload is not None
    assert created_payload["age_verified"] is True
    assert "verified_at" in created_payload


def test_age_verification_gate_checks(monkeypatch):
    from app.routers.ai import check_aria_age_verified
    app.dependency_overrides.pop(check_aria_age_verified, None)

    headers = {"Authorization": "Bearer fake_token"}
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    mock_profile_items = []
    async def fake_list_records(collection, token=None, params=None):
        if collection == "user_age_verification":
            return {"items": mock_profile_items, "totalItems": len(mock_profile_items)}
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        return "Standard response"
    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)

    # 1. No profile -> 403 Age verification required
    mock_profile_items = []
    response = client.post("/api/ai/chat", json={"message": "hello"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"] == "Age verification required"
    assert response.json()["code"] == "not_verified"

    # 2. Profile exists but not verified -> 403 Age verification required
    mock_profile_items = [{"age_verified": False, "verified_at": None}]
    response = client.post("/api/ai/chat", json={"message": "hello"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"] == "ARIA not available for users under 18"
    assert response.json()["code"] == "age_restricted"

    # 3. Profile verified but older than 30 days -> 403 Age verification expired
    from datetime import datetime, timedelta, timezone
    expired_time = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    mock_profile_items = [{"age_verified": True, "verified_at": expired_time}]
    response = client.post("/api/ai/chat", json={"message": "hello"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"] == "Age verification expired"
    assert response.json()["code"] == "expired"

    # 4. Profile verified and recent -> 200 OK
    recent_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    mock_profile_items = [{"age_verified": True, "verified_at": recent_time}]
    
    async def fake_create_record(collection, data, token=None):
        return {"id": "convo_123"}
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    response = client.post("/api/ai/chat", json={"message": "hello"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["reply"] == "Standard response"



