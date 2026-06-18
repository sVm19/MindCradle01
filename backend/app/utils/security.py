import hashlib
import hmac
import bcrypt
from typing import Optional
from app import config as settings

# Define pwd_context to mimic passlib's CryptContext class
# to prevent any import errors in other files or tests.
class NativeBcryptContext:
    def __init__(self, schemes=None, deprecated=None, bcrypt__rounds=12):
        self.rounds = bcrypt__rounds

    def hash(self, password: str) -> str:
        """Generate a secure random-salted bcrypt hash."""
        salt = bcrypt.gensalt(rounds=self.rounds)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a bcrypt hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
            )
        except Exception:
            return False

# Instantiate pwd_context to match standard passlib structure
pwd_context = NativeBcryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS
)


def hash_password(password: str) -> str:
    """
    Generate a secure, random-salted bcrypt hash of the password.
    Used for storing passwords in the local user history.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a secure bcrypt hash.
    Used for verifying passwords against the local user history.
    """
    return pwd_context.verify(plain_password, hashed_password)


def validate_password(password: str) -> Optional[str]:
    """
    Validate password against environment-defined strength requirements.
    Returns a descriptive error message if invalid, or None if valid.
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long."
        
    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."
        
    if settings.PASSWORD_REQUIRE_NUMBER and not any(c.isdigit() for c in password):
        return "Password must contain at least one number."
        
    if settings.PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*" for c in password):
        return "Password must contain at least one special character (!@#$%^&*)."
        
    return None


def get_deterministic_hash(password: str) -> str:
    """
    Generate a deterministic, secure hash of the password using HMAC-SHA256
    keyed with the app's secret key (JWT_SECRET_KEY).
    
    This is sent to Supabase as the password, keeping the original plain password
    private and ensuring the authentication remains secure, robust, and compatible
    with Supabase's internal hashing flow.
    """
    key = settings.JWT_SECRET_KEY or "dev-fallback-secret-key-123456"
    return hmac.new(
        key.encode("utf-8"),
        password.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
