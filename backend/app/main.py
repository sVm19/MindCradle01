from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import FRONTEND_URL, ENVIRONMENT, JWT_SECRET_KEY
from app.routers import resources, mood, journal, ai, auth, rituals, profile, notifications
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers.ai import AgeGateException

from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic import BaseModel

class CsrfSettings(BaseModel):
    secret_key: str = JWT_SECRET_KEY
    cookie_samesite: str = "lax"
    cookie_secure: bool = (ENVIRONMENT == "production")

@CsrfProtect.load_config
def load_config():
    return CsrfSettings()

csrf_protect = CsrfProtect()

app = FastAPI(
    title="MindCradle API",
    description="Backend API for the MindCradle mental health dashboard",
    version="0.1.0",
)

from fastapi.exceptions import RequestValidationError

@app.exception_handler(AgeGateException)
async def age_gate_exception_handler(request, exc: AgeGateException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "code": exc.code}
    )

@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=403,
        content={"detail": exc.message}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # If there is a password error, return 400 Bad Request to match prompt spec
    for error in exc.errors():
        if "password" in error.get("loc", []):
            return JSONResponse(
                status_code=400,
                content={"detail": error.get("msg")}
            )
    # Default behavior for other 422 validations
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


# ─── Security Headers Middleware ──────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Attaches security response headers on every reply.

    In production these enforce HTTPS, prevent clickjacking, stop MIME
    sniffing, and tell browsers to apply a basic Content-Security-Policy.
    Headers are safe to send in development too — they have no effect on
    plain-HTTP localhost requests.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Strict-Transport-Security — tell browsers to only use HTTPS for 1 year
        # includeSubDomains: covers api.mindcradle.com and any sub-paths
        # preload: eligible for browser HSTS preload lists (optional)
        if ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Prevent the page from being embedded in an iframe (clickjacking)
        response.headers["X-Frame-Options"] = "DENY"

        # Stop browsers from MIME-sniffing a response away from the declared content-type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Control how much referrer info is included in requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disable browser features not needed by this API
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Basic Content-Security-Policy for the API (not a browser-rendered app,
        # but helps if the docs UI is ever exposed)
        response.headers["Content-Security-Policy"] = "default-src 'none'"

        return response


app.add_middleware(SecurityHeadersMiddleware)

# Register rate limiter middleware (standard endpoints: 100 requests/minute)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# In production: only the HTTPS production frontend origin is allowed.
# In development: localhost origins are added so the Vite dev server works.

if ENVIRONMENT == "production":
    # Only the real HTTPS frontend domain — no HTTP fallback in production
    allowed_origins = [FRONTEND_URL]
else:
    # Dev: accept both the configured URL and Vite's default dev server ports
    allowed_origins = [
        FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(resources.router, prefix="/api/resources", tags=["resources"])
app.include_router(mood.router, prefix="/api/mood", tags=["mood"])
app.include_router(journal.router, prefix="/api/journal", tags=["journal"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(ai.aria_router, prefix="/api/aria", tags=["aria"])
app.include_router(rituals.router, prefix="/api/rituals", tags=["rituals"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(profile.router, prefix="/api", tags=["profile"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])


@app.get("/api/csrf-token")
async def get_csrf_token(request: Request):
    """Return CSRF token for form submissions and set signed cookie."""
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = JSONResponse(content={"csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "mindcradle-backend"}
