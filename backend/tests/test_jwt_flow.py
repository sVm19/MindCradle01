import os
import time

# Set up test env before importing config
os.environ["ENVIRONMENT"] = "development"
os.environ["JWT_SECRET_KEY"] = "test-access-secret-key-1234567890-test-key-access"
os.environ["JWT_REFRESH_SECRET_KEY"] = "test-refresh-secret-key-1234567890-test-key-refresh"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "1"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "1"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test"
os.environ["SUPABASE_JWT_SECRET"] = "test"

from fastapi.testclient import TestClient
from app.main import app
from app.routers.auth import create_access_token, create_refresh_token
from app.core.security import extract_user_id_verified, verify_custom_access_token
from jwt.exceptions import ExpiredSignatureError
import jwt

client = TestClient(app)

def test_jwt_flow(monkeypatch):
    print("Starting JWT flow test...")
    user_id = "test-user-uuid"
    email = "test@example.com"
    name = "Test User"
    
    # 1. Test helper functions
    access_token = create_access_token(user_id, email=email)
    refresh_token = create_refresh_token(user_id, email=email, name=name)
    
    assert access_token is not None
    assert refresh_token is not None
    print("1. Helper functions created access and refresh tokens successfully.")
    
    # 2. Verify custom access token decoding
    decoded_access = verify_custom_access_token(access_token)
    assert decoded_access.sub == user_id
    assert decoded_access.type == "access"
    print("2. Decoded and verified custom access token successfully.")
    
    # 3. Test expired token
    from datetime import datetime, timedelta
    expire = datetime.utcnow() - timedelta(minutes=5)
    expired_payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow() - timedelta(minutes=10),
        "type": "access"
    }
    from app import config as settings
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, "HS256")
    
    try:
        verify_custom_access_token(expired_token)
        raise AssertionError("Expected ExpiredSignatureError, but validation passed.")
    except ExpiredSignatureError:
        print("3. Expired token signature validation failed as expected (returns ExpiredSignatureError).")
        
    # 4. Test refresh endpoint via Supabase refresh-token cookie
    async def fake_refresh_session(refresh_token: str):
        assert refresh_token == "supabase-refresh-token"
        return {
            "token": "supabase-access-token",
            "refresh_token": "next-supabase-refresh-token",
            "record": {
                "id": user_id,
                "email": email,
                "name": name,
            },
        }

    monkeypatch.setattr("app.routers.auth.pb.refresh_session", fake_refresh_session)

    cookies = {"refresh_token": "supabase-refresh-token"}
    response = client.post("/api/auth/refresh", cookies=cookies)
    assert response.status_code == 200, f"Refresh failed: {response.text}"
    
    data = response.json()
    assert data["token"] == "supabase-access-token"
    assert data["user_id"] == user_id
    assert data["email"] == email
    assert data["name"] == name
    assert data["refresh_token"] == ""  # Refresh token should NOT be returned in body

    set_cookie = response.headers.get("set-cookie", "")
    assert "refresh_token=next-supabase-refresh-token" in set_cookie
    print("4. Refresh endpoint exchanged the Supabase refresh token and issued a new Supabase access token.")

    # 5. Test refresh failure with expired/invalid Supabase refresh token
    async def fake_failed_refresh_session(refresh_token: str):
        raise Exception("invalid refresh token")

    monkeypatch.setattr("app.routers.auth.pb.refresh_session", fake_failed_refresh_session)

    expired_cookies = {"refresh_token": "invalid-supabase-refresh-token"}
    response = client.post("/api/auth/refresh", cookies=expired_cookies)
    assert response.status_code == 401, f"Expected 401 but got {response.status_code}"
    print("5. Refresh endpoint correctly returned 401 for expired refresh token.")
    
    print("\nAll integration tests passed successfully!")

def test_extract_user_id_falls_back_to_supabase_auth(monkeypatch):
    user_id = "remote-user-id"

    def fake_decode(*args, **kwargs):
        raise jwt.InvalidSignatureError("local secret did not verify token")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"id": user_id}

    def fake_get(url, headers, timeout):
        assert url.endswith("/auth/v1/user")
        assert headers["Authorization"] == "Bearer supabase-access-token"
        assert headers["apikey"]
        assert timeout == 5
        return FakeResponse()

    monkeypatch.setattr("app.core.security.jwt.decode", fake_decode)
    monkeypatch.setattr("app.core.security.httpx.get", fake_get)

    assert extract_user_id_verified("supabase-access-token") == user_id
