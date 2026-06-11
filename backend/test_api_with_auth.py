import uuid
from fastapi.testclient import TestClient
from app.main import app

def main():
    client = TestClient(app)
    
    # 1. Sign up a new user
    email = f"test_{uuid.uuid4()}@example.com"
    password = "password123"
    name = "Test User"
    
    print(f"Signing up user: {email}...")
    signup_res = client.post("/api/auth/signup", json={
        "email": email,
        "password": password,
        "passwordConfirm": password,
        "name": name
    })
    
    print(f"Signup response status: {signup_res.status_code}")
    print(f"Signup response: {signup_res.text}")
    
    if signup_res.status_code != 200:
        print("Signup failed. Cannot proceed.")
        return
        
    auth_data = signup_res.json()
    token = auth_data["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Test POST /api/mood
    print("\nTesting POST /api/mood with auth...")
    mood_res = client.post("/api/mood", json={
        "level": 7,
        "emotions": ["motivated", "focused"],
        "note": "Feeling good today"
    }, headers=headers)
    
    print(f"POST /api/mood status: {mood_res.status_code}")
    print(f"POST /api/mood response: {mood_res.text}")
    
    # 3. Test GET /api/mood
    print("\nTesting GET /api/mood with auth...")
    mood_get = client.get("/api/mood?range=7d", headers=headers)
    print(f"GET /api/mood status: {mood_get.status_code}")
    print(f"GET /api/mood response: {mood_get.text}")

    # 4. Test POST /api/rituals/morning
    print("\nTesting POST /api/rituals/morning with auth...")
    morning_res = client.post("/api/rituals/morning", json={
        "forecast": "productive",
        "intention": "finish tasks",
        "activityType": "coding",
        "completedAt": "2026-06-10T22:51:55Z"
    }, headers=headers)
    print(f"POST /api/rituals/morning status: {morning_res.status_code}")
    print(f"POST /api/rituals/morning response: {morning_res.text}")

if __name__ == "__main__":
    main()
