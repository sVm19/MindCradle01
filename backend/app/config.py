import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

# Runtime environment — set to "production" on deployment platforms.
# Controls CORS origins, HSTS headers, and startup validation.
# Defaults to "development" so local dev works with no extra config.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nnwuthynlxrbvuxmpjgu.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# SUPABASE_JWT_SECRET — used to cryptographically verify Supabase-issued JWTs.
# Find it in: Supabase Dashboard → Project Settings → API → JWT Secret
# NEVER log or expose this value.
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# AI API (OpenRouter)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_URL = os.getenv(
    "OPENROUTER_API_URL",
    "https://openrouter.ai/api/v1",
)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")


# CORS — the URL of the frontend that is allowed to call this API.
# In production this MUST be an https:// URL.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ── JWT token lifetime settings ───────────────────────────────────────────────
# These govern how long sessions last.
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

# Custom JWT Keys
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "")

# JWT algorithm — HS256 is used for both Supabase and custom tokens.
JWT_ALGORITHM = "HS256"

# Password validation and hashing configurations
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
PASSWORD_REQUIRE_UPPERCASE = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
PASSWORD_REQUIRE_NUMBER = os.getenv("PASSWORD_REQUIRE_NUMBER", "true").lower() == "true"
PASSWORD_REQUIRE_SPECIAL = os.getenv("PASSWORD_REQUIRE_SPECIAL", "true").lower() == "true"
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))


# ── Startup validation ────────────────────────────────────────────────────────
# Fail hard at startup if production config is obviously wrong.
# This catches misconfigured deployments before any requests are served.

if ENVIRONMENT == "production":
    if not FRONTEND_URL.startswith("https://"):
        sys.exit(
            f"[FATAL] FRONTEND_URL must use https:// in production. Got: {FRONTEND_URL!r}\n"
            "Set FRONTEND_URL=https://your-domain.com in your deployment environment."
        )
    if not SUPABASE_URL:
        sys.exit(
            "[FATAL] SUPABASE_URL is not set.\n"
            "Cannot connect to database. Set it in your deployment environment variables."
        )
    if not SUPABASE_ANON_KEY:
        sys.exit(
            "[FATAL] SUPABASE_ANON_KEY is not set.\n"
            "All database requests will fail. Set it in your deployment environment variables.\n"
            "Find it at: Supabase Dashboard → Project Settings → API → anon (public)"
        )
    if not SUPABASE_JWT_SECRET:
        sys.exit(
            "[FATAL] SUPABASE_JWT_SECRET is not set.\n"
            "All JWT verification will fail. Set it in your deployment environment variables.\n"
            "Find it at: Supabase Dashboard → Project Settings → API → JWT Secret"
        )
    if not JWT_SECRET_KEY or not JWT_REFRESH_SECRET_KEY:
        sys.exit(
            "[FATAL] JWT_SECRET_KEY or JWT_REFRESH_SECRET_KEY is not set.\n"
            "Cannot run custom token security in production."
        )
    if not OPENROUTER_API_KEY:
        sys.exit("[FATAL] OPENROUTER_API_KEY is not set. Cannot run in production.")
    if not RESEND_API_KEY:
        sys.exit("[FATAL] RESEND_API_KEY is not set. Cannot run in production.")


