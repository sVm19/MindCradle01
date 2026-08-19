from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import FRONTEND_URL, ENVIRONMENT, JWT_SECRET_KEY
from app.routers import resources, mood, journal, ai, auth, rituals, profile, notifications, user, billing, payments, webhooks, growth, seo, widgets
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers.ai import AgeGateException


from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

app = FastAPI(
    title="MindCradle API",
    description="Backend API for the MindCradle mental health dashboard",
    version="0.1.0",
)

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    async def check_expired_trials_job():
        try:
            from app.services.supabase import pb
            await pb.check_expired_trials()
            logger.info("Checked and deactivated expired trials successfully")
        except Exception as e:
            logger.error("Failed to run check_expired_trials background job: %s", e)
    scheduler.add_job(check_expired_trials_job, "interval", hours=1)
    
    async def pregenerate_daily_discoveries_job():
        try:
            logger.info("Daily Discovery background job ticked.")
        except Exception as e:
            logger.error("Failed to run pregenerate_daily_discoveries_job: %s", e)

    scheduler.add_job(pregenerate_daily_discoveries_job, "interval", hours=24)

    async def nightly_pkg_job():
        try:
            from app.services.supabase import pb
            from app.services import knowledge_graph as kg_svc
            # Query all user profiles to perform PKG decay/recalculation
            profile_res = await pb.list_records("user_profiles", params={"perPage": 1000})
            profiles = profile_res.get("items") or []
            for p in profiles:
                u_id = p.get("user_id")
                if u_id:
                    # Decay confidence of inactive nodes
                    await kg_svc.decay_confidence(u_id)
                    # Recompute 10 dimensions of growth metrics
                    await kg_svc.compute_growth_metrics(u_id)
                    # Scan and update active goal threads
                    await kg_svc.update_goal_threads(u_id)
                    # Detect behavioral routines and cycles
                    await kg_svc.detect_behavioral_patterns(u_id)
                    # Evaluate and detect life chapter boundary shifts
                    await kg_svc.detect_life_chapters(u_id)
            logger.info("Nightly PKG maintenance completed successfully")
        except Exception as err:
            logger.error("Failed to run nightly_pkg_job: %s", err)

    scheduler.add_job(nightly_pkg_job, "cron", hour=2) # run every night at 2 AM
    scheduler.start()
    logger.info("Background AsyncIOScheduler started successfully")

@app.on_event("shutdown")
async def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Background AsyncIOScheduler shutdown successfully")

# Add routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(resources.router, prefix="/api/resources", tags=["resources"])
app.include_router(mood.router, prefix="/api/mood", tags=["mood"])
app.include_router(journal.router, prefix="/api/journal", tags=["journal"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(ai.telemetry_router, prefix="/api/ai", tags=["ai"])
app.include_router(ai.aria_router, prefix="/api/aria", tags=["aria"])
app.include_router(rituals.router, prefix="/api/rituals", tags=["rituals"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(profile.router, prefix="/api", tags=["profile"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(growth.router, prefix="/api/growth", tags=["growth"])
app.include_router(seo.router, prefix="/api", tags=["seo"])
app.include_router(widgets.router, prefix="/api/widgets", tags=["widgets"])


# Health endpoint (no DB required)
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "mindcradle-backend"}

# Everything else below
class CsrfSettings(BaseModel):
    secret_key: str = JWT_SECRET_KEY
    cookie_samesite: str = "none" if ENVIRONMENT == "production" else "lax"
    cookie_secure: bool = (ENVIRONMENT == "production")

@CsrfProtect.load_config
def load_config():
    return CsrfSettings()

csrf_protect = CsrfProtect()

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

# Handle validation errors (don't expose details)
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    logger.error(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid request"}
    )

# Handle database errors (don't expose connection details)
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An error occurred. Please try again."}
    )

# Handle 404s gracefully
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"}
        )
    # Prevent 5xx detail leak centrally
    if exc.status_code >= 500:
        logger.error(f"HTTP Server Error {exc.status_code}: {exc.detail}")
        detail_msg = "An error occurred. Please try again."
        if exc.status_code == 502:
            detail_msg = "AI service unavailable"
        elif exc.status_code == 504:
            detail_msg = "AI service timeout. Please try again."
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail_msg}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# ─── Security Headers Middleware ──────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection (older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (strict)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://apis.google.com https://accounts.google.com https://cdn.jsdelivr.net https://abacklaunch.com https://nicklaunches.com https://invitejs.trustpilot.com https://*.trustpilot.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: blob: https: https://*.trustpilot.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "connect-src 'self' https: wss: https://*.trustpilot.com; "
            "frame-src 'self' https://accounts.google.com https://abacklaunch.com https://nicklaunches.com https://*.trustpilot.com; "
            "frame-ancestors 'none';"
        )
        
        # Strict Transport Security (HTTPS only)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # Remove Server header (don't advertise FastAPI)
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


# ─── CORS ─────────────────────────────────────────────────────────────────────
# In production: only the HTTPS production frontend origin is allowed.
# In development: localhost origins are added so the Vite dev server works.
# NOTE: Starlette middleware runs in LIFO order — CORS must be added last
# so it is the outermost wrapper and handles preflight before other middleware.

if ENVIRONMENT == "production":
    # Only the real HTTPS frontend domain — no HTTP fallback in production
    allowed_origins = [FRONTEND_URL]
    # Allow both www and non-www variants of FRONTEND_URL to avoid CORS issues
    if "://www." in FRONTEND_URL:
        allowed_origins.append(FRONTEND_URL.replace("://www.", "://"))
    elif "://" in FRONTEND_URL:
        scheme, domain = FRONTEND_URL.split("://", 1)
        allowed_origins.append(f"{scheme}://www.{domain}")
else:
    # Dev: accept both the configured URL and Vite's default dev server ports
    allowed_origins = [
        FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
    ]

# Security and rate-limit middleware (inner layers)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

# CORS middleware must be outermost (added last) so it intercepts OPTIONS
# preflights before any other middleware can reject them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Requested-With",
        "X-CSRF-Token",  # Required for CSRF-protected POST/PUT/DELETE requests
    ],
)

