"""
Comprehensive test suite for the Advanced Evidence Verification Engine.

Validates all 10 requirements:
1. Integration with existing Gemini API (structured responses & Pydantic validation).
2. Section-by-section handover analysis.
3. Document chunk retrieval from existing retrieval system.
4. Claim comparison against supporting source passages.
5. 5-status classification: Supported, Partially Supported, Unsupported, Conflicting, Insufficient Evidence.
6. Storage of all 8 mandatory claim fields:
   - claim_id
   - claim_text
   - verification_status
   - supporting_document_id
   - source_filename
   - page_number or section_reference
   - supporting_text_excerpt
   - verification_timestamp
7. Never invent evidence or source references (rejects hallucinated references).
8. Claims with missing evidence marked as Unsupported / Insufficient Evidence with null citations.
9. Database persistence into claim_verifications and evidence_references.
10. Proper API endpoints to retrieve verification results.
"""

import json
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import Settings
from app.models.document import Document, DocumentChunk
from app.models.evidence import EvidenceReference, ClaimVerification
from app.models.handover import Handover, HandoverSection
from app.models.user import User
from app.schemas.handover import (
    EvidenceStatus,
    VerificationStatus,
    normalize_verification_status,
    ClaimVerificationRecord,
    SectionVerificationReport,
    AdvancedHandoverVerificationReport,
)
from app.services.verification_service import (
    EvidenceVerificationService,
    StructuredGeminiClaimEvaluation,
)


# =============================================================================
# 1. 5-STATUS CLASSIFICATION & VALIDATION TESTS
# =============================================================================

def test_status_normalization_and_all_5_statuses():
    """Validates that all 5 verification statuses normalize correctly."""
    assert normalize_verification_status("Supported") == "Supported"
    assert normalize_verification_status("SUPPORTED") == "Supported"
    assert normalize_verification_status("Partially Supported") == "Partially Supported"
    assert normalize_verification_status("PARTIALLY_SUPPORTED") == "Partially Supported"
    assert normalize_verification_status("Unsupported") == "Unsupported"
    assert normalize_verification_status("UNSUPPORTED") == "Unsupported"
    assert normalize_verification_status("Conflicting") == "Conflicting"
    assert normalize_verification_status("CONFLICTING") == "Conflicting"
    assert normalize_verification_status("Insufficient Evidence") == "Insufficient Evidence"
    assert normalize_verification_status("INSUFFICIENT_EVIDENCE") == "Insufficient Evidence"
    assert normalize_verification_status("NEEDS_REVIEW") == "Insufficient Evidence"
    assert normalize_verification_status(None) == "Insufficient Evidence"


@pytest.mark.asyncio
async def test_claim_verification_all_8_required_fields_supported():
    """
    Validates Requirement 6: Every claim stores the 8 mandatory fields when supported:
    claim_id, claim_text, verification_status, supporting_document_id, source_filename,
    page_number / section_reference, supporting_text_excerpt, verification_timestamp.
    """
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        original_filename="deployment_guide.pdf",
        project_id=uuid.uuid4(),
    )
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        content="The Redis caching cluster operates on port 6379 with a maxmemory limit of 8GB.",
        page_number=4,
        section_title="Caching Layer Configuration",
    )

    claim_id = "claim_cache_001"
    claim_text = "Redis caching cluster operates on port 6379 with 8GB memory."

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        record = await service.verify_claim(
            claim_id=claim_id,
            claim_text=claim_text,
            candidate_chunks=[(chunk, doc)],
        )

        # 1. Claim ID
        assert record.claim_id == claim_id
        # 2. Claim text
        assert record.claim_text == claim_text
        # 3. Verification status (Supported or Partially Supported)
        assert record.verification_status in (VerificationStatus.SUPPORTED.value, VerificationStatus.PARTIALLY_SUPPORTED.value)
        # 4. Supporting document ID
        assert record.supporting_document_id == doc_id
        # 5. Source filename
        assert record.source_filename == "deployment_guide.pdf"
        # 6. Page number or section reference
        assert record.page_number == 4
        assert record.section_reference == "Caching Layer Configuration"
        # 7. Supporting text excerpt
        assert "6379" in record.supporting_text_excerpt
        # 8. Verification timestamp
        assert isinstance(record.verification_timestamp, datetime)


