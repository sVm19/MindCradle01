from datetime import datetime, timedelta
import logging
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
import sys
from app.config import ENVIRONMENT

logger = logging.getLogger(__name__)

_active_rate_limiters = []

def reset_rate_limiters():
    """Clear all request logs on active rate limiters. Useful for test isolation."""
    for limiter in _active_rate_limiters:
        limiter.request_log.clear()
        limiter.cleanup_counter = 0

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_log = {}  # {ip: [timestamp]}
        self.cleanup_counter = 0
        _active_rate_limiters.append(self)
    
    async def dispatch(self, request: Request, call_next):
        # We only apply rate limiting to /api routes
        if not request.url.path.startswith("/api"):
            return await call_next(request)
            
        # Do not rate limit OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
            
        ip = request.client.host if request.client else "unknown-ip"
        now = datetime.utcnow()
        
        # Periodic cleanup of expired entries across all IPs to prevent memory leaks
        self.cleanup_counter += 1
        if self.cleanup_counter >= 100:
            self.cleanup_counter = 0
            empty_ips = []
            for k, timestamps in list(self.request_log.items()):
                pruned = [t for t in timestamps if now - t < timedelta(minutes=1)]
                if not pruned:
                    empty_ips.append(k)
                    self.request_log.pop(k, None)
                else:
                    self.request_log[k] = pruned
        
        # Stricter limit of 5 requests per minute for login and signup endpoints
        is_testing = "pytest" in sys.modules
        if request.url.path in ["/api/auth/login", "/api/auth/signup"]:
            if not is_testing and ENVIRONMENT != "production":
                limit = 100  # Relaxed for local development and manual testing
            else:
                limit = 5
        else:
            if not is_testing and ENVIRONMENT != "production":
                limit = 1000  # Relaxed for local development
            else:
                limit = self.requests_per_minute
        
        # Initialize log list for new IP
        if ip not in self.request_log:
            self.request_log[ip] = []
            
        # Clean up old timestamps (older than 1 minute) for current IP
        self.request_log[ip] = [
            t for t in self.request_log[ip]
            if now - t < timedelta(minutes=1)
        ]
        
        # Check if rate limit exceeded
        if len(self.request_log[ip]) >= limit:
            logger.warning(
                "Rate limit exceeded for IP %s on path %s (%s/%s requests)",
                ip, request.url.path, len(self.request_log[ip]), limit
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Try again in 1 minute."}
            )
            
        # Log the current request timestamp
        self.request_log[ip].append(now)
        
        return await call_next(request)
