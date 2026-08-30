"""Controller configuration API — kill switch, safety limits."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.models.controller import ControllerConfig
from app.models.user import Role
from app.schemas.controller import ControllerConfigResponse, ControllerConfigUpdate
from app.services.audit_service import AuditService

router = APIRouter(prefix="/controller/config", tags=["Controller Config"])

# Default configuration values
_DEFAULTS = {
    "kill_switch": {"enabled": False},
    "max_auto_amount": {"value": 10000.0},
    "max_auto_per_run": {"value": 500},
    "max_auto_per_hour": {"value": 1000},
    "max_concurrent": {"value": 10},
    "dry_run_default": {"value": False},
}


def _get_config(db: Session) -> dict:
    """Load all config values, falling back to defaults."""
    configs = db.query(ControllerConfig).all()
    config_map = {c.key: c.value for c in configs}
    return {
        key: config_map.get(key, default)
        for key, default in _DEFAULTS.items()
    }


@router.get("", response_model=ControllerConfigResponse)
def get_config(
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """Get current controller configuration."""
    cfg = _get_config(db)
    return ControllerConfigResponse(
        kill_switch=cfg["kill_switch"].get("enabled", False),
        max_auto_amount=cfg["max_auto_amount"].get("value", 10000.0),
        max_auto_per_run=cfg["max_auto_per_run"].get("value", 500),
        max_auto_per_hour=cfg["max_auto_per_hour"].get("value", 1000),
        max_concurrent=cfg["max_concurrent"].get("value", 10),
        dry_run_default=cfg["dry_run_default"].get("value", False),
    )


@router.patch("", response_model=ControllerConfigResponse)
def update_config(
    body: ControllerConfigUpdate,
    current_user: CurrentUser = require_role(Role.ADMIN),
    db: Session = Depends(get_db),
):
    """Update controller configuration. ADMIN only.

    Includes kill switch — when enabled, blocks all new autonomous actions.
    """
    audit = AuditService(db)
    updates = body.model_dump(exclude_none=True)

    for key, value in updates.items():
        if key == "kill_switch":
            _upsert_config(db, "kill_switch", {"enabled": value}, current_user.id)
            audit.log(
                AuditAction.KILL_SWITCH_TOGGLED,
                f"Kill switch {'ENABLED' if value else 'DISABLED'} by {current_user.email}",
                user_id=current_user.id,
                entity_type="controller_config",
                entity_id="kill_switch",
                metadata={"enabled": value},
            )
        else:
            _upsert_config(db, key, {"value": value}, current_user.id)

    db.commit()
    return get_config(current_user=current_user, db=db)


def _upsert_config(
    db: Session, key: str, value: dict, user_id=None
) -> None:
    """Insert or update a config key."""
    existing = db.query(ControllerConfig).filter(
        ControllerConfig.key == key
    ).first()
    if existing:
        existing.value = value
        existing.updated_at = datetime.now(timezone.utc)
        existing.updated_by = user_id
    else:
        db.add(ControllerConfig(
            key=key,
            value=value,
            updated_by=user_id,
        ))
