from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import FRONTEND_URL
from app.routers import resources, mood, journal, ai, auth

app = FastAPI(
    title="The Calm Center API",
    description="Backend API for The Calm Center mental health dashboard",
    version="0.1.0",
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
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


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "calm-center-backend"}
