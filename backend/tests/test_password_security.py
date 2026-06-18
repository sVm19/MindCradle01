import os
import pytest

# Set up test env before importing config
os.environ["ENVIRONMENT"] = "development"
os.environ["JWT_SECRET_KEY"] = "test-access-secret-key-1234567890-test-key-access"
os.environ["JWT_REFRESH_SECRET_KEY"] = "test-refresh-secret-key-1234567890-test-key-refresh"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test"
os.environ["SUPABASE_JWT_SECRET"] = "test"

# Override default password settings for tests
os.environ["PASSWORD_MIN_LENGTH"] = "8"
os.environ["PASSWORD_REQUIRE_UPPERCASE"] = "true"
os.environ["PASSWORD_REQUIRE_NUMBER"] = "true"
os.environ["PASSWORD_REQUIRE_SPECIAL"] = "true"
os.environ["BCRYPT_ROUNDS"] = "4"  # Use fewer rounds for faster tests

from fastapi.testclient import TestClient
from app.main import app
from app.utils.security import (
    validate_password,
    hash_password,
    verify_password,
    get_deterministic_hash,
)

client = TestClient(app)

def test_password_validator():
    # Test min length
    assert validate_password("Short1!") is not None
    
    # Test require uppercase
    assert validate_password("lowercase1!") is not None
    
    # Test require number
    assert validate_password("NoNumber!") is not None
    
    # Test require special character
    assert validate_password("NoSpecial1") is not None
    
    # Test valid password
    assert validate_password("ValidPassword1!") is None


def test_signup_validation_rejections():
    # Test signup with weak password (too short)
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "test@example.com",
            "password": "Weak1!",
            "passwordConfirm": "Weak1!",
            "name": "Test User"
        }
    )
    assert response.status_code == 400
    assert "at least 8 characters" in response.json()["detail"]


def test_signup_and_login_success(monkeypatch):
    # Mock extract_user_id
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")

    # Mock Supabase create_user
    async def fake_create_user(data):
        assert data["email"] == "test_success@example.com"
        assert data["password"] == get_deterministic_hash("ValidPassword1!")
        return {"id": "fake-user-id"}
    monkeypatch.setattr("app.routers.auth.pb.create_user", fake_create_user)

    # Mock Supabase auth_with_password
    async def fake_auth_with_password(email, password):
        assert email == "test_success@example.com"
        assert password == get_deterministic_hash("ValidPassword1!")
        return {
            "token": "session-token",
            "record": {
                "id": "fake-user-id",
                "email": "test_success@example.com",
                "name": "Test User"
            }
        }
    monkeypatch.setattr("app.routers.auth.pb.auth_with_password", fake_auth_with_password)

    # Mock Supabase create_record for history table
    async def fake_create_record(collection, data, token=None):
        assert collection == "user_password_history"
        assert data["user_id"] == "fake-user-id"
        assert verify_password("ValidPassword1!", data["password_hash"])
        return {"id": "history-id"}
    monkeypatch.setattr("app.routers.auth.pb.create_record", fake_create_record)

    # Test signup
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "test_success@example.com",
            "password": "ValidPassword1!",
            "passwordConfirm": "ValidPassword1!",
            "name": "Test User"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "fake-user-id"
    assert data["email"] == "test_success@example.com"
    assert data["token"] != ""

    # Test login success
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test_success@example.com",
            "password": "ValidPassword1!"
        }
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == "fake-user-id"


def test_login_failure_is_generic(monkeypatch):
    # Mock Supabase auth_with_password failing
    async def fake_auth_with_password_fail(email, password):
        raise Exception("Supabase Auth Error")
    monkeypatch.setattr("app.routers.auth.pb.auth_with_password", fake_auth_with_password_fail)

    # Test login with bad password
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test_fail@example.com",
            "password": "WrongPassword1!"
        }
    )
    # Failure status code must be 401
    assert response.status_code == 401
    # Error message must be generic and not tell which part failed
    assert response.json()["detail"] == "Invalid email or password"


def test_password_reuse_history_prevention(monkeypatch):
    monkeypatch.setattr("app.routers.auth.extract_user_id", lambda t: "fake-user-id")

    # Mock get_user_email
    async def fake_get_user_email(token):
        return "test_history@example.com"
    monkeypatch.setattr("app.routers.auth.pb.get_user_email", fake_get_user_email)

    # Mock auth_with_password for current password validation
    async def fake_auth_with_password(email, password):
        assert password == get_deterministic_hash("CurrentPassword1!")
        return {"token": "token"}
    monkeypatch.setattr("app.routers.auth.pb.auth_with_password", fake_auth_with_password)

    # Mock list_records returning the past password hashes
    async def fake_list_records(collection, token=None, params=None):
        assert collection == "user_password_history"
        return {
            "items": [
                {"password_hash": hash_password("OldPassword1!")},
                {"password_hash": hash_password("OldPassword2!")},
                {"password_hash": hash_password("OldPassword3!")},
                {"password_hash": hash_password("OldPassword4!")},
                {"password_hash": hash_password("OldPassword5!")},
            ]
        }
    monkeypatch.setattr("app.routers.auth.pb.list_records", fake_list_records)

    # 1. Test change password with a password that matches one of the last 5
    response = client.post(
        "/api/auth/change-password",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "currentPassword": "CurrentPassword1!",
            "newPassword": "OldPassword3!"
        }
    )
    assert response.status_code == 400
    assert "Cannot reuse any of your last 5 passwords" in response.json()["detail"]

    # 2. Mock update_user and create_record for success test
    async def fake_update_user(token, data):
        assert data["password"] == get_deterministic_hash("BrandNewPassword1!")
        return {"id": "fake-user-id"}
    monkeypatch.setattr("app.routers.auth.pb.update_user", fake_update_user)

    async def fake_create_record(collection, data, token=None):
        assert collection == "user_password_history"
        assert verify_password("BrandNewPassword1!", data["password_hash"])
        return {"id": "history-id"}
    monkeypatch.setattr("app.routers.auth.pb.create_record", fake_create_record)

    # 3. Test change password with a fresh password
    response = client.post(
        "/api/auth/change-password",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "currentPassword": "CurrentPassword1!",
            "newPassword": "BrandNewPassword1!"
        }
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


if __name__ == "__main__":
    pytest.main([__file__])
