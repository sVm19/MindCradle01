from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_themes_routes_require_auth():
    response1 = client.post("/api/ai/extract-themes", json={"conversation_id": "convo_1"})
    assert response1.status_code == 401

    response2 = client.get("/api/ai/conversation-themes")
    assert response2.status_code == 401

def test_extract_themes_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_get_record(collection, record_id, token=None):
        assert collection == "ai_conversations"
        assert record_id == "convo_123"
        return {
            "id": "convo_123",
            "messages": [
                {"role": "user", "content": "I feel very stressed about my work tasks"},
                {"role": "assistant", "content": "Take a breath, tell me what tasks."}
            ]
        }

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        assert "memory extractor" in system_prompt.lower()
        return '{"theme": "Work Stress", "theme_category": "stress", "mentioned_emotions": ["stressed"], "solutions_tried": ["breathing"]}'

    created_payload = {}
    async def fake_create_record(collection, data, token=None):
        assert collection == "conversation_themes"
        nonlocal created_payload
        created_payload = data
        return {"id": "theme_insight_1"}

    monkeypatch.setattr("app.routers.ai.pb.get_record", fake_get_record)
    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/ai/extract-themes", json={"conversation_id": "convo_123"}, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["theme"] == "Work Stress"
    assert data["theme_category"] == "stress"
    assert "stressed" in data["mentioned_emotions"]
    assert "breathing" in data["solutions_tried"]

    assert created_payload["theme"] == "Work Stress"
    assert created_payload["conversation_id"] == "convo_123"
    assert created_payload["user"] == "user_123"


def test_get_conversation_themes(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    async def fake_list_records(collection, token=None, params=None):
        assert collection == "conversation_themes"
        return {
            "items": [
                {"id": "t1", "theme": "Anxiety", "theme_category": "anxiety"},
                {"id": "t2", "theme": "Anxiety", "theme_category": "anxiety"},
                {"id": "t3", "theme": "Sleep", "theme_category": "sleep"}
            ],
            "totalItems": 3
        }

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/api/ai/conversation-themes", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    assert "frequencies" in data
    assert len(data["frequencies"]) == 2
    
    anxiety_freq = next(f for f in data["frequencies"] if f["theme"] == "Anxiety")
    sleep_freq = next(f for f in data["frequencies"] if f["theme"] == "Sleep")
    
    assert anxiety_freq["count"] == 2
    assert sleep_freq["count"] == 1
