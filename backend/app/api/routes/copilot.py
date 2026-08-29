"""Finance Copilot API route — Phase 3B.

Answers merchant-scoped finance questions using real database data.
NOT a generic chatbot. Only answers based on real LedgerPilot data.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.agents.prompts import COPILOT_SYSTEM
from app.agents.provider import get_provider
from app.agents.tools import InvestigationTools
from app.core.config import get_settings
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.models.merchant import Merchant
from app.schemas.investigation import CopilotRequest, CopilotResponse
from app.services.audit_service import AuditService

router = APIRouter(tags=["Finance Copilot"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _resolve_merchant_id(db: Session):
    merchant = db.query(Merchant).first()
    return merchant.id if merchant else None


@router.post("/copilot/ask", response_model=CopilotResponse, summary="Ask Finance Copilot")
def ask_copilot(
    request: CopilotRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> CopilotResponse:
    """Answer a finance question using real merchant data.

    The copilot searches evidence, exceptions, and transactions to provide
    a grounded, data-backed answer. It will not invent financial data.
    """
    merchant_id = _resolve_merchant_id(db)
    tools = InvestigationTools(db=db, merchant_id=merchant_id)

    AuditService(db).log(
        AuditAction.COPILOT_QUERY,
        f"Copilot query: {request.question[:100]}",
        user_id=current_user.id,
        merchant_id=merchant_id,
    )

    # 1. Search evidence relevant to the question
    evidence = tools.search_evidence(query=request.question, top_k=6)
    finance_rules = tools.get_finance_rules(request.question)
    all_evidence = evidence + finance_rules

    # 2. Build context for LLM
    evidence_text = "\n".join(
        f"[{e.get('source_type', '?')}] {e.get('title', '')}: {e.get('content', '')[:300]}"
        for e in all_evidence[:settings.AI_MAX_CONTEXT_ITEMS]
    ) or "No directly relevant records found."

    user_msg = f"""Question: {request.question}

Available data from LedgerPilot:
{evidence_text}

Answer the question using only the data above. If data is insufficient, say so."""

    # 3. Call LLM
    try:
        provider = get_provider()
        raw = provider.complete(COPILOT_SYSTEM, user_msg)

        # Try to parse as JSON, fall back to raw text
        try:
            import json
            parsed = json.loads(raw.strip().strip("```json").strip("```").strip())
            answer = parsed.get("answer", raw)
        except Exception:
            answer = raw

    except Exception as exc:
        logger.warning("Copilot LLM call failed: %s", exc)
        answer = (
            "AI Copilot is temporarily unavailable. "
            "Please review the evidence sections in LedgerPilot directly."
        )

    return CopilotResponse(
        answer=answer,
        evidence_used=[
            {
                "id": e.get("id"),
                "title": e.get("title"),
                "source_type": e.get("source_type"),
            }
            for e in all_evidence[:5]
        ],
    )
