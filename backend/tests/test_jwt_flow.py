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
from app.core.security import verify_custom_access_token
from jwt.exceptions import ExpiredSignatureError
import jwt

client = TestClient(app)

def test_jwt_flow():
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
        
    # 4. Test refresh endpoint via cookies
    cookies = {"refresh_token": refresh_token}
    response = client.post("/api/auth/refresh", cookies=cookies)
    assert response.status_code == 200, f"Refresh failed: {response.text}"
    
    data = response.json()
    assert "token" in data
    assert data["user_id"] == user_id
    assert data["email"] == email
    assert data["name"] == name
    assert data["refresh_token"] == ""  # Refresh token should NOT be returned in body
    
    new_access_token = data["token"]
    decoded_new_access = verify_custom_access_token(new_access_token)
    assert decoded_new_access.sub == user_id
    print("4. Refresh endpoint verified cookie, issued a new access token, and did not issue a new refresh token.")
    
    # 5. Test refresh failure with expired/invalid refresh token
    expired_refresh_payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow() - timedelta(minutes=10),
        "type": "refresh"
    }
    expired_refresh_token = jwt.encode(expired_refresh_payload, settings.JWT_REFRESH_SECRET_KEY, "HS256")
    
    expired_cookies = {"refresh_token": expired_refresh_token}
    response = client.post("/api/auth/refresh", cookies=expired_cookies)
    assert response.status_code == 401, f"Expected 401 but got {response.status_code}"
    print("5. Refresh endpoint correctly returned 401 for expired refresh token.")
    
    print("\nAll integration tests passed successfully!")

if __name__ == "__main__":
    test_jwt_flow()
