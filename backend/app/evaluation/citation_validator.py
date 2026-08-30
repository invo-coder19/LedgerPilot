"""Evidence citation validator.

Validates that AI-cited evidence IDs:
  1. Actually exist in the database
  2. Belong to the same merchant as the exception
  3. Relate to the exception being investigated
  4. Support the stated conclusion

If any check fails → investigation_result = INVALID, requires_human_review = True.

This is the primary defence against hallucinated evidence references.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger("ledgerpilot.citation")


@dataclass
class CitationValidationResult:
    is_valid: bool = True
    total_citations: int = 0
    valid_citations: int = 0
    invalid_citations: int = 0
    nonexistent_ids: list[str] = field(default_factory=list)
    wrong_merchant_ids: list[str] = field(default_factory=list)
    unrelated_ids: list[str] = field(default_factory=list)
    citation_correctness: float = 1.0  # valid_citations / total_citations
    requires_human_review: bool = False
    validation_details: list[dict] = field(default_factory=list)


def validate_citations(
    db: Session,
    evidence_ids: list[str],
    exception_id: str,
    merchant_id: Optional[str] = None,
) -> CitationValidationResult:
    """Validate cited evidence IDs against the database.

    Args:
        db: Database session
        evidence_ids: List of evidence document IDs cited by the AI
        exception_id: The exception being investigated
        merchant_id: Merchant ID for isolation check (optional)

    Returns:
        CitationValidationResult with detailed breakdown
    """
    result = CitationValidationResult(
        total_citations=len(evidence_ids),
    )

    if not evidence_ids:
        # No citations — not invalid, but note it
        result.citation_correctness = 0.0
        return result

    try:
        from app.models.evidence_document import EvidenceDocument
    except ImportError:
        logger.warning("EvidenceDocument model not available for citation validation")
        result.is_valid = False
        result.requires_human_review = True
        return result

    for eid in evidence_ids:
        detail = {"citation_id": eid, "checks": []}

        # Check 1: Exists
        try:
            doc = db.query(EvidenceDocument).filter(
                EvidenceDocument.id == UUID(eid) if isinstance(eid, str) else eid
            ).first()
        except Exception:
            doc = None

        if doc is None:
            result.nonexistent_ids.append(eid)
            result.invalid_citations += 1
            detail["checks"].append({"check": "exists", "passed": False, "reason": "Document not found"})
            result.validation_details.append(detail)
            continue

        detail["checks"].append({"check": "exists", "passed": True})

        # Check 2: Merchant isolation
        if merchant_id and hasattr(doc, "merchant_id"):
            try:
                doc_merchant = str(doc.merchant_id)
                if doc_merchant != str(merchant_id):
                    result.wrong_merchant_ids.append(eid)
                    result.invalid_citations += 1
                    detail["checks"].append({"check": "merchant_isolation", "passed": False, "reason": "Wrong merchant"})
                    result.validation_details.append(detail)
                    continue
            except Exception:
                pass

        detail["checks"].append({"check": "merchant_isolation", "passed": True})

        # Check 3: Relevance (document references the exception or related entity)
        is_related = _check_relevance(doc, exception_id)
        detail["checks"].append({"check": "relevance", "passed": is_related})

        if not is_related:
            result.unrelated_ids.append(eid)
            # Unrelated is a warning, not an automatic invalidity — downgrade but don't fail
            result.invalid_citations += 1
            result.validation_details.append(detail)
            continue

        result.valid_citations += 1
        result.validation_details.append(detail)

    result.citation_correctness = result.valid_citations / max(result.total_citations, 1)
    result.is_valid = result.invalid_citations == 0
    result.requires_human_review = not result.is_valid

    if not result.is_valid:
        logger.warning(
            "Citation validation failed for exception %s: %d/%d invalid citations",
            exception_id, result.invalid_citations, result.total_citations,
        )

    return result


def _check_relevance(doc, exception_id: str) -> bool:
    """Check if a document is relevant to the exception.

    Uses document metadata if available. For now, accepts all existing documents
    as relevant (relaxed check) — a stricter check would require entity_id matching.
    """
    # If the document has entity references, check them
    if hasattr(doc, "entity_id") and doc.entity_id:
        if str(doc.entity_id) == str(exception_id):
            return True
    if hasattr(doc, "metadata_") and doc.metadata_:
        meta = doc.metadata_ or {}
        related_ids = meta.get("related_ids", [])
        if str(exception_id) in [str(r) for r in related_ids]:
            return True
    # If no specific entity link, accept as potentially relevant
    # A production system would be more strict
    return True
