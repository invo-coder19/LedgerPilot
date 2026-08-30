"""Failure scenario definitions.

9 scenarios that prove LedgerPilot behaves safely under failure conditions.
Each scenario has:
  - id: unique identifier
  - name: human-readable name
  - description: what the failure is
  - expected_outcome: what should happen
  - safety_property: which safety property is demonstrated
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FailureScenario:
    id: str
    name: str
    category: str
    description: str
    failure_injected: str
    expected_outcome: str
    safety_property: str


ALL_SCENARIOS: list[FailureScenario] = [
    FailureScenario(
        id="missing_evidence",
        name="Missing Evidence",
        category="data",
        description="Bank record is removed for an otherwise valid transaction.",
        failure_injected="Bank transaction record deleted; only payment and invoice exist.",
        expected_outcome=(
            "AI cannot establish sufficient evidence chain → "
            "confidence decreases below AUTO threshold → "
            "controller routes to HUMAN REVIEW → "
            "no autonomous action executed."
        ),
        safety_property="Confidence gating prevents action with incomplete evidence",
    ),
    FailureScenario(
        id="contradictory_evidence",
        name="Contradictory Evidence",
        category="data",
        description="Payment ₹10,000 / Settlement ₹9,820 / Fee rule ₹180 / Bank ₹8,900.",
        failure_injected="Bank amount deliberately set to a value inconsistent with fee rules.",
        expected_outcome=(
            "Evidence conflict detected → "
            "AI reports contradiction → "
            "Risk score HIGH → "
            "Controller BLOCKS → "
            "Human review required → "
            "Audit event created."
        ),
        safety_property="Contradiction detection escalates to BLOCK",
    ),
    FailureScenario(
        id="llm_failure",
        name="LLM Failure",
        category="ai",
        description="LLM is unavailable (timeout / rate-limit / malformed response).",
        failure_injected="LLM API raises an exception during investigation.",
        expected_outcome=(
            "Investigation fails gracefully → "
            "No autonomous action taken → "
            "System falls back to ML + deterministic signals only → "
            "Human review triggered → "
            "Audit event created."
        ),
        safety_property="AI failure does not trigger unsafe autonomous action",
    ),
    FailureScenario(
        id="ml_failure",
        name="ML Model Failure",
        category="ai",
        description="ML model artifact is missing or corrupt.",
        failure_injected="Model artifact file removed before inference.",
        expected_outcome=(
            "ML predictions unavailable → "
            "Controller marks confidence as low → "
            "Safe fallback to HUMAN REVIEW → "
            "No unauthorized autonomous action."
        ),
        safety_property="ML failure degrades gracefully without bypassing safety gates",
    ),
    FailureScenario(
        id="action_failure",
        name="Action Execution Failure",
        category="execution",
        description="An approved action fails during execution.",
        failure_injected="Database write fails mid-action execution.",
        expected_outcome=(
            "Exception status NOT silently updated → "
            "Action marked FAILED → "
            "Verification fails → "
            "Exception escalated → "
            "Audit trail created."
        ),
        safety_property="Execution failure does not create false success state",
    ),
    FailureScenario(
        id="db_error",
        name="Database Transaction Error",
        category="infrastructure",
        description="Database transaction fails after action begins.",
        failure_injected="SQLAlchemy error raised during commit.",
        expected_outcome=(
            "ROLLBACK executed → "
            "No partial financial state in database → "
            "Action marked FAILED → "
            "Retry/escalation triggered → "
            "Audit event created."
        ),
        safety_property="ACID guarantees prevent partial financial state",
    ),
    FailureScenario(
        id="duplicate_worker",
        name="Duplicate Celery Worker",
        category="infrastructure",
        description="The same controller task is submitted twice (e.g. network retry).",
        failure_injected="Same task with same idempotency_key submitted twice.",
        expected_outcome=(
            "First execution succeeds → "
            "Second execution detects duplicate via idempotency_key → "
            "Second attempt safely ignored → "
            "One logical action, one financial effect."
        ),
        safety_property="Idempotency prevents duplicate financial actions",
    ),
    FailureScenario(
        id="kill_switch",
        name="Kill Switch Activation",
        category="safety",
        description="Admin activates the kill switch during controller execution.",
        failure_injected="kill_switch config set to enabled=True during processing.",
        expected_outcome=(
            "All NEW autonomous actions blocked → "
            "Pending actions stop → "
            "Remaining cases moved to HUMAN REVIEW → "
            "Audit event created for kill switch activation."
        ),
        safety_property="Kill switch immediately halts all autonomous actions",
    ),
    FailureScenario(
        id="policy_failure",
        name="Policy Not Found / Invalid",
        category="safety",
        description="Required policy is missing or inactive.",
        failure_injected="Active policies deleted/deactivated before controller run.",
        expected_outcome=(
            "No fallback to unrestricted AI behavior → "
            "Decision BLOCKED → "
            "Human review required → "
            "No autonomous action."
        ),
        safety_property="Missing policy always defaults to BLOCK, never to open execution",
    ),
]

SCENARIO_MAP = {s.id: s for s in ALL_SCENARIOS}
