"""Simulation API routes."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.database import get_db
from app.models.user import Role
from app.simulation.scenarios import ALL_SCENARIOS, SCENARIO_MAP

router = APIRouter(prefix="/simulation", tags=["Simulation"])


class ScenarioResponse(BaseModel):
    id: str
    name: str
    category: str
    description: str
    failure_injected: str
    expected_outcome: str
    safety_property: str


class SimulationRunResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    passed: bool
    initial_state: dict[str, Any] = {}
    failure_injected: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    evidence: list[str] = []
    duration_ms: float = 0.0
    error: Optional[str] = None
    timestamp: str = ""
    demo_disclaimer: str = "DEMO / SIMULATION MODE — NO REAL MONEY MOVEMENT"


@router.get("/scenarios", response_model=list[ScenarioResponse])
def list_scenarios(
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST),
):
    """List all 9 defined failure scenarios."""
    return [
        ScenarioResponse(
            id=s.id,
            name=s.name,
            category=s.category,
            description=s.description,
            failure_injected=s.failure_injected,
            expected_outcome=s.expected_outcome,
            safety_property=s.safety_property,
        )
        for s in ALL_SCENARIOS
    ]


@router.post("/run/{scenario_id}", response_model=SimulationRunResponse)
def run_scenario(
    scenario_id: str,
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER),
    db: Session = Depends(get_db),
):
    """Run a specific failure simulation scenario. FINANCE_MANAGER+ only.

    ⚠️ DEMO / SIMULATION MODE — NO REAL MONEY MOVEMENT.
    Operates on synthetic data only. State is always restored after simulation.
    """
    if scenario_id not in SCENARIO_MAP:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    from app.simulation.runner import run_scenario as _run

    result = _run(db=db, scenario_id=scenario_id)
    return SimulationRunResponse(
        scenario_id=result.scenario_id,
        scenario_name=result.scenario_name,
        passed=result.passed,
        initial_state=result.initial_state,
        failure_injected=result.failure_injected,
        expected_behavior=result.expected_behavior,
        actual_behavior=result.actual_behavior,
        evidence=result.evidence,
        duration_ms=result.duration_ms,
        error=result.error,
        timestamp=result.timestamp,
    )


@router.post("/run-all", response_model=list[SimulationRunResponse])
def run_all_scenarios(
    current_user: CurrentUser = require_role(Role.ADMIN),
    db: Session = Depends(get_db),
):
    """Run all 9 failure simulation scenarios. ADMIN only.

    ⚠️ DEMO / SIMULATION MODE — NO REAL MONEY MOVEMENT.
    """
    from app.simulation.runner import run_scenario as _run

    results = []
    for scenario in ALL_SCENARIOS:
        result = _run(db=db, scenario_id=scenario.id)
        results.append(SimulationRunResponse(
            scenario_id=result.scenario_id,
            scenario_name=result.scenario_name,
            passed=result.passed,
            initial_state=result.initial_state,
            failure_injected=result.failure_injected,
            expected_behavior=result.expected_behavior,
            actual_behavior=result.actual_behavior,
            evidence=result.evidence,
            duration_ms=result.duration_ms,
            error=result.error,
            timestamp=result.timestamp,
        ))
    return results
