from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.main import app
from app.routers import auth as auth_router


captured = {}


async def fake_create_magic_login_token(email: str, token: str, expiry_seconds: int) -> bool:
    captured["email"] = email
    captured["token"] = token
    captured["expiry_seconds"] = expiry_seconds
    return True


def fake_send_magic_link_email(user_email: str, magic_link: str) -> bool:
    captured["sent_to"] = user_email
    captured["magic_link"] = magic_link
    return True


async def fake_consume_magic_login_token(token: str):
    if token != captured.get("token"):
        return None

    return {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "user_email": captured["email"],
        "user_name": "Magic Test",
    }


async def fake_auto_start_trial_if_needed(user_id: str, token: str):
    captured["trial_user_id"] = user_id


def main() -> None:
    auth_router.pb.create_magic_login_token = fake_create_magic_login_token
    auth_router.pb.consume_magic_login_token = fake_consume_magic_login_token
    auth_router.send_magic_link_email = fake_send_magic_link_email
    auth_router._auto_start_trial_if_needed = fake_auto_start_trial_if_needed

    client = TestClient(app)
    email = "Magic.User+Test@Example.com"

    request_response = client.post("/api/auth/magic-link", json={"email": email})
    assert request_response.status_code == 200, request_response.text
    assert captured["email"] == email.lower()
    assert captured["sent_to"] == email.lower()
    assert captured["expiry_seconds"] == 900

    magic_link = captured["magic_link"]
    parsed = urlparse(magic_link)
    token = parse_qs(parsed.query).get("token", [""])[0]
    assert parsed.path == "/auth/magic"
    assert token == captured["token"]

    login_response = client.post("/api/auth/magic-login", json={"token": token})
    assert login_response.status_code == 200, login_response.text

    body = login_response.json()
    assert body["token"]
    assert body["refresh_token"] == ""
    assert body["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert body["email"] == email.lower()
    assert body["name"] == "Magic Test"
    assert "refresh_token=" in login_response.headers.get("set-cookie", "")
    assert captured["trial_user_id"] == body["user_id"]

    print("Magic-link login flow passed")
    print(f"Generated callback path: {parsed.path}")
    print(f"Authenticated user: {body['email']}")


if __name__ == "__main__":
    main()
