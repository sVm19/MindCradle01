from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_profile_milestones_patch_upserts_profile(monkeypatch):
    async def fake_upsert_user_profile(token, payload):
        assert token == "demo-token"
        assert payload["unlocked_badges"] == ["first-light"]
        return {"id": "profile_1", "unlocked_badges": ["first-light"]}

    monkeypatch.setattr("app.routers.profile.pb.upsert_user_profile", fake_upsert_user_profile)

    response = client.patch(
        "/api/profile/milestones",
        headers={"Authorization": "demo-token"},
        json={"unlockedBadges": ["first-light"]},
    )

    assert response.status_code == 200
    assert response.json()["unlocked_badges"] == ["first-light"]
