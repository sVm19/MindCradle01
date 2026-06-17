from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import FRONTEND_URL
from app.routers import resources, mood, journal, ai, auth, rituals, profile, notifications
from app.routers.ai import AgeGateException
from fastapi.responses import JSONResponse

app = FastAPI(
    title="MindCradle API",
    description="Backend API for the MindCradle mental health dashboard",
    version="0.1.0",
)

@app.exception_handler(AgeGateException)
async def age_gate_exception_handler(request, exc: AgeGateException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "code": exc.code}
    )

# CORS — allow the frontend (Vite dev on 5173, or configured FRONTEND_URL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "mindcradle-backend"}
