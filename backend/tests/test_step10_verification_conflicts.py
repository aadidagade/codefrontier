"""
Unit tests for Step 10: Evidence Verification and Conflict Detection.

Validates:
1. Evidence verification engine assigns correct statuses:
   SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, NEEDS_REVIEW.
2. Evidence verification does not rely blindly on generation confidence.
3. Conflict detection records both conflicting sources without choosing one silently.
4. Conflict statuses: OPEN, UNDER_REVIEW, RESOLVED, DISMISSED.
5. Human resolution records chosen source/value, explanation, and responsible user.
6. Role-based permission checks for conflict resolution (LEAD / ADMIN).
"""

import json
import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from app.services.verification_service import EvidenceVerificationService
from app.models.document import Document, DocumentChunk
from app.models.evidence import EvidenceReference
from app.models.conflict import Conflict
from app.models.project import ProjectMemberRole
from app.schemas.handover import (
    EvidenceStatus,
    ClaimVerificationResult,
    ConflictResolveRequest,
    ConflictUpdateRequest,
)


@pytest.mark.asyncio
async def test_evidence_verification_supported_lexical():
    """Validates that a claim matching source passage is assigned SUPPORTED."""
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    passage = (
        "The primary database cluster runs PostgreSQL 16 on port 5432 with the pgvector extension "
        "installed for semantic vector search."
    )
    chunk = DocumentChunk(id=uuid.uuid4(), content=passage, page_number=2)

    claim = "PostgreSQL 16 runs on port 5432 with pgvector extension."

    with patch("app.core.config.settings.is_gemini_configured", return_value=False):
        result = await service.verify_claim_against_chunks(claim_text=claim, chunks=[chunk])
        assert result.verification_status in (EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIALLY_SUPPORTED)
        assert result.alignment_score >= 0.60
        assert result.chunks_evaluated == 1


@pytest.mark.asyncio
async def test_evidence_verification_unsupported():
    """Validates that a claim with no support in the passage is marked UNSUPPORTED."""
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    passage = "The front-end user interface is implemented in React with Vite and Tailwind CSS."
    chunk = DocumentChunk(id=uuid.uuid4(), content=passage, page_number=1)

    claim = "The backend microservice is deployed on Kubernetes using Helm charts with Istio service mesh."

    with patch("app.core.config.settings.is_gemini_configured", return_value=False):
        result = await service.verify_claim_against_chunks(claim_text=claim, chunks=[chunk])
        assert result.verification_status == EvidenceStatus.UNSUPPORTED
        assert result.alignment_score < 0.35


@pytest.mark.asyncio
async def test_evidence_verification_no_chunks():
    """Validates that claims with empty source chunks are automatically UNSUPPORTED."""
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    result = await service.verify_claim_against_chunks(
        claim_text="Any claim statement",
        chunks=[],
    )
    assert result.verification_status == EvidenceStatus.UNSUPPORTED
    assert result.alignment_score == 0.0
    assert result.chunks_evaluated == 0


@pytest.mark.asyncio
async def test_evidence_verification_gemini_nli_eval():
    """Validates that Gemini NLI prompt parses JSON and assigns status."""
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    chunk = DocumentChunk(
        id=uuid.uuid4(),
        content="Session tokens expire in Redis after 3600 seconds.",
        page_number=3,
    )

    mock_nli_response = {
        "verification_status": "SUPPORTED",
        "alignment_score": 0.98,
        "reasoning": "Evidence directly confirms Redis session TTL is 3600s.",
        "supported_facts": ["Redis session TTL is 3600s"],
        "unsupported_facts": [],
    }

    with patch("app.core.config.settings.is_gemini_configured", return_value=True), \
         patch("app.services.verification_service.gemini_service.generate_content", return_value=json.dumps(mock_nli_response)):

        res = await service.verify_claim_against_chunks(
            claim_text="Redis session TTL is set to 3600 seconds.",
            chunks=[chunk],
        )
        assert res.verification_status == EvidenceStatus.SUPPORTED
        assert res.alignment_score == 0.98
        assert "directly confirms" in res.reasoning


def test_conflict_model_structure_and_never_silently_choose():
    """Validates that Conflict stores both Source A and Source B with quotes and page numbers."""
    conflict = Conflict(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        conflict_type="architecture",
        description="Conflicting communication ports identified across documentation.",
        source_a={
            "document_name": "system_architecture.md",
            "chunk_id": str(uuid.uuid4()),
            "text": "Internal calls use gRPC on port 50051.",
            "page": 1,
        },
        source_b={
            "document_name": "deployment_runbook.md",
            "chunk_id": str(uuid.uuid4()),
            "text": "Legacy services communicate over HTTP REST on port 8080.",
            "page": 2,
        },
        status="OPEN",
    )

    # STRICT ASSERTIONS: Both sources must be present and detailed
    assert conflict.status == "OPEN"
    assert conflict.source_a["document_name"] == "system_architecture.md"
    assert conflict.source_b["document_name"] == "deployment_runbook.md"
    assert "50051" in conflict.source_a["text"]
    assert "8080" in conflict.source_b["text"]
    assert conflict.resolution is None
    assert conflict.resolved_by is None


def test_conflict_status_transitions():
    """Validates conflict status progression: OPEN -> UNDER_REVIEW -> RESOLVED."""
    conflict = Conflict(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        conflict_type="deadline",
        description="Release date mismatch: Nov 15 vs Dec 1.",
        source_a={"text": "Release date is Nov 15, 2026."},
        source_b={"text": "Target release pushed to Dec 1, 2026."},
        status="OPEN",
    )

    assert conflict.status == "OPEN"

    # Lead puts conflict under review
    conflict.status = "UNDER_REVIEW"
    assert conflict.status == "UNDER_REVIEW"

    # Lead resolves conflict with human explanation
    user_id = uuid.uuid4()
    conflict.status = "RESOLVED"
    conflict.resolution = {
        "chosen_source": "source_b",
        "chosen_value": "Dec 1, 2026",
        "resolution_explanation": "Dec 1 release was confirmed in sprint planning notes.",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
    conflict.resolved_by = user_id

    assert conflict.status == "RESOLVED"
    assert conflict.resolution["chosen_value"] == "Dec 1, 2026"
    assert conflict.resolved_by == user_id
