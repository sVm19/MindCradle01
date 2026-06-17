import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_check_age_verified_true(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    async def fake_list_records(collection, token=None, params=None):
        assert collection == "user_age_verification"
        assert token == "test-token"
        return {"items": [{"id": "profile_1", "age_verified": True, "verified_at": "2026-06-16T12:00:00Z"}]}

    monkeypatch.setattr("app.routers.auth.pb.list_records", fake_list_records)

    response = client.get(
        "/api/auth/check-age-verified",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    assert response.json() == {"age_verified": True, "verified_at": "2026-06-16T12:00:00Z"}

def test_check_age_verified_false(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    async def fake_list_records(collection, token=None, params=None):
        return {"items": []}

    monkeypatch.setattr("app.routers.auth.pb.list_records", fake_list_records)

    response = client.get(
        "/api/auth/check-age-verified",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    assert response.json() == {"age_verified": False, "verified_at": None}

def test_verify_age_updates_existing(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    async def fake_list_records(collection, token=None, params=None):
        return {"items": [{"id": "profile_1", "age_verified": False}]}

    async def fake_update_record(collection, record_id, data, token=None):
        assert collection == "user_age_verification"
        assert record_id == "profile_1"
        assert data["age_verified"] is True
        return {"id": "profile_1", "age_verified": True}

    monkeypatch.setattr("app.routers.auth.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.auth.pb.update_record", fake_update_record)

    response = client.post(
        "/api/auth/verify-age",
        headers={"Authorization": "Bearer test-token"},
        json={"age_verified": True}
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "verified": True}

def test_verify_age_creates_new(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    async def fake_list_records(collection, token=None, params=None):
        return {"items": []}

    async def fake_create_record(collection, data, token=None):
        assert collection == "user_age_verification"
        assert data["age_verified"] is True
        return {"id": "new_profile", "age_verified": True}

    monkeypatch.setattr("app.routers.auth.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.auth.pb.create_record", fake_create_record)

    response = client.post(
        "/api/auth/verify-age",
        headers={"Authorization": "Bearer test-token"},
        json={"age_verified": True}
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "verified": True}
