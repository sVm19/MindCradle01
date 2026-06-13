import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_rich_context_chat_flow(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_rich_123")

    captured_system_prompt = None
    captured_messages = []

    async def fake_chat_completion(messages, system_prompt=None, temperature=0.7, top_p=0.9, max_tokens=180):
        nonlocal captured_system_prompt, captured_messages
        # Skip profiling calls which might run in the background
        if system_prompt and "personality profiler" in system_prompt:
            return '{"communication_style": "reflective", "preference_advice_type": "gentle_suggestions"}'
        if system_prompt and "memory processor" in system_prompt:
            return '{}'
        captured_system_prompt = system_prompt
        captured_messages = messages
        # Return a reply containing "remember" to satisfy the keyword heuristic
        return "I remember you said you like calm nights, let's try a wind down ritual."

    monkeypatch.setattr("app.routers.ai.openrouter_ai.chat_completion", fake_chat_completion)

    # Mock list_records for all collections queried in _build_user_context and chat
    async def fake_list_records(collection, token=None, params=None):
        if collection == "mood_logs":
            return {
                "items": [
                    {"id": "m1", "level": 3, "emotions": ["anxious", "sad"], "created": "2026-06-12 12:00:00"},
                    {"id": "m2", "level": 4, "emotions": ["anxious"], "created": "2026-06-11 12:00:00"}
                ],
                "totalItems": 2
            }
        elif collection == "ai_conversations":
            return {
                "items": [
                    {
                        "id": "convo_123",
                        "messages": [
                            {"role": "user", "content": "Hello ARIA"},
                            {"role": "assistant", "content": "Hello! How are you?"}
                        ],
                        "context_used": {"is_personalized": True, "referenced_past_context": True}
                    }
                ],
                "totalItems": 1
            }
        elif collection == "conversation_themes":
            return {
                "items": [
                    {"theme": "Anxiety", "theme_category": "stress"},
                    {"theme": "Anxiety", "theme_category": "stress"},
                    {"theme": "Sleep", "theme_category": "sleep"}
                ],
                "totalItems": 3
            }
        elif collection == "advice_effectiveness":
            return {
                "items": [
                    {"advice_given": "Try deep breathing", "help_rating": 3},
                    {"advice_given": "Write in journal", "help_rating": 2}
                ],
                "totalItems": 2
            }
        elif collection == "user_personality":
            return {
                "items": [
                    {
                        "communication_style": "reflective, casual",
                        "preference_advice_type": "gentle_suggestions",
                        "response_length_preference": "medium",
                        "emotional_openness": "high"
                    }
                ],
                "totalItems": 1
            }
        elif collection == "recovery_data":
            return {
                "items": [
                    {"recovery_days": 2},
                    {"recovery_days": 4}
                ],
                "totalItems": 2
            }
        elif collection in ["morning_rituals", "wind_down_rituals", "journal_entries"]:
            return {"items": [], "totalItems": 0}
        
        return {"items": [], "totalItems": 0}

    created_records = {}
    async def fake_create_record(collection, data, token=None):
        created_records[collection] = data
        return {"id": f"mock_rec_{collection}"}

    updated_records = {}
    async def fake_update_record(collection, record_id, data, token=None):
        updated_records[collection] = data
        return {"id": record_id}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)
    monkeypatch.setattr("app.routers.ai.pb.update_record", fake_update_record)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post(
        "/api/ai/chat",
        json={"message": "I feel anxious today", "response_type": "rough_day_support"},
        headers=headers
    )

    assert response.status_code == 200
    res_data = response.json()
    assert "I remember" in res_data["reply"]
    
    # Verify hyper-personalized prompt instructions were built
    assert captured_system_prompt is not None
    assert "PERSONALIZED USER BEHAVIOR PROFILE:" in captured_system_prompt
    assert "This user is dealing with anxiety." in captured_system_prompt
    assert "They prefer validation before solutions. Use warm, validating language. Ask before suggesting." in captured_system_prompt
    assert "They recover fastest with breathing exercise." in captured_system_prompt
    assert "Show deep curiosity about their inner world" in captured_system_prompt
    
    # Verify forced memory reference rule is in system prompt
    assert "CRITICAL CONTEXT INJECTION RULE:" in captured_system_prompt
    assert "You MUST explicitly include at least one memory reference" in captured_system_prompt
    assert "I remember you said [X] about this" in captured_system_prompt

    # Verify context_used logging payload
    saved_convo_payload = updated_records.get("ai_conversations") or created_records.get("ai_conversations")
    assert saved_convo_payload is not None
    context_used = saved_convo_payload["context_used"]
    assert context_used["is_personalized"] is True
    assert context_used["referenced_past_context"] is True
    assert context_used["context_summary"]["has_themes"] is True
    assert context_used["context_summary"]["has_personality"] is True
    assert context_used["context_summary"]["has_recovery"] is True


def test_track_help_engagement_metrics_logging(monkeypatch):
    monkeypatch.setattr("app.routers.ai.extract_user_id", lambda token: "user_rich_123")

    async def fake_list_records(collection, token=None, params=None):
        return {"items": [], "totalItems": 0}

    async def fake_get_record(collection, record_id, token=None):
        if collection == "ai_conversations":
            return {
                "id": record_id,
                "context_used": {
                    "is_personalized": True,
                    "referenced_past_context": True
                }
            }
        raise Exception("Not found")

    created_records = {}
    async def fake_create_record(collection, data, token=None):
        if collection not in created_records:
            created_records[collection] = []
        created_records[collection].append(data)
        return {"id": f"mock_{collection}_id"}

    monkeypatch.setattr("app.routers.ai.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.ai.pb.get_record", fake_get_record)
    monkeypatch.setattr("app.routers.ai.pb.create_record", fake_create_record)

    headers = {"Authorization": "Bearer fake_token"}
    response = client.post(
        "/api/ai/track-help",
        json={
            "conversation_id": "convo_123",
            "advice_given": "Take a deep breath",
            "help_rating": 3,
            "follow_up_mood": 8
        },
        headers=headers
    )

    assert response.status_code == 200
    assert "advice_effectiveness" in created_records
    assert "engagement_metrics" in created_records
    
    eng_record = created_records["engagement_metrics"][0]
    assert eng_record["conversation_id"] == "convo_123"
    assert eng_record["suggestion_followed"] is True
    # 8 - 5 = 3
    assert eng_record["sentiment_shift"] == 3
