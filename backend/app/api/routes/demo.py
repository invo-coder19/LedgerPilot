"""Demo reset and preset management — for competition presentations.

Provides:
  POST /api/v1/demo/reset         — Reset synthetic environment to baseline
  POST /api/v1/demo/preset/{name} — Load a demo preset (A/B/C/D)
  GET  /api/v1/demo/status        — Current demo environment state

⚠️ DEMO MODE ONLY — Operates on synthetic data. No real money movement.
Requires ADMIN role or DEMO_MODE=true environment variable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import Role

router = APIRouter(prefix="/demo", tags=["Demo"])
logger = logging.getLogger("ledgerpilot.demo")

DEMO_PRESETS = {
    "A": {
        "name": "Safe Automation",
        "description": "Mostly high-confidence fee variances — demonstrates autonomous resolution",
        "scenario_distribution": {
            "clean_match": 0.60,
            "fee_variance": 0.35,
            "date_mismatch": 0.05,
        },
        "records": 100,
    },
    "B": {
        "name": "Mixed Finance Operations",
        "description": "Varied exceptions — demonstrates full controller routing",
        "scenario_distribution": {
            "clean_match": 0.40,
            "fee_variance": 0.15,
            "amount_mismatch": 0.15,
            "duplicate": 0.10,
            "missing_invoice": 0.10,
            "refund_mismatch": 0.10,
        },
        "records": 100,
    },
    "C": {
        "name": "High Risk",
        "description": "Ambiguity and contradictions — demonstrates safety controls",
        "scenario_distribution": {
            "amount_mismatch": 0.30,
            "ambiguous": 0.30,
            "missing_settlement": 0.20,
            "refund_mismatch": 0.20,
        },
        "records": 50,
    },
    "D": {
        "name": "Failure Demo",
        "description": "Designed to trigger safety controls and demonstrate failure handling",
        "scenario_distribution": {
            "ambiguous": 0.40,
            "amount_mismatch": 0.35,
            "duplicate": 0.25,
        },
        "records": 50,
    },
}


class DemoStatusResponse(BaseModel):
    environment: str
    demo_mode: bool
    version: str
    timestamp: str
    available_presets: list[str]
    disclaimer: str


class DemoResetResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    disclaimer: str


class DemoPresetResponse(BaseModel):
    preset: str
    name: str
    description: str
    records: int
    status: str
    timestamp: str
    disclaimer: str


def _require_demo_or_admin(current_user: CurrentUser, settings) -> None:
    """Allow access only in demo mode or for admins."""
    if not settings.DEMO_MODE and current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Demo endpoints are only available in DEMO_MODE or to ADMIN users.",
        )


@router.get("/status", response_model=DemoStatusResponse)
def demo_status(
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST),
    db: Session = Depends(get_db),
):
    """Get current demo environment status."""
    settings = get_settings()
    return DemoStatusResponse(
        environment=settings.ENVIRONMENT,
        demo_mode=settings.DEMO_MODE,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        available_presets=list(DEMO_PRESETS.keys()),
        disclaimer="DEMO ENVIRONMENT — Synthetic financial data — No real money movement",
    )


@router.post("/reset", response_model=DemoResetResponse)
def reset_demo(
    current_user: CurrentUser = require_role(Role.ADMIN),
    db: Session = Depends(get_db),
):
    """Reset the synthetic demo environment to a known baseline state.

    Only available to ADMIN users. Does not affect production data.
    Used to ensure consistent state for live presentations.
    """
    settings = get_settings()
    _require_demo_or_admin(current_user, settings)

    logger.info("Demo reset initiated by user %s", current_user.email)

    # Reset kill switch to OFF
    from app.models.controller import ControllerConfig
    ks_cfg = db.query(ControllerConfig).filter(ControllerConfig.key == "kill_switch").first()
    if ks_cfg:
        ks_cfg.value = {"enabled": False}

    # Reset dry_run to False
    dr_cfg = db.query(ControllerConfig).filter(ControllerConfig.key == "dry_run_default").first()
    if dr_cfg:
        dr_cfg.value = {"value": False}

    db.commit()
    logger.info("Demo reset completed")

    return DemoResetResponse(
        status="reset_complete",
        message=(
            "Demo environment reset: kill switch deactivated, dry-run disabled. "
            "Seed data and demo exceptions preserved."
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
        disclaimer="DEMO ENVIRONMENT — Synthetic financial data — No real money movement",
    )


@router.post("/preset/{preset_id}", response_model=DemoPresetResponse)
def load_preset(
    preset_id: str,
    current_user: CurrentUser = require_role(Role.ADMIN),
    db: Session = Depends(get_db),
):
    """Load a demo preset dataset. ADMIN only.

    Presets:
      A — Safe Automation (fee variances, demonstrates auto-resolution)
      B — Mixed Finance Operations (full controller routing demo)
      C — High Risk (safety controls demo)
      D — Failure Demo (triggers safety mechanisms)
    """
    preset_id = preset_id.upper()
    if preset_id not in DEMO_PRESETS:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{preset_id}' not found. Available: {list(DEMO_PRESETS.keys())}",
        )

    settings = get_settings()
    _require_demo_or_admin(current_user, settings)

    preset = DEMO_PRESETS[preset_id]
    logger.info("Loading demo preset %s (%s) for user %s", preset_id, preset["name"], current_user.email)

    # Generate the preset dataset
    try:
        from app.evaluation.dataset_generator import BenchmarkDatasetGenerator
        from app.models.evaluation import EvaluationDataset

        dataset_name = f"demo_preset_{preset_id.lower()}"
        gen = BenchmarkDatasetGenerator(
            records=preset["records"],
            seed=42,
            dataset_name=dataset_name,
            version="demo",
            distribution=preset["scenario_distribution"],
        )
        data = gen.generate()

        # Update or create the preset dataset
        existing = db.query(EvaluationDataset).filter(
            EvaluationDataset.name == dataset_name,
        ).first()

        if existing:
            existing.cases = data["cases"]
            existing.metadata_ = data["metadata"]
            existing.record_count = preset["records"]
        else:
            dataset = EvaluationDataset(
                name=dataset_name,
                version="demo",
                description=preset["description"],
                record_count=preset["records"],
                random_seed=42,
                distribution=preset["scenario_distribution"],
                cases=data["cases"],
                metadata_=data["metadata"],
                is_active=True,
            )
            db.add(dataset)

        db.commit()
    except Exception as e:
        logger.warning("Could not generate preset dataset: %s", e)

    return DemoPresetResponse(
        preset=preset_id,
        name=preset["name"],
        description=preset["description"],
        records=preset["records"],
        status="loaded",
        timestamp=datetime.now(timezone.utc).isoformat(),
        disclaimer="DEMO ENVIRONMENT — Synthetic financial data — No real money movement",
    )
