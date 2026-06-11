from fastapi.testclient import TestClient
from app.main import app

def main():
    client = TestClient(app)
    
    print("Testing GET /api/mood...")
    try:
        response = client.get("/api/mood")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print("GET /api/mood raised exception:", e)

    print("\nTesting POST /api/mood...")
    try:
        response = client.post("/api/mood", json={
            "level": 5,
            "emotions": ["calm"],
            "note": "A good day"
        })
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print("POST /api/mood raised exception:", e)

    print("\nTesting POST /api/rituals/morning...")
    try:
        response = client.post("/api/rituals/morning", json={
            "forecast": "sunny",
            "intention": "be productive",
            "activityType": "breathing",
            "completedAt": "2026-06-10T22:51:55Z"
        })
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print("POST /api/rituals/morning raised exception:", e)

if __name__ == "__main__":
    main()
