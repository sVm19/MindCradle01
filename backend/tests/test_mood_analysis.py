from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_mood_analysis_route_exists():
    response = client.post("/api/ai/mood-analysis", json={})
    assert response.status_code != 404

def test_mood_analysis_success_flow(monkeypatch):
    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=350):
        return '{"analysis": "Your mood seems stable and calm.", "pattern": "You feel better after stretching.", "suggestion": "Try yoga.", "mood_trend": "stable"}'

    async def fake_list_records(collection, token=None, params=None):
        return {"items": [], "totalItems": 0}

    async def fake_create_record(collection, data, token=None):
        return {"id": "convo_2"}

    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)
    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    response = client.post(
        "/api/ai/mood-analysis",
        json={
            "mood_data": [
                {"level": 8, "emotions": ["happy"], "date": "2026-06-10T12:00:00Z"},
                {"level": 6, "emotions": ["stressed"], "date": "2026-06-11T12:00:00Z"}
            ],
            "user_id": "user_456"
        }
    )

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["analysis"] == "Your mood seems stable and calm."
    assert res_json["pattern"] == "You feel better after stretching."
    assert res_json["suggestion"] == "Try yoga."
    assert res_json["mood_trend"] == "stable"
