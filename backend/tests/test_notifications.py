from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_device_unauthorized():
    response = client.post(
        "/api/notifications/register-device",
        json={
            "push_token": "token123",
            "platform": "web",
            "device_id": "device123",
        },
    )
    assert response.status_code == 401


def test_register_device_success_insert(monkeypatch):
    user_id = "test-user-id"
    monkeypatch.setattr(
        "app.routers.notifications.extract_user_id", lambda auth: user_id
    )

    class FakeTable:

        def __init__(self, name):
            self.name = name

        def select(self, *args):
            return self

        def eq(self, field, value):
            return self

        def execute(self):
            # Return empty data to simulate no existing device token
            class Result:
                data = []

            return Result()

        def insert(self, data):
            assert data["user_id"] == user_id
            assert data["push_token"] == "token123"
            assert data["platform"] == "web"
            assert data["device_id"] == "device123"
            assert data["is_active"] is True
            return self

    class FakeClient:

        def table(self, name):
            return FakeTable(name)

    monkeypatch.setattr(
        "app.routers.notifications._get_client", lambda auth: FakeClient()
    )

    response = client.post(
        "/api/notifications/register-device",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "push_token": "token123",
            "platform": "web",
            "device_id": "device123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"registered": True, "device_id": "device123"}


def test_register_device_success_update(monkeypatch):
    user_id = "test-user-id"
    monkeypatch.setattr(
        "app.routers.notifications.extract_user_id", lambda auth: user_id
    )

    class FakeTable:

        def __init__(self, name):
            self.name = name

        def select(self, *args):
            return self

        def eq(self, field, value):
            return self

        def execute(self):
            # Return existing record to trigger update path
            class Result:
                data = [
                    {"id": "existing-record-id", "device_id": "device123"}
                ]

            return Result()

        def update(self, data):
            assert data["push_token"] == "token_new"
            assert data["platform"] == "web"
            assert data["is_active"] is True
            return self

    class FakeClient:

        def table(self, name):
            return FakeTable(name)

    monkeypatch.setattr(
        "app.routers.notifications._get_client", lambda auth: FakeClient()
    )

    response = client.post(
        "/api/notifications/register-device",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "push_token": "token_new",
            "platform": "web",
            "device_id": "device123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"registered": True, "device_id": "device123"}


def test_test_notifications_unauthorized():
    response = client.post("/api/notifications/test")
    assert response.status_code == 401


def test_test_notifications_success(monkeypatch):
    user_id = "test-user-id"
    monkeypatch.setattr(
        "app.routers.notifications.extract_user_id", lambda auth: user_id
    )

    def fake_send_to_user(uid, title, body):
        assert uid == user_id
        assert title == "Test"
        assert body == "Hello from Firebase!"
        return 2

    monkeypatch.setattr(
        "app.routers.notifications.send_to_user", fake_send_to_user
    )

    response = client.post(
        "/api/notifications/test",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"sent": True, "count": 2}

