from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_emotion_trends_requires_auth():
    response = client.get("/api/ai/emotion-trends")
    assert response.status_code == 401

def test_emotion_trends_success(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")

    now = datetime.now(timezone.utc)
    
    # Mock mood logs
    mock_mood_logs = [
        # W1: 2 days ago
        {
            "id": "log_1",
            "user_id": "user_123",
            "level": 6,
            "emotions": ["anxiety", "calm"],
            "note": "Felt anxious about work but calmed down after breathing.",
            "created": (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        },
        # W2: 9 days ago
        {
            "id": "log_2",
            "user_id": "user_123",
            "level": 4,
            "emotions": ["anxiety"],
            "note": "Work is very stressful.",
            "created": (now - timedelta(days=9)).strftime("%Y-%m-%d %H:%M:%S")
        }
    ]

    async def fake_list_records(collection, token=None, params=None):
        if collection == "mood_logs":
            return {
                "items": mock_mood_logs,
                "totalItems": len(mock_mood_logs)
            }
        elif collection == "emotion_insights":
            # Return empty to trigger CREATE
            return {
                "items": [],
                "totalItems": 0
            }
        return {"items": [], "totalItems": 0}

    created_insights = []
    async def fake_create_record(collection, data, token=None):
        if collection == "emotion_insights":
            created_insights.append(data)
            return {"id": "mock_insight_id"}
        return {"id": "mock_id"}

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        # Mock OpenRouter return JSON
        return '{"anxiety": "after work stress", "calm": "during morning breathing"}'

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)
    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.get("/api/ai/emotion-trends", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "dominant_emotions" in data
    assert "anxiety" in data["dominant_emotions"]
    
    assert "trending_emotions" in data
    assert len(data["trending_emotions"]) >= 2
    
    anxiety_trend = next(item for item in data["trending_emotions"] if item["emotion"] == "anxiety")
    # W1: 1 anxiety count, W2: 1 anxiety count -> c1 == c2 -> stable
    assert anxiety_trend["trend"] == "stable"
    assert anxiety_trend["frequency"] == 2
    
    # Check created insights database payloads
    assert len(created_insights) >= 2
    anxiety_db = next(item for item in created_insights if item["emotion"] == "anxiety")
    assert anxiety_db["frequency"] == 2
    assert anxiety_db["trend"] == "stable"
