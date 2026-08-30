"""Phase 5 — Production middleware stack.

Middleware execution order (outermost first):
  1. SecurityHeadersMiddleware  — adds security headers
  2. RequestIDMiddleware        — assigns X-Request-ID to every request
  3. StructuredLoggingMiddleware — logs request lifecycle as JSON
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("ledgerpilot.http")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a unique X-Request-ID to every request.

    Clients may send their own X-Request-ID which is preserved if valid UUID4,
    otherwise a new one is generated.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", "")
        try:
            if request_id:
                uuid.UUID(request_id)   # validate format
            else:
                request_id = str(uuid.uuid4())
        except ValueError:
            request_id = str(uuid.uuid4())

        # Store in request state for downstream access
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request as a structured JSON line.

    Does NOT log:
      - Authorization headers
      - Request bodies (may contain credentials/financial data)
      - Cookie values
    """

    SKIP_PATHS = {"/health", "/health/live", "/health/ready", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", "-")

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(json.dumps({
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "error": str(exc),
                "event": "request_error",
            }))
            raise

        log_level = logging.WARNING if status_code >= 400 else logging.INFO
        logger.log(log_level, json.dumps({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "event": "request_completed",
        }))

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add essential security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Note: HSTS only set in production via reverse proxy / load balancer
        return response
