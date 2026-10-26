import sys
import os
import hmac
import hashlib
import json

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["ENVIRONMENT"] = "development"
os.environ["CREEM_WEBHOOK_SECRET"] = "test-webhook-secret-key-123456"

from fastapi.testclient import TestClient
from app.main import app
from app.config import ENVIRONMENT, CREEM_WEBHOOK_SECRET

client = TestClient(app)

def test_alb_spoofing_rejected():
    print("[TEST 1] Verifying ALB OIDC header spoofing rejection (VULN-01)...")
    # Attempting to authenticate via raw forged x-amzn-oidc-identity header
    resp = client.get(
        "/api/auth/alb-session",
        headers={"x-amzn-oidc-identity": "00000000-0000-0000-0000-000000000001"}
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
    
    # Attempting with malformed x-amzn-oidc-data header
    resp2 = client.get(
        "/api/auth/alb-session",
        headers={"x-amzn-oidc-data": "fake.jwt.token"}
    )
    assert resp2.status_code == 401, f"Expected 401, got {resp2.status_code}: {resp2.text}"
    print("  -> PASSED: Unverified ALB headers are strictly rejected with 401.")

def test_creem_webhook_signature():
    print("[TEST 2] Verifying Creem webhook HMAC signature enforcement (VULN-02)...")
    payload = json.dumps({"type": "subscription.created", "metadata": {"user_id": "fake-uuid"}}).encode()
    
    # Missing signature header
    resp = client.post("/api/webhooks/creem", content=payload, headers={"Content-Type": "application/json"})
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
    
    # Invalid signature header
    resp2 = client.post(
        "/api/webhooks/creem",
        content=payload,
        headers={"Content-Type": "application/json", "x-creem-signature": "invalid_hex_signature"}
    )
    assert resp2.status_code == 401, f"Expected 401, got {resp2.status_code}: {resp2.text}"
    
    # Valid signature header but empty metadata (proves signature check passes)
    payload_valid = json.dumps({"type": "subscription.created", "metadata": {}}).encode()
    valid_sig = hmac.new(b"test-webhook-secret-key-123456", payload_valid, hashlib.sha256).hexdigest()
    resp3 = client.post(
        "/api/webhooks/creem",
        content=payload_valid,
        headers={"Content-Type": "application/json", "x-creem-signature": valid_sig}
    )
    # Valid signature succeeds past auth check
    assert resp3.status_code == 200, f"Expected 200, got {resp3.status_code}: {resp3.text}"
    print("  -> PASSED: Creem webhook cryptographically validates HMAC-SHA256 signature.")

def test_journal_and_mood_auth():
    print("[TEST 3] Verifying mandatory authentication on Journal & Mood endpoints (VULN-04)...")
    # Unauthenticated GET /api/journal
    resp_j_get = client.get("/api/journal")
    assert resp_j_get.status_code == 401, f"Expected 401 on /api/journal GET, got {resp_j_get.status_code}"
    
    # Unauthenticated POST /api/journal
    resp_j_post = client.post("/api/journal", json={"prompt": "test", "content": "test entry"})
    assert resp_j_post.status_code in (401, 403), f"Expected 401/403 on /api/journal POST, got {resp_j_post.status_code}"

    # Unauthenticated GET /api/mood
    resp_m_get = client.get("/api/mood")
    assert resp_m_get.status_code == 401, f"Expected 401 on /api/mood GET, got {resp_m_get.status_code}"

    # Unauthenticated POST /api/mood
    resp_m_post = client.post("/api/mood", json={"level": 7, "emotions": ["calm"], "note": "fine"})
    assert resp_m_post.status_code in (401, 403), f"Expected 401/403 on /api/mood POST, got {resp_m_post.status_code}"
    print("  -> PASSED: Journal and Mood endpoints require valid authentication.")

def test_csp_unsafe_eval_eliminated():
    print("[TEST 4] Verifying CSP headers contain no 'unsafe-eval' (VULN-06)...")
    resp = client.get("/health")
    csp = resp.headers.get("content-security-policy", "")
    assert "unsafe-eval" not in csp, f"Found 'unsafe-eval' in backend CSP: {csp}"
    print("  -> PASSED: Backend CSP does not contain 'unsafe-eval'.")

def test_mock_billing_gated_in_prod():
    print("[TEST 5] Verifying mock credit card billing is gated in production (VULN-05)...")
    import app.routers.billing as billing_module
    old_env = billing_module.ENVIRONMENT
    billing_module.ENVIRONMENT = "production"
    try:
        resp = client.post(
            "/api/billing/checkout",
            json={"card_number": "4111111111111111", "cvc": "123", "expiry": "12/28"},
            headers={"Authorization": "Bearer fake_token"}
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        assert "disabled in production" in resp.text
        print("  -> PASSED: Direct card checkout is strictly blocked in production.")
    finally:
        billing_module.ENVIRONMENT = old_env

if __name__ == "__main__":
    print("=== Running MindCradle Security Hardening Verification ===")
    test_alb_spoofing_rejected()
    test_creem_webhook_signature()
    test_journal_and_mood_auth()
    test_csp_unsafe_eval_eliminated()
    test_mock_billing_gated_in_prod()
    print("=== ALL SECURITY CHECKS PASSED SUCCESSFULLY ===")
