from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import FRONTEND_URL
from app.routers import resources, mood, journal, ai, auth, rituals, profile

app = FastAPI(
    title="MindCradle API",
    description="Backend API for the MindCradle mental health dashboard",
    version="0.1.0",
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
app.include_router(rituals.router, prefix="/api/rituals", tags=["rituals"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(profile.router, prefix="/api", tags=["profile"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "mindcradle-backend"}
