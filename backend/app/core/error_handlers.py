"""Consistent application error codes and handlers.

All production errors return a structured JSON body:
  {
    "error": {
      "code": "ACTION_NOT_ALLOWED",
      "message": "Human-readable description",
      "request_id": "uuid"
    }
  }

Stack traces are NEVER returned in production responses.
"""

from __future__ import annotations

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("ledgerpilot.errors")

# ── Error codes ───────────────────────────────────────────────────────────────

class ErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    DATASET_ERROR = "DATASET_ERROR"
    RECONCILIATION_ERROR = "RECONCILIATION_ERROR"
    INVESTIGATION_ERROR = "INVESTIGATION_ERROR"
    POLICY_ERROR = "POLICY_ERROR"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    ACTION_EXECUTION_FAILED = "ACTION_EXECUTION_FAILED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    UPLOAD_ERROR = "UPLOAD_ERROR"


def _error_body(code: str, message: str, request_id: str = "-") -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


# ── Handlers ──────────────────────────────────────────────────────────────────

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Convert FastAPI HTTPExceptions to structured JSON."""
    code_map = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.AUTHENTICATION_ERROR,
        403: ErrorCode.AUTHORIZATION_ERROR,
        404: ErrorCode.NOT_FOUND,
        429: ErrorCode.RATE_LIMITED,
    }
    code = code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    # Safe sanitization: only return detail string, never dict/object that might expose internals
    message = str(exc.detail) if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, message, _request_id(request)),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convert Pydantic validation errors to structured JSON without exposing internals."""
    # Summarise which fields failed — don't expose full Pydantic error chain
    fields = [" → ".join(str(loc) for loc in e["loc"]) for e in exc.errors()]
    message = f"Validation failed for: {', '.join(fields[:5])}"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(ErrorCode.VALIDATION_ERROR, message, _request_id(request)),
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler — logs full error but returns sanitized response."""
    request_id = _request_id(request)
    logger.error(
        "Unhandled exception request_id=%s path=%s error=%r",
        request_id, request.url.path, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            ErrorCode.INTERNAL_ERROR,
            "An internal error occurred. Please try again or contact support.",
            request_id,
        ),
    )
