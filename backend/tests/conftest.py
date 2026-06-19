import os
# Set default environment variables for test isolation before any imports that use them
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-jwt-refresh-secret-key")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
os.environ.setdefault("ENVIRONMENT", "development")

import pytest
from app.main import app
from app.routers.ai import check_aria_age_verified, OFF_TOPIC_LIMITS
from app.middleware.rate_limit import reset_rate_limiters
from fastapi_csrf_protect import CsrfProtect

class MockCsrfProtect:
    async def validate_csrf(self, request, cookie_key=None, secret_key=None, time_limit=None):
        pass

    def generate_csrf_tokens(self, secret_key=None):
        return "mocked-token", "mocked-signed-token"

    def set_csrf_cookie(self, token, response):
        pass

@pytest.fixture(autouse=True)
def override_age_verified():
    OFF_TOPIC_LIMITS.clear()
    # Reset rate limiters before each test for test isolation
    reset_rate_limiters()
    
    # By default, mock the age verification dependency to pass for all existing tests
    app.dependency_overrides[check_aria_age_verified] = lambda: None
    # Mock CSRF protection to pass for all existing tests
    app.dependency_overrides[CsrfProtect] = lambda: MockCsrfProtect()
    yield
    app.dependency_overrides.clear()
    OFF_TOPIC_LIMITS.clear()
    # Clean up rate limiters after test execution as well
    reset_rate_limiters()
