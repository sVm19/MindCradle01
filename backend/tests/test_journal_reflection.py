from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_journal_reflection_route_exists():
    response = client.post("/api/ai/journal-reflection", json={})
    assert response.status_code != 404

def test_journal_reflection_returns_mocked_or_actual_response(monkeypatch):
    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=350):
        return '{"reflection": "I see you\'re processing something difficult. That takes courage. Be gentle with yourself today.", "themes": ["Stress", "Fatigue"], "emotional_tone": "Tired but resilient"}'

    async def fake_list_records(collection, token=None, params=None):
        return {"items": [], "totalItems": 0}

    async def fake_create_record(collection, data, token=None):
        return {"id": "convo_1"}

    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    response = client.post(
        "/api/ai/journal-reflection",
        json={
            "journal_content": "I am feeling extremely overwhelmed by my workload lately. I need to take a break.",
            "user_id": "user_123"
        }
    )

    assert response.status_code == 200
    res_json = response.json()
    assert "reflection" in res_json
    assert res_json["reflection"] == "I see you're processing something difficult. That takes courage. Be gentle with yourself today."
    assert res_json["themes"] == ["Stress", "Fatigue"]
    assert res_json["emotional_tone"] == "Tired but resilient"

def test_journal_reflection_parsing_fallback(monkeypatch):
    async def fake_chat_completion_invalid_json(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=350):
        return "Invalid non-JSON text that triggers parsing failure"

    async def fake_list_records(collection, token=None, params=None):
        return {"items": [], "totalItems": 0}

    async def fake_create_record(collection, data, token=None):
        return {"id": "convo_1"}

    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion_invalid_json)
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    response = client.post(
        "/api/ai/journal-reflection",
        json={
            "journal_content": "This is a short test post.",
            "user_id": "user_123"
        }
    )

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["reflection"] == "I see you're processing something difficult. That takes courage. Be gentle with yourself today."
    assert res_json["themes"] == ["Self-reflection"]
    assert res_json["emotional_tone"] == "Thoughtful and introspective"

def test_save_journal_entry_with_reflection(monkeypatch):
    async def fake_create_record(collection, data, token=None):
        assert collection == "journal_entries"
        assert data["prompt"] == "Test prompt"
        assert data["content"] == "Test content"
        assert data["ai_reflection"] == "Test reflection text"
        return {"id": "journal_entry_1"}

    monkeypatch.setattr("app.routers.journal.pb.create_record", fake_create_record)

    response = client.post(
        "/api/journal",
        json={
            "prompt": "Test prompt",
            "content": "Test content",
            "ai_reflection": "Test reflection text"
        }
    )

    assert response.status_code == 200
    assert response.json() == {"id": "journal_entry_1", "saved": True}
