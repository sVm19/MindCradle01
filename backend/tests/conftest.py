import pytest
from app.main import app
from app.routers.ai import check_aria_age_verified, OFF_TOPIC_LIMITS

@pytest.fixture(autouse=True)
def override_age_verified():
    OFF_TOPIC_LIMITS.clear()
    # By default, mock the age verification dependency to pass for all existing tests
    app.dependency_overrides[check_aria_age_verified] = lambda: None
    yield
    app.dependency_overrides.clear()
    OFF_TOPIC_LIMITS.clear()
