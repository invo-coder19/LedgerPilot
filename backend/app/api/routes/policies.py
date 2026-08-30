"""Policy management API routes — CRUD with version control."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.models.controller import ControllerPolicy, PolicyStatus
from app.models.user import Role
from app.schemas.controller import (
    PolicyCreateRequest, PolicyListResponse,
    PolicyResponse, PolicyUpdateRequest,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/controller/policies", tags=["Policies"])


@router.get("", response_model=PolicyListResponse)
def list_policies(
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """List all policies (active + inactive for version history)."""
    policies = (
        db.query(ControllerPolicy)
        .order_by(ControllerPolicy.policy_id, ControllerPolicy.version.desc())
        .all()
    )
    return PolicyListResponse(
        total=len(policies),
        items=[PolicyResponse.model_validate(p) for p in policies],
    )


@router.get("/{policy_uuid}", response_model=PolicyResponse)
def get_policy(
    policy_uuid: uuid.UUID,
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """Get a specific policy version."""
    policy = db.get(ControllerPolicy, policy_uuid)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return PolicyResponse.model_validate(policy)


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    body: PolicyCreateRequest,
    current_user: CurrentUser = require_role(Role.ADMIN),
    db: Session = Depends(get_db),
):
    """Create a new policy. ADMIN only."""
    # Check if policy_id already exists
    existing = (
        db.query(ControllerPolicy)
        .filter(ControllerPolicy.policy_id == body.policy_id)
        .first()
    )
    version = 1
    if existing:
        max_ver = (
            db.query(ControllerPolicy)
            .filter(ControllerPolicy.policy_id == body.policy_id)
            .order_by(ControllerPolicy.version.desc())
            .first()
        )
        version = (max_ver.version + 1) if max_ver else 1

    policy = ControllerPolicy(
        policy_id=body.policy_id,
        version=version,
        name=body.name,
        description=body.description,
        configuration=body.configuration,
        status=PolicyStatus.ACTIVE,
        created_by=current_user.id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    AuditService(db).log(
        AuditAction.POLICY_CREATED,
        f"Policy {body.policy_id} v{version} created",
        user_id=current_user.id,
        entity_type="policy",
        entity_id=str(policy.id),
    )

    return PolicyResponse.model_validate(policy)


@router.patch("/{policy_uuid}", response_model=PolicyResponse)
def update_policy(
    policy_uuid: uuid.UUID,
    body: PolicyUpdateRequest,
    current_user: CurrentUser = require_role(Role.ADMIN),
    db: Session = Depends(get_db),
):
    """Update a policy — creates a new version, deactivates the old one. ADMIN only."""
    old_policy = db.get(ControllerPolicy, policy_uuid)
    if not old_policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Deactivate old version
    old_policy.status = PolicyStatus.INACTIVE

    # Create new version
    new_policy = ControllerPolicy(
        policy_id=old_policy.policy_id,
        version=old_policy.version + 1,
        name=body.name or old_policy.name,
        description=body.description if body.description is not None else old_policy.description,
        configuration=body.configuration or old_policy.configuration,
        status=PolicyStatus.ACTIVE,
        created_by=current_user.id,
    )
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)

    AuditService(db).log(
        AuditAction.POLICY_UPDATED,
        f"Policy {old_policy.policy_id} updated: v{old_policy.version} → v{new_policy.version}",
        user_id=current_user.id,
        entity_type="policy",
        entity_id=str(new_policy.id),
    )

    return PolicyResponse.model_validate(new_policy)