@app.get("/api/csrf-token")
async def get_csrf_token(request: Request):
    """Return CSRF token for form submissions and set signed cookie."""
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = JSONResponse(content={"csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


# ─── OpenAPI Customization ───────────────────────────────────────────────────
from fastapi.openapi.utils import get_openapi
from starlette.responses import Response
import yaml

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="MindCradle API",
        version=app.version or "0.1.0",
        description="API for MindCradle, an AI-powered personal reflection platform providing context-aware AI interactions, journaling, personal memory, and personalized experiences.",
        routes=app.routes,
    )
    
    # Configure Server URLs for production and local environments
    openapi_schema["servers"] = [
        {
            "url": "https://www.mindcradle.online",
            "description": "Production Server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Local Development Server"
        }
    ]
    
    # 1. Add security schemes (Bearer JWT)
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
        
    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT Access Token for MindCradle user authentication. Get this by calling /api/auth/login or /api/auth/signup."
    }
    
    # 2. Add standard HTTP error structures to components
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
        
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "detail": {
                "type": "string",
                "description": "Short error message describing the failure."
            }
        }
    }
    
    # 3. Post-process paths to associate authorization requirement
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            params = operation.get("parameters", [])
            has_auth = False
            new_params = []
            
            # Filter out the raw 'authorization' header input from the params list
            for param in params:
                if param.get("name", "").lower() == "authorization":
                    has_auth = True
                else:
                    new_params.append(param)
            
            # Determine if this route is private/protected
            # Exclude endpoints that are explicitly public
            is_public = (
                path in [
                    "/api/auth/signup",
                    "/api/auth/login",
                    "/api/auth/forgot-password",
                    "/api/auth/reset-password",
                    "/api/auth/privacy-policy",
                    "/health",
                    "/api/health",
                    "/api/csrf-token"
                ]
                or path.startswith("/api/webhooks")
                or path.startswith("/api/seo")
            )
            
            if has_auth or not is_public:
                operation["parameters"] = new_params
                if "security" not in operation:
                    operation["security"] = []
                operation["security"].append({"bearerAuth": []})
                
                # Standardize error responses on protected routes
                if "responses" not in operation:
                    operation["responses"] = {}
                
                if "401" not in operation["responses"]:
                    operation["responses"]["401"] = {
                        "description": "Unauthorized - Missing or invalid JWT access token",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                if "403" not in operation["responses"]:
                    operation["responses"]["403"] = {
                        "description": "Forbidden - Account restrictions or age gate validation failed",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ErrorResponse"
                                }
                            }
                        }
                    }
                    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/openapi.yaml", include_in_schema=False)
async def get_openapi_yaml():
    """Return the OpenAPI specification in YAML format."""
    openapi_json = app.openapi()
    yaml_str = yaml.dump(openapi_json, default_flow_style=False, sort_keys=False)
    return Response(content=yaml_str, media_type="application/x-yaml")

