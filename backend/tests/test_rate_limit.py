import os

# Set up test env before importing config
os.environ["ENVIRONMENT"] = "development"
os.environ["JWT_SECRET_KEY"] = "test-access-secret-key-1234567890-test-key-access"
os.environ["JWT_REFRESH_SECRET_KEY"] = "test-refresh-secret-key-1234567890-test-key-refresh"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test"
os.environ["SUPABASE_JWT_SECRET"] = "test"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_rate_limiting_flow():
    print("Starting rate limiting tests...")
    
    # 1. Test auth endpoint (/api/auth/login)
    # The strict limit is 5 requests per minute
    print("Testing auth limit (5 requests/minute)...")
    for i in range(5):
        # We send random credentials; it should pass rate limiter
        # and fail at auth verification, returning 400 or 401, NOT 429
        response = client.post("/api/auth/login", json={"email": f"user{i}@example.com", "password": "Password123!"})
        assert response.status_code != 429, f"Request {i+1} got unexpected 429"
        print(f"Request {i+1} passed rate limit (Status: {response.status_code})")
        
    # The 6th request to login should return 429
    response = client.post("/api/auth/login", json={"email": "user5@example.com", "password": "Password123!"})
    assert response.status_code == 429, f"Expected 429 on 6th request, got {response.status_code}: {response.text}"
    assert response.json() == {"detail": "Too many requests. Try again in 1 minute."}
    print("Auth endpoint rate limiting (5 requests/min) works as expected!")
    
    # 2. Test standard endpoint (/api/health)
    # The default limit is 100 requests per minute.
    # Since we have already appended 5 timestamps, we can make 95 more requests.
    print("Testing standard limit (100 requests/minute)...")
    for i in range(95):
        response = client.get("/api/health")
        assert response.status_code == 200, f"Request {i+1} failed with status {response.status_code}: {response.text}"
        
    # The 96th health request (101st request overall for this IP) should return 429
    response = client.get("/api/health")
    assert response.status_code == 429, f"Expected 429 on 101st request, got {response.status_code}: {response.text}"
    assert response.json() == {"detail": "Too many requests. Try again in 1 minute."}
    print("Standard endpoint rate limiting (100 requests/min) works as expected!")
    
    # 3. Test OPTIONS request is NOT rate-limited
    # Even though we are rate-limited, OPTIONS should still pass through
    print("Testing that OPTIONS requests are not rate-limited...")
    response = client.options("/api/health")
    assert response.status_code != 429, f"OPTIONS request got rate limited with status {response.status_code}"
    print("OPTIONS request successfully bypassed rate limiting!")
    
    print("\nAll rate limiting tests passed successfully!")
