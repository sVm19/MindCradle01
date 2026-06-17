import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_privacy_accepted_anonymous():
    response = client.post(
        "/api/auth/privacy-accepted",
        json={"privacy_accepted": True}
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Privacy policy accepted anonymously"}


def test_privacy_accepted_creates_new(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    async def fake_list_records(collection, token=None, params=None):
        assert collection == "user_privacy_acceptance"
        return {"items": []}

    async def fake_create_record(collection, data, token=None):
        assert collection == "user_privacy_acceptance"
        assert data["user_id"] == "fake-user-id"
        assert data["privacy_accepted"] is True
        return {"id": "new_rec", "privacy_accepted": True}

    monkeypatch.setattr("app.routers.auth.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.auth.pb.create_record", fake_create_record)

    response = client.post(
        "/api/auth/privacy-accepted",
        headers={"Authorization": "Bearer test-token"},
        json={"privacy_accepted": True}
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}


def test_privacy_accepted_updates_existing(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    async def fake_list_records(collection, token=None, params=None):
        assert collection == "user_privacy_acceptance"
        return {"items": [{"id": "existing_rec", "privacy_accepted": False}]}

    async def fake_update_record(collection, record_id, data, token=None):
        assert collection == "user_privacy_acceptance"
        assert record_id == "existing_rec"
        assert data["privacy_accepted"] is True
        return {"id": "existing_rec", "privacy_accepted": True}

    monkeypatch.setattr("app.routers.auth.pb.list_records", fake_list_records)
    monkeypatch.setattr("app.routers.auth.pb.update_record", fake_update_record)

    response = client.post(
        "/api/auth/privacy-accepted",
        headers={"Authorization": "Bearer test-token"},
        json={"privacy_accepted": True}
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}


def test_check_privacy_unauthorized():
    response = client.get("/api/auth/check-privacy")
    assert response.status_code == 401


def test_check_privacy_found(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    async def fake_list_records(collection, token=None, params=None):
        assert collection == "user_privacy_acceptance"
        return {"items": [{"id": "rec_1", "privacy_accepted": True, "accepted_at": "2026-06-16T12:00:00Z"}]}

    monkeypatch.setattr("app.routers.auth.pb.list_records", fake_list_records)

    response = client.get(
        "/api/auth/check-privacy",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    assert response.json() == {"privacy_accepted": True, "accepted_at": "2026-06-16T12:00:00Z"}


def test_check_privacy_not_found(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    async def fake_list_records(collection, token=None, params=None):
        return {"items": []}

    monkeypatch.setattr("app.routers.auth.pb.list_records", fake_list_records)

    response = client.get(
        "/api/auth/check-privacy",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    assert response.json() == {"privacy_accepted": False, "accepted_at": None}


def test_get_privacy_policy():
    response = client.get("/api/auth/privacy-policy")
    assert response.status_code == 200
    assert "text" in response.json()
    assert "MindCradle" in response.json()["text"]


def test_withdraw_consent_success(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    # Mock resolving email
    async def fake_get_user_email(token):
        assert token == "test-token"
        return "user@example.com"
    monkeypatch.setattr("app.routers.auth.pb.get_user_email", fake_get_user_email)

    # Mock password verification
    async def fake_auth_with_password(email, password):
        assert email == "user@example.com"
        assert password == "valid-password"
        return {"token": "session-token"}
    monkeypatch.setattr("app.routers.auth.pb.auth_with_password", fake_auth_with_password)

    # Mock account deletion
    async def fake_delete_user_account(token):
        assert token == "test-token"
    monkeypatch.setattr("app.routers.auth.pb.delete_user_account", fake_delete_user_account)

    response = client.request(
        "DELETE",
        "/api/auth/withdraw-consent",
        headers={"Authorization": "Bearer test-token"},
        json={"password": "valid-password"}
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Account deleted"}


def test_withdraw_consent_incorrect_password(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")
    
    async def fake_get_user_email(token):
        return "user@example.com"
    monkeypatch.setattr("app.routers.auth.pb.get_user_email", fake_get_user_email)

    async def fake_auth_with_password(email, password):
        raise Exception("Invalid password")
    monkeypatch.setattr("app.routers.auth.pb.auth_with_password", fake_auth_with_password)

    response = client.request(
        "DELETE",
        "/api/auth/withdraw-consent",
        headers={"Authorization": "Bearer test-token"},
        json={"password": "wrong-password"}
    )
    assert response.status_code == 401
    assert "Incorrect password" in response.json()["detail"]
