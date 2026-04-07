"""Security headers and request logging middleware."""

import time
import uuid
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = structlog.get_logger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # HSTS in production
        if not request.url.hostname in ("localhost", "127.0.0.1"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests with timing and request IDs."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip logging for health checks and static files
        if request.url.path in ("/", "/health", "/favicon.ico"):
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        # Bind request context for structured logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        elapsed = time.time() - start
        response.headers["X-Request-ID"] = request_id

        log_method = logger.info if response.status_code < 400 else logger.warning
        log_method(
            "request_completed",
            status=response.status_code,
            duration_ms=round(elapsed * 1000),
            client=request.client.host if request.client else "unknown",
        )

        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Basic input sanitization — reject oversized payloads."""

    MAX_BODY_SIZE = 50 * 1024 * 1024  # 50MB

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return Response(
                content='{"detail": "Request body too large (max 50MB)"}',
                status_code=413,
                media_type="application/json",
            )

        return await call_next(request)
