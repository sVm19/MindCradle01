import pytest
from fastapi.testclient import TestClient
from app.main import app
from fastapi_csrf_protect import CsrfProtect

@pytest.fixture(autouse=True)
def remove_csrf_override():
    # Remove the general MockCsrfProtect override for these tests
    # so we test the actual CSRF library behavior
    if CsrfProtect in app.dependency_overrides:
        del app.dependency_overrides[CsrfProtect]
    yield

@pytest.fixture
def client():
    return TestClient(app)

def test_csrf_token_endpoint(client):
    response = client.get("/api/csrf-token")
    assert response.status_code == 200
    res_json = response.json()
    assert "csrf_token" in res_json
    assert res_json["csrf_token"] is not None
    # Verify the CSRF cookie was set in the response headers
    assert "fastapi-csrf-token" in response.cookies

def test_post_mood_without_csrf_fails(client):
    response = client.post(
        "/api/mood",
        json={"level": 6, "emotions": ["Relaxed"], "note": "Feeling good"}
    )
    assert response.status_code == 403
    assert "detail" in response.json()
    assert "Missing Cookie" in response.json()["detail"]

def test_post_mood_with_invalid_csrf_fails(client):
    # Set the cookie but send a wrong header token
    client.cookies.set("fastapi-csrf-token", "some-signed-token")
    response = client.post(
        "/api/mood",
        headers={"X-CSRF-Token": "wrong-token"},
        json={"level": 6, "emotions": ["Relaxed"], "note": "Feeling good"}
    )
    assert response.status_code == 403

def test_post_mood_with_valid_csrf_succeeds(client, monkeypatch):
    # Mock database record creation
    async def fake_create_record(collection, data, token=None):
        return {"id": "mocked_mood_1"}
    monkeypatch.setattr("app.routers.mood.pb.create_record", fake_create_record)

    # 1. Fetch valid token and signed cookie
    token_response = client.get("/api/csrf-token")
    assert token_response.status_code == 200
    csrf_token = token_response.json()["csrf_token"]
    
    # 2. Make the POST request containing both the header and the cookie
    response = client.post(
        "/api/mood",
        headers={"X-CSRF-Token": csrf_token},
        json={"level": 6, "emotions": ["Relaxed"], "note": "Feeling good"}
    )
    assert response.status_code == 200
    assert response.json() == {"id": "mocked_mood_1", "saved": True}
