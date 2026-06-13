from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_engagement_metrics_calculations(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")
    
    # 1. Setup mock data
    now = datetime.now(timezone.utc)
    t1 = (now - timedelta(minutes=10)).isoformat()
    t2 = (now - timedelta(minutes=6)).isoformat()
    t3 = (now - timedelta(minutes=5)).isoformat()
    t4 = now.isoformat()
    
    mock_messages = [
        {"role": "user", "content": "I feel anxious", "timestamp": t1},
        {"role": "assistant", "content": "Let's do a breathing exercise.", "timestamp": t2},
        {"role": "user", "content": "Okay, that helped.", "timestamp": t3},
        {"role": "assistant", "content": "Great! Try journaling too.", "timestamp": t4}
    ]
    
    convo_mock = {
        "id": "convo_123",
        "user_id": "user_123",
        "messages": mock_messages,
        "emotional_journey": "anxious → grounded → calm",
        "created": (now - timedelta(hours=25)).isoformat(),
        "updated": now.isoformat()
    }
    
    # Create subsequent conversation to verify return_time_hours calculation
    next_convo_mock = {
        "id": "convo_456",
        "user_id": "user_123",
        "messages": [{"role": "user", "content": "Hello", "timestamp": (now + timedelta(hours=4)).isoformat()}],
        "created": (now + timedelta(hours=4)).isoformat(),
        "updated": (now + timedelta(hours=4)).isoformat()
    }
    
    # Create journal entry completed within 2 hours after convo to verify suggestion_followed
    journal_mock = {
        "id": "journal_1",
        "user_id": "user_123",
        "created": (now + timedelta(minutes=30)).isoformat()
    }
    
    # Database calls mock
    created_metrics = []
    
    async def fake_get_record(collection, record_id, token=None):
        if record_id == "convo_123":
            return convo_mock
        raise Exception("Not found")
        
    async def fake_list_records(collection, token=None, params=None):
        if collection == "journal_entries":
            return {"items": [journal_mock], "totalItems": 1}
        elif collection == "morning_rituals" or collection == "wind_down_rituals":
            return {"items": [], "totalItems": 0}
        elif collection == "ai_conversations":
            return {"items": [convo_mock, next_convo_mock], "totalItems": 2}
        elif collection == "engagement_metrics":
            return {"items": [], "totalItems": 0}
        return {"items": [], "totalItems": 0}
        
    async def fake_create_record(collection, data, token=None):
        if collection == "engagement_metrics":
            created_metrics.append(data)
        return {"id": "metrics_1", **data}
        
    monkeypatch.setattr("app.routers.ai.pb.get_record", fake_get_record)
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)
    
    # 2. Test POST /api/ai/track-engagement
    response = client.post(
        "/api/ai/track-engagement",
        headers={"Authorization": "Bearer demo_token"},
        json={"conversation_id": "convo_123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == "convo_123"
    assert len(created_metrics) == 1
    
    # Verify calculated values
    metric = created_metrics[0]
    # user responded at t3 to assistant's message at t2. Diff = 1 min = 60s
    assert metric["user_response_time"] == 60
    # journal entry was completed within 2 hours
    assert metric["suggestion_followed"] is True
    # next conversation started 4 hours after convo_123 completion
    assert metric["return_time_hours"] == 4
    # anxious -> calm shift = 3 - (-4) = 7
    assert metric["sentiment_shift"] == 7


def test_engagement_stats_aggregation(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_123")
    
    mock_metrics = [
        {
            "id": "m1",
            "conversation_id": "convo_1",
            "user_response_time": 45,
            "suggestion_followed": True,
            "return_time_hours": 12,
            "sentiment_shift": 7
        },
        {
            "id": "m2",
            "conversation_id": "convo_2",
            "user_response_time": 120,
            "suggestion_followed": False,
            "return_time_hours": 36,
            "sentiment_shift": 2
        }
    ]
    
    mock_convos = [
        {
            "id": "convo_1",
            "type": "VALIDATION",
            "context_used": {"is_personalized": True, "referenced_past_context": True}
        },
        {
            "id": "convo_2",
            "type": "ACTION",
            "context_used": {"is_personalized": False, "referenced_past_context": False}
        }
    ]
    
    async def fake_list_records(collection, token=None, params=None):
        if collection == "engagement_metrics":
            return {"items": mock_metrics, "totalItems": 2}
        elif collection == "ai_conversations":
            return {"items": mock_convos, "totalItems": 2}
        return {"items": [], "totalItems": 0}
        
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    
    # Test GET /api/ai/engagement-stats
    response = client.get("/api/ai/engagement-stats", headers={"Authorization": "Bearer demo_token"})
    assert response.status_code == 200
    data = response.json()
    
    # Overall averages
    # avg_response_time = (45 + 120) / 2 = 82.5s
    assert data["avg_response_time"] == 82.5
    # returns: 12h (under 24h), 36h (over 24h). 1 out of 2 = 50%
    assert data["return_rate_24h"] == 50.0
    
    # A/B Tests
    tests = {t["test_name"]: t for t in data["ab_tests"]}
    assert "Memory References vs No Memory References" in tests
    assert "Validating before Advising vs Direct Action-first" in tests
    
    # Convo Type Engagement
    convo_types = {t["convo_type"]: t for t in data["convo_type_engagement"]}
    assert "VALIDATION" in convo_types
    assert "ACTION" in convo_types