@pytest.mark.asyncio
async def test_claim_verification_conflicting_classification():
    """Validates that a direct contradiction is classified as Conflicting."""
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, original_filename="architecture.md")
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="PostgreSQL database runs on port 5432.",
        page_number=1,
    )

    # Claim asserts contradictory port 8080
    claim_text = "PostgreSQL database runs on port 8080."

    with patch.object(Settings, "is_gemini_configured", return_value=False):
        record = await service.verify_claim(
            claim_id="claim_db_port",
            claim_text=claim_text,
            candidate_chunks=[(chunk, doc)],
        )
        assert record.verification_status == VerificationStatus.CONFLICTING.value
        assert "Conflicting" in record.reasoning


@pytest.mark.asyncio
async def test_claim_verification_insufficient_evidence_when_no_chunks():
    """
    Validates Requirement 8: If evidence cannot be found, explicitly mark Unsupported
    or Insufficient Evidence, with null document citations (never invent references).
    """
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    record = await service.verify_claim(
        claim_id="claim_missing_01",
        claim_text="Quantum encryption protocol AES-9000 is active.",
        candidate_chunks=[],
    )

    assert record.verification_status == VerificationStatus.INSUFFICIENT_EVIDENCE.value
    # Requirement 7: Never invent evidence or source references
    assert record.supporting_document_id is None
    assert record.source_filename is None
    assert record.page_number is None
    assert record.section_reference is None
    assert record.supporting_text_excerpt is None
    assert record.document_chunk_id is None
    assert isinstance(record.verification_timestamp, datetime)


# =============================================================================
# 2. GEMINI STRUCTURED JSON VALIDATION & HALLUCINATION REJECTION (Req 1 & 7)
# =============================================================================

@pytest.mark.asyncio
async def test_structured_gemini_response_validation():
    """Validates that structured Gemini response is parsed and validated with Pydantic."""
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    doc = Document(id=doc_id, original_filename="security.pdf")
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        content="All passwords are encrypted using Argon2id with 64MB memory cost.",
        page_number=12,
        section_title="Security Standards",
    )

    gemini_json_output = {
        "verification_status": "Supported",
        "alignment_score": 0.99,
        "reasoning": "Passage directly confirms Argon2id encryption with 64MB memory cost.",
        "supporting_chunk_id": str(chunk_id),
        "supporting_text_excerpt": "All passwords are encrypted using Argon2id with 64MB memory cost.",
        "supported_facts": ["Argon2id encryption is used with 64MB memory cost."],
        "unsupported_facts": [],
    }

    with patch.object(Settings, "is_gemini_configured", return_value=True), \
         patch("app.services.verification_service.gemini_service.generate_structured_json", return_value=json.dumps(gemini_json_output)):

        record = await service.verify_claim(
            claim_id="claim_sec_01",
            claim_text="Passwords use Argon2id with 64MB memory cost.",
            candidate_chunks=[(chunk, doc)],
        )

        assert record.verification_status == VerificationStatus.SUPPORTED.value
        assert record.supporting_document_id == doc_id
        assert record.source_filename == "security.pdf"
        assert record.page_number == 12
        assert record.section_reference == "Security Standards"
        assert record.alignment_score == 0.99


@pytest.mark.asyncio
async def test_gemini_hallucinated_chunk_id_is_rejected():
    """
    Validates Requirement 7: Never invent evidence or source references.
    If Gemini hallucinates a random UUID that was NOT in the retrieved passages,
    the engine MUST reject the hallucinated ID and not store it.
    """
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    doc_id = uuid.uuid4()
    real_chunk_id = uuid.uuid4()
    fake_chunk_id = uuid.uuid4()  # Hallucinated by model

    doc = Document(id=doc_id, original_filename="spec.txt")
    chunk = DocumentChunk(id=real_chunk_id, document_id=doc_id, content="System uses port 80.")

    hallucinated_output = {
        "verification_status": "Supported",
        "alignment_score": 0.90,
        "reasoning": "Evidence matches.",
        "supporting_chunk_id": str(fake_chunk_id),  # Not in retrieved set!
        "supporting_text_excerpt": "System uses port 80.",
    }

    with patch.object(Settings, "is_gemini_configured", return_value=True), \
         patch("app.services.verification_service.gemini_service.generate_structured_json", return_value=json.dumps(hallucinated_output)):

        record = await service.verify_claim(
            claim_id="claim_port",
            claim_text="System uses port 80.",
            candidate_chunks=[(chunk, doc)],
        )

        # Engine must NOT store the fake hallucinated chunk ID
        assert record.document_chunk_id != fake_chunk_id
        assert record.supporting_document_id is None


