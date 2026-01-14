"""
Shared Authentication and Rate Limiting Module

Provides optional API key authentication and rate limiting for all DGX Spark services.

Configuration via environment variables:
  DGX_API_KEY: If set, enables Bearer token authentication
  DGX_RATE_LIMIT: Requests per minute per IP (default: 60)
  DGX_AUTH_DISABLED: Set to "true" to disable auth even if API key is set

Usage:
    from shared.auth import add_auth_middleware

    app = FastAPI()
    add_auth_middleware(app)
"""

import os
import time
import hashlib
from collections import defaultdict
from typing import Callable, Dict, Tuple
from functools import wraps

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Configuration from environment
API_KEY = os.environ.get("DGX_API_KEY")
RATE_LIMIT = int(os.environ.get("DGX_RATE_LIMIT", "60"))  # requests per minute
AUTH_DISABLED = os.environ.get("DGX_AUTH_DISABLED", "").lower() == "true"

# In-memory rate limit tracking
# Format: {client_ip: [(timestamp, count), ...]}
_rate_limits: Dict[str, list] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For header (from reverse proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP in chain (original client)
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client
    return request.client.host if request.client else "unknown"


def check_rate_limit(client_ip: str) -> Tuple[bool, int]:
    """
    Check if client is within rate limit.

    Returns:
        Tuple of (is_allowed, remaining_requests)
    """
    now = time.time()
    window_start = now - 60  # 1 minute window

    # Clean old entries
    _rate_limits[client_ip] = [
        (ts, count) for ts, count in _rate_limits[client_ip]
        if ts > window_start
    ]

    # Count requests in current window
    total_requests = sum(count for _, count in _rate_limits[client_ip])

    if total_requests >= RATE_LIMIT:
        return False, 0

    # Add current request
    _rate_limits[client_ip].append((now, 1))

    return True, RATE_LIMIT - total_requests - 1


def verify_api_key(request: Request) -> bool:
    """Verify API key from Authorization header."""
    if not API_KEY or AUTH_DISABLED:
        return True  # Auth not enabled

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return False

    token = auth_header[7:]  # Remove "Bearer " prefix

    # Constant-time comparison to prevent timing attacks
    return hashlib.sha256(token.encode()).hexdigest() == hashlib.sha256(API_KEY.encode()).hexdigest()


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication and rate limiting middleware.

    - Validates Bearer token if DGX_API_KEY is set
    - Enforces rate limits per client IP
    - Adds security headers to responses
    - Skips auth for health check endpoints
    """

    # Endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {"/health", "/", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        client_ip = get_client_ip(request)

        # Skip auth for public endpoints
        if path in self.PUBLIC_ENDPOINTS:
            response = await call_next(request)
            return self._add_security_headers(response)

        # Check API key authentication
        if API_KEY and not AUTH_DISABLED:
            if not verify_api_key(request):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key"},
                    headers={"WWW-Authenticate": "Bearer"}
                )

        # Check rate limit
        is_allowed, remaining = check_rate_limit(client_ip)
        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "X-RateLimit-Limit": str(RATE_LIMIT),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60"
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-Client-IP"] = client_ip

        return self._add_security_headers(response)

    def _add_security_headers(self, response) -> JSONResponse:
        """Add security headers to response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


def add_auth_middleware(app: FastAPI, skip_paths: set = None):
    """
    Add authentication middleware to FastAPI app.

    Args:
        app: FastAPI application instance
        skip_paths: Additional paths to skip authentication (optional)
    """
    if skip_paths:
        AuthMiddleware.PUBLIC_ENDPOINTS = AuthMiddleware.PUBLIC_ENDPOINTS | skip_paths

    app.add_middleware(AuthMiddleware)

    # Log auth status on startup
    if API_KEY and not AUTH_DISABLED:
        print(f"🔐 API authentication enabled (rate limit: {RATE_LIMIT}/min)")
    else:
        print(f"⚠️  API authentication disabled (rate limit: {RATE_LIMIT}/min)")


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for specific endpoints.
    Use when you want to protect specific routes without middleware.

    Usage:
        @app.post("/admin/action")
        @require_auth
        async def admin_action(request: Request):
            ...
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not verify_api_key(request):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return await func(request, *args, **kwargs)
    return wrapper
