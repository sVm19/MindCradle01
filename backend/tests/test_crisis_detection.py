from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_profile_get_and_patch(monkeypatch):
    # Mock authentication and profile database calls
    monkeypatch.setattr("app.routers.profile.extract_user_id", lambda token: "user_123")
    
    profile_db = {
        "id": "profile_abc",
        "user_id": "user_123",
        "unlocked_badges": ["first-light"],
        "badge_history": [],
        "emergency_contact": "Spouse (+1-555-0100)",
        "created": "2026-06-13T00:00:00Z"
    }
    
    async def fake_list_records(collection, token=None, params=None):
        return {"items": [profile_db], "totalItems": 1}
        
    async def fake_update_record(collection, record_id, data, token=None):
        profile_db.update(data)
        return profile_db
        
    monkeypatch.setattr("app.routers.profile.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.profile.pb.update_record", fake_update_record)
    
    # 1. Test GET /api/profile
    response = client.get("/api/profile", headers={"Authorization": "Bearer demo_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["emergency_contact"] == "Spouse (+1-555-0100)"
    
    # 2. Test PATCH /api/profile
    response = client.patch(
        "/api/profile",
        headers={"Authorization": "Bearer demo_token"},
        json={"emergency_contact": "Therapist (+1-555-9999)"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["emergency_contact"] == "Therapist (+1-555-9999)"


def test_detect_crisis_route_critical(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")
    
    logged_flags = []
    async def fake_create_record(collection, data, token=None):
        if collection == "crisis_flags":
            logged_flags.append(data)
        return {"id": "flag_123", **data}
        
    async def fake_list_records(collection, token=None, params=None):
        return {"items": [], "totalItems": 0}
        
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    
    # Test high-risk keywords triggers Level 4 immediately
    response = client.post(
        "/api/ai/detect-crisis",
        headers={"Authorization": "Bearer demo_token"},
        json={"conversation_id": "new", "message": "I want to kill myself"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["severity_level"] == 4
    assert len(logged_flags) == 1
    assert logged_flags[0]["severity_level"] == 4


def test_chat_route_crisis_safety_override(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")
    
    logged_flags = []
    updated_convos = []
    
    async def fake_create_record(collection, data, token=None):
        if collection == "crisis_flags":
            logged_flags.append(data)
        elif collection == "ai_conversations":
            return {"id": "convo_123", **data}
        return {"id": "record_123", **data}
        
    async def fake_update_record(collection, record_id, data, token=None):
        if collection == "ai_conversations":
            updated_convos.append(data)
        return {"id": record_id, **data}
        
    async def fake_get_record(collection, record_id, token=None):
        return {"id": record_id, "messages": []}
        
    async def fake_list_records(collection, token=None, params=None):
        return {"items": [], "totalItems": 0}
        
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)
    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)
    monkeypatch.setattr("app.routers.ai.pb.get_record", fake_get_record)
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    
    # Post a message that triggers Level 4
    response = client.post(
        "/api/ai/chat",
        headers={"Authorization": "Bearer demo_token"},
        json={"conversation_id": "new", "message": "I am planning to end it all tonight."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["crisis_detected"] is True
    assert data["crisis_severity"] == 4
    assert "988" in data["reply"]
    assert "741741" in data["reply"]
    assert len(logged_flags) == 1
    assert logged_flags[0]["severity_level"] == 4


def test_chat_route_crisis_level2_prompt_injection(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")
    
    captured_system_prompt = None
    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        nonlocal captured_system_prompt
        if system_prompt and "memory processor" in system_prompt:
            return "{}"
        captured_system_prompt = system_prompt
        return "I hear you. Have you thought about speaking with someone?"
        
    async def fake_detect_crisis_llm(messages, system_prompt=None, temperature=0.0, max_tokens=300):
        # Mocking the classification call to return LEVEL 2
        return '{"severity_level": 2, "red_flags_detected": ["persistent hopelessness"], "reasoning": "User feels empty"}'
        
    # Hook into openrouter
    async def fake_openrouter_chat_completion(messages, system_prompt=None, **kwargs):
        temp = kwargs.get("temperature", 0.7)
        max_t = kwargs.get("max_tokens", 180)
        if system_prompt and "MindCradle's safety classification engine" in system_prompt:
            return await fake_detect_crisis_llm(messages, system_prompt=system_prompt, temperature=temp, max_tokens=max_t)
        return await fake_chat_completion(messages, system_prompt=system_prompt, temperature=temp, max_tokens=max_t)
        
    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_openrouter_chat_completion)
    
    async def fake_list_records(collection, token=None, params=None):
        return {"items": [], "totalItems": 0}
        
    async def fake_create_record(collection, data, token=None):
        return {"id": "abc", **data}
        
    async def fake_get_record(collection, record_id, token=None):
        return {"id": record_id, "messages": []}

    async def fake_update_record(collection, record_id, data, token=None):
        return {"id": record_id, **data}
        
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)
    monkeypatch.setattr("app.routers.ai.pb.get_record", fake_get_record)
    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)
    
    response = client.post(
        "/api/ai/chat",
        headers={"Authorization": "Bearer demo_token"},
        json={"conversation_id": "convo_123", "message": "Nothing matters anymore. I feel completely empty."}
    )
    assert response.status_code == 200
    assert captured_system_prompt is not None
    assert "SAFETY DIRECTION" in captured_system_prompt
    assert "hopelessness" in captured_system_prompt.lower()


def test_detect_crisis_keywords_classifier():
    from app.routers.ai import detect_crisis_keywords

    # 1. Critical keywords
    res = detect_crisis_keywords("I want to kill myself today.")
    assert res["detected"] is True
    assert res["severity"] == "CRITICAL"

    res = detect_crisis_keywords("Planning to overdose on sleeping pills.")
    assert res["detected"] is True
    assert res["severity"] == "CRITICAL"

    # 2. High-risk keywords
    res = detect_crisis_keywords("Feeling completely hopeless and suicidal.")
    assert res["detected"] is True
    assert res["severity"] == "HIGH"

    res = detect_crisis_keywords("I just want to self harm.")
    assert res["detected"] is True
    assert res["severity"] == "HIGH"

    # 3. Safe/Normal keywords
    res = detect_crisis_keywords("I had a stressful day at work.")
    assert res["detected"] is False
    assert res["severity"] is None


def test_crisis_status_endpoint(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    # Mock critical crisis flag exists
    async def fake_list_records(collection, token=None, params=None):
        if collection == "crisis_flags":
            return {"items": [{"id": "flag_1"}], "totalItems": 1}
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    response = client.get("/api/aria/crisis-status", headers={"Authorization": "Bearer demo_token"})
    assert response.status_code == 200
    assert response.json()["has_critical_crisis"] is True


def test_crisis_resolve_endpoint(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    resolved_records = []

    async def fake_list_records(collection, token=None, params=None):
        if collection == "crisis_flags":
            return {"items": [{"id": "flag_1", "admin_reviewed": False}], "totalItems": 1}
        return {"items": [], "totalItems": 0}

    async def fake_update_record(collection, record_id, data, token=None):
        if collection == "crisis_flags":
            resolved_records.append((record_id, data))
        return {"id": record_id, **data}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)

    response = client.post("/api/aria/crisis-resolve", headers={"Authorization": "Bearer demo_token"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert len(resolved_records) == 1
    assert resolved_records[0][0] == "flag_1"
    assert resolved_records[0][1]["admin_reviewed"] is True


def test_emergency_contact_warning_notification(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    logged_flags = []
    contact_notified = False

    async def fake_create_record(collection, data, token=None):
        if collection == "crisis_flags":
            logged_flags.append(data)
        return {"id": "rec_123", **data}

    async def fake_list_records(collection, token=None, params=None):
        if collection == "user_profiles":
            # Profile has contact and notify_on_crisis = True
            return {
                "items": [{
                    "id": "profile_123",
                    "user_id": "user_123",
                    "emergency_contact": "emergency@contact.com",
                    "notify_on_crisis": True
                }]
            }
        return {"items": [], "totalItems": 0}

    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    # Trigger a critical crisis chat request
    response = client.post(
        "/api/ai/chat",
        headers={"Authorization": "Bearer demo_token"},
        json={"conversation_id": "new", "message": "I want to kill myself"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["crisis_detected"] is True
    assert data["severity"] == "CRITICAL"
    assert len(logged_flags) == 1
    assert "emergency@contact.com" in logged_flags[0]["action_taken"]