# =============================================================================
# 3. SECTION-BY-SECTION ANALYSIS & RETRIEVAL SYSTEM INTEGRATION (Req 2 & 3)
# =============================================================================

@pytest.mark.asyncio
async def test_section_by_section_verification_and_db_persistence():
    """
    Validates Requirement 2, 3, 9:
    - Analyzes section by section.
    - Retrieves document chunks from retrieval system when unevidenced.
    - Saves ClaimVerification and EvidenceReference in database.
    """
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    project_id = uuid.uuid4()
    handover_id = uuid.uuid4()
    section_id = uuid.uuid4()

    handover = Handover(id=handover_id, project_id=project_id, title="Test Handover")
    section = HandoverSection(
        id=section_id,
        handover_id=handover_id,
        section_type="technical_architecture",
        title="2. Technical Architecture",
        content={
            "summary": "Architecture overview.",
            "claims": [
                {
                    "claim_id": "arch_claim_1",
                    "statement": "FastAPI backend with PostgreSQL 16.",
                    "source_chunk_ids": [],
                },
                {
                    "claim_id": "arch_claim_2",
                    "statement": "Redis used for session store.",
                    "source_chunk_ids": [],
                },
            ],
        },
    )

    doc = Document(id=uuid.uuid4(), original_filename="arch_doc.md")
    chunk1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        content="FastAPI backend framework connects to PostgreSQL 16 database.",
        page_number=1,
    )
    chunk2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        content="Redis cluster provides in-memory session store.",
        page_number=2,
    )

    # Mock DB query for section + handover
    exec_res = MagicMock()
    exec_res.first.return_value = (section, handover)
    mock_db.execute.return_value = exec_res

    # Mock document retrieval system query (_retrieve_relevant_chunks_for_claim)
    with patch.object(service, "_retrieve_relevant_chunks_for_claim") as mock_retrieve, \
         patch.object(Settings, "is_gemini_configured", return_value=False):

        mock_retrieve.side_effect = [
            [(chunk1, doc)],
            [(chunk2, doc)],
        ]

        report = await service.verify_section(section_id=section_id, handover_id=handover_id)

        assert report.section_id == section_id
        assert report.total_claims == 2
        assert report.supported_claims == 2
        assert report.section_support_rate == 1.0
        assert len(report.claims) == 2

        # Verify that mock_db.add was called to persist ClaimVerification records
        assert mock_db.add.call_count >= 2
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_end_to_end_handover_verification_report():
    """Validates full handover audit generating AdvancedHandoverVerificationReport."""
    mock_db = AsyncMock()
    service = EvidenceVerificationService(mock_db)

    handover_id = uuid.uuid4()
    sec1_id = uuid.uuid4()
    sec2_id = uuid.uuid4()

    sec1 = HandoverSection(
        id=sec1_id,
        handover_id=handover_id,
        section_type="project_overview",
        title="1. Overview",
        sort_order=0,
        content={"claims": [{"claim_id": "c1", "statement": "Overview claim", "source_chunk_ids": []}]},
    )
    sec2 = HandoverSection(
        id=sec2_id,
        handover_id=handover_id,
        section_type="known_issues",
        title="6. Known Issues",
        sort_order=1,
        content={"claims": [{"claim_id": "c2", "statement": "Issue claim", "source_chunk_ids": []}]},
    )

    handover = Handover(id=handover_id, project_id=uuid.uuid4(), title="Full Handover")
    handover.sections = [sec1, sec2]

    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = handover
    mock_db.execute.return_value = exec_res

    with patch.object(service, "verify_section") as mock_v_sec:
        mock_v_sec.side_effect = [
            SectionVerificationReport(
                section_id=sec1_id,
                section_type="project_overview",
                section_title="1. Overview",
                total_claims=1,
                supported_claims=1,
                partially_supported_claims=0,
                unsupported_claims=0,
                conflicting_claims=0,
                insufficient_evidence_claims=0,
                section_support_rate=1.0,
                claims=[
                    ClaimVerificationRecord(
                        claim_id="c1",
                        claim_text="Overview claim",
                        verification_status="Supported",
                        verification_timestamp=datetime.now(timezone.utc),
                    )
                ],
            ),
            SectionVerificationReport(
                section_id=sec2_id,
                section_type="known_issues",
                section_title="6. Known Issues",
                total_claims=1,
                supported_claims=0,
                partially_supported_claims=0,
                unsupported_claims=1,
                conflicting_claims=0,
                insufficient_evidence_claims=0,
                section_support_rate=0.0,
                claims=[
                    ClaimVerificationRecord(
                        claim_id="c2",
                        claim_text="Issue claim",
                        verification_status="Unsupported",
                        verification_timestamp=datetime.now(timezone.utc),
                    )
                ],
            ),
        ]

        report = await service.verify_handover(handover_id)

        assert report.handover_id == handover_id
        assert report.total_claims == 2
        assert report.supported_claims == 1
        assert report.unsupported_claims == 1
        assert report.overall_support_rate == 0.50
        assert len(report.sections) == 2
        assert len(report.claims) == 2


