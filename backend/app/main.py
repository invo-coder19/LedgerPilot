"""FastAPI application factory and entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import auth, dashboard, transactions, invoices, settlements, bank_transactions, exceptions, audit_logs

settings = get_settings()

app = FastAPI(
    title="LedgerPilot API",
    description=(
        "LedgerPilot — AI Finance Controller. "
        "Phase 1: Foundation & Finance Dashboard. "
        "Provides authentication, RBAC, transaction/invoice/settlement/exception management, "
        "and audit logging. AI reconciliation features will be introduced in Phase 2+."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(transactions.router, prefix=API_PREFIX)
app.include_router(invoices.router, prefix=API_PREFIX)
app.include_router(settlements.router, prefix=API_PREFIX)
app.include_router(bank_transactions.router, prefix=API_PREFIX)
app.include_router(exceptions.router, prefix=API_PREFIX)
app.include_router(audit_logs.router, prefix=API_PREFIX)


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "version": settings.APP_VERSION}
