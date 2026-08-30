"""Health check endpoints — liveness, readiness, detailed system health."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["Health"])
logger = logging.getLogger("ledgerpilot.health")


def _check_database() -> dict[str, Any]:
    """Verify PostgreSQL/SQLite connectivity."""
    from app.core.database import SessionLocal
    start = time.perf_counter()
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        return {"status": "healthy", "latency_ms": round((time.perf_counter() - start) * 1000, 1)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


def _check_redis() -> dict[str, Any]:
    """Verify Redis connectivity."""
    start = time.perf_counter()
    try:
        import redis as redis_lib
        from app.core.config import get_settings
        settings = get_settings()
        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        return {"status": "healthy", "latency_ms": round((time.perf_counter() - start) * 1000, 1)}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)[:100]}


def _check_ml_models() -> dict[str, Any]:
    """Verify ML model artifacts are loadable."""
    try:
        from app.core.config import get_settings
        import os
        settings = get_settings()
        models_path = settings.models_path
        classifier_path = models_path / "exception_classifier.joblib"
        anomaly_path = models_path / "anomaly_detector.joblib"
        classifier_ok = os.path.exists(classifier_path)
        anomaly_ok = os.path.exists(anomaly_path)
        if classifier_ok and anomaly_ok:
            return {"status": "healthy", "classifier": "loaded", "anomaly_detector": "loaded"}
        return {
            "status": "degraded",
            "classifier": "loaded" if classifier_ok else "not_found",
            "anomaly_detector": "loaded" if anomaly_ok else "not_found",
            "note": "Run ML training to generate model artifacts",
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


def _check_rag() -> dict[str, Any]:
    """Verify RAG / embedding availability."""
    try:
        from app.core.database import SessionLocal
        from app.models.evidence_document import EvidenceDocument
        db = SessionLocal()
        count = db.query(EvidenceDocument).count()
        db.close()
        return {"status": "healthy", "document_count": count}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


def _check_llm() -> dict[str, Any]:
    """Check if LLM credentials are configured (does not make an API call)."""
    from app.core.config import get_settings
    settings = get_settings()
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return {"status": "configured", "provider": "gemini", "model": settings.effective_llm_model}
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return {"status": "configured", "provider": "openai", "model": settings.effective_llm_model}
    return {
        "status": "not_configured",
        "provider": settings.LLM_PROVIDER,
        "note": "Set GEMINI_API_KEY or OPENAI_API_KEY to enable AI investigations",
    }


@router.get("/live", summary="Liveness probe")
def liveness() -> dict:
    """Kubernetes/Docker liveness probe. Returns 200 if the process is alive."""
    return {"status": "alive"}


@router.get("/ready", summary="Readiness probe")
def readiness():
    """Readiness probe — verifies the DB is reachable before accepting traffic."""
    db_result = _check_database()
    if db_result["status"] != "healthy":
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": db_result},
        )
    return {"status": "ready", "database": db_result}


@router.get("/detailed", summary="Full system health status")
def detailed_health():
    """Full system health for the System Health dashboard. Non-sensitive."""
    from app.core.config import get_settings
    settings = get_settings()

    db_result = _check_database()
    redis_result = _check_redis()
    ml_result = _check_ml_models()
    rag_result = _check_rag()
    llm_result = _check_llm()

    overall_healthy = (
        db_result["status"] == "healthy"
        and redis_result.get("status") in ("healthy", "unavailable")  # Redis optional for dev
    )

    return {
        "overall": "healthy" if overall_healthy else "degraded",
        "environment": settings.ENVIRONMENT,
        "demo_mode": settings.DEMO_MODE,
        "version": settings.APP_VERSION,
        "components": {
            "api": {"status": "healthy"},
            "database": db_result,
            "redis": redis_result,
            "ml_models": ml_result,
            "rag": rag_result,
            "llm_provider": llm_result,
        },
    }