# =============================================================================
# 4. API ENDPOINT VERIFICATION TESTS (Requirement 10)
# =============================================================================

@pytest.mark.asyncio
async def test_get_handover_verification_results_endpoint(async_client):
    """Validates the GET /api/v1/evidence/handovers/{handover_id}/verification-results endpoint."""
    from app.main import app
    from app.dependencies.authorization import require_handover_access
    from app.dependencies.auth import get_current_user

    handover_id = uuid.uuid4()
    mock_user = User(id=uuid.uuid4(), email="dev@example.com", full_name="Test Dev")
    mock_handover = Handover(id=handover_id, project_id=uuid.uuid4(), title="Test Handover")

    mock_report = AdvancedHandoverVerificationReport(
        handover_id=handover_id,
        total_claims=5,
        supported_claims=4,
        partially_supported_claims=1,
        unsupported_claims=0,
        conflicting_claims=0,
        insufficient_evidence_claims=0,
        overall_support_rate=1.0,
        verification_timestamp=datetime.now(timezone.utc).isoformat(),
        sections=[],
        claims=[
            ClaimVerificationRecord(
                claim_id="c_test_1",
                claim_text="API uses FastAPI",
                verification_status="Supported",
                supporting_document_id=uuid.uuid4(),
                source_filename="readme.md",
                page_number=1,
                section_reference="Backend",
                supporting_text_excerpt="FastAPI backend",
                verification_timestamp=datetime.now(timezone.utc),
            )
        ],
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_handover_access] = lambda: mock_handover

    try:
        with patch.object(EvidenceVerificationService, "get_handover_verification_results", return_value=mock_report):
            response = await async_client.get(f"/api/v1/evidence/handovers/{handover_id}/verification-results")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total_claims"] == 5
            assert data["data"]["supported_claims"] == 4
            assert len(data["data"]["claims"]) == 1
            claim_data = data["data"]["claims"][0]
            assert claim_data["claim_id"] == "c_test_1"
            assert claim_data["verification_status"] == "Supported"
            assert claim_data["source_filename"] == "readme.md"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_claim_verification_endpoint(async_client):
    """Validates the GET /api/v1/evidence/claims/{claim_id} endpoint."""
    from app.main import app
    from app.dependencies.auth import get_current_user

    claim_id = "claim_database_99"
    mock_user = User(id=uuid.uuid4(), email="dev@example.com", full_name="Test Dev")
    mock_record = ClaimVerificationRecord(
        claim_id=claim_id,
        claim_text="PostgreSQL 16 cluster runs on port 5432.",
        verification_status="Supported",
        supporting_document_id=uuid.uuid4(),
        source_filename="db_config.md",
        page_number=2,
        section_reference="Database",
        supporting_text_excerpt="PostgreSQL 16 cluster runs on port 5432.",
        verification_timestamp=datetime.now(timezone.utc),
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        with patch.object(EvidenceVerificationService, "get_claim_verification", return_value=mock_record):
            response = await async_client.get(f"/api/v1/evidence/claims/{claim_id}")
            assert response.status_code == 200
            json_data = response.json()
            assert json_data["success"] is True
            assert json_data["data"]["claim_id"] == claim_id
            assert json_data["data"]["verification_status"] == "Supported"
            assert json_data["data"]["source_filename"] == "db_config.md"
    finally:
        app.dependency_overrides.clear()
