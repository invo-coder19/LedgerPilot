"""FastAPI application factory and entrypoint — LedgerPilot Phase 5."""

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.error_handlers import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    StructuredLoggingMiddleware,
)
from app.api.routes import (
    auth, dashboard, transactions, invoices, settlements,
    bank_transactions, exceptions, audit_logs, intelligence,
    investigations, copilot,
    # Phase 4
    controller, approvals, policies, actions, controller_config,
    # Phase 5
    health, evaluation, simulation, demo,
)

settings = get_settings()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(message)s",
)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="LedgerPilot API",
    description=(
        "**LedgerPilot — Autonomous AI Finance Controller**\n\n"
        "An AI-powered system that reconciles financial records, investigates exceptions "
        "using ML + evidence-backed reasoning, applies deterministic risk/policy gates, "
        "autonomously resolves bounded low-risk cases, and escalates uncertain decisions "
        "to humans — with complete auditability and measurable accuracy.\n\n"
        "**Phases:** 1 Foundation | 2 Reconciliation | 3A ML/RAG | 3B AI Investigator | "
        "4 Autonomous Controller | 5 Evaluation & Hardening\n\n"
        "> ⚠️ **DEMO MODE** — Synthetic financial data only. No real money movement."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_tags=[
        {"name": "Authentication", "description": "Login and token management"},
        {"name": "Dashboard", "description": "Operational metrics and KPIs"},
        {"name": "Data", "description": "Transactions, invoices, settlements, bank records"},
        {"name": "Reconciliation", "description": "Matching engine and reconciliation runs"},
        {"name": "Exceptions", "description": "Financial exception management"},
        {"name": "Intelligence", "description": "ML predictions and anomaly detection"},
        {"name": "Investigations", "description": "AI-driven root-cause investigations"},
        {"name": "Controller", "description": "Autonomous finance controller"},
        {"name": "Approvals", "description": "Human approval workflow"},
        {"name": "Policies", "description": "Controller policy management"},
        {"name": "Actions", "description": "Action execution history and rollback"},
        {"name": "Controller Config", "description": "Safety limits and kill switch"},
        {"name": "Evaluation", "description": "Benchmark evaluation and quality metrics"},
        {"name": "Simulation", "description": "Failure simulation framework"},
        {"name": "Demo", "description": "Demo environment management"},
        {"name": "Health", "description": "System health and liveness probes"},
    ],
)

# ── Exception Handlers ────────────────────────────────────────────────────────
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ── Middleware (applied in reverse registration order) ────────────────────────
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Request-ID"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

# Phase 1-2
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(transactions.router, prefix=API_PREFIX)
app.include_router(invoices.router, prefix=API_PREFIX)
app.include_router(settlements.router, prefix=API_PREFIX)
app.include_router(bank_transactions.router, prefix=API_PREFIX)
app.include_router(exceptions.router, prefix=API_PREFIX)
app.include_router(audit_logs.router, prefix=API_PREFIX)
# Phase 3
app.include_router(intelligence.router, prefix=API_PREFIX)
app.include_router(investigations.router, prefix=API_PREFIX)
app.include_router(copilot.router, prefix=API_PREFIX)
# Phase 4
app.include_router(controller.router, prefix=API_PREFIX)
app.include_router(approvals.router, prefix=API_PREFIX)
app.include_router(policies.router, prefix=API_PREFIX)
app.include_router(actions.router, prefix=API_PREFIX)
app.include_router(controller_config.router, prefix=API_PREFIX)
# Phase 5
app.include_router(health.router)          # no API prefix — /health/*
app.include_router(evaluation.router, prefix=API_PREFIX)
app.include_router(simulation.router, prefix=API_PREFIX)
app.include_router(demo.router, prefix=API_PREFIX)


# ── Root health (backward compat) ─────────────────────────────────────────────
@app.get("/health", tags=["Health"], include_in_schema=False)
def health_check() -> dict:
    """Simple liveness probe (backward compat). Use /health/live for k8s."""
    return {"status": "ok", "version": settings.APP_VERSION}
