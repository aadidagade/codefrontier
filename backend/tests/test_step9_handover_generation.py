"""
Unit and integration tests for Step 9: AI-Powered Knowledge Handover Generation.

Tests:
1. Synthesis of all 10 required handover sections in order.
2. Factual claim attribution (claim_id, source_doc_ids, source_chunk_ids, page_numbers, evidence_status).
3. Explicit separation of recommendations from documented facts.
4. Marking unsupported/missing information as UNKNOWN or NEEDS_REVIEW.
5. Saving generated handovers strictly as DRAFT.
6. Single-section regeneration without regenerating the rest of the handover.
7. Pydantic schema validation for AI generation output.
"""

import json
import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from app.services.rag_service import RAGService, HANDOVER_SECTIONS_SPEC
from app.models.document import Document, DocumentChunk
from app.models.handover import Handover, HandoverSection
from app.schemas.handover import (
    GenerationRequest,
    HandoverAIGenerationOutput,
    GeneratedSection,
    SectionContent,
    FactualClaim,
    Recommendation,
    EvidenceStatus,
)


def test_handover_sections_spec_has_10_sections():
    """Validates that exactly 10 required sections are specified in HANDOVER_SECTIONS_SPEC."""
    assert len(HANDOVER_SECTIONS_SPEC) == 10
    expected_types = [
        "project_overview",
        "technical_architecture",
        "setup_and_installation",
        "important_decisions",
        "pending_tasks",
        "known_issues",
        "risks_and_blockers",
        "deployment_and_maintenance",
        "open_questions",
        "recommended_next_actions",
    ]
    actual_types = [s["type"] for s in HANDOVER_SECTIONS_SPEC]
    assert actual_types == expected_types


def test_pydantic_schema_validation_success():
    """Validates that HandoverAIGenerationOutput enforces strict typing on claims and recommendations."""
    payload = {
        "title": "Alpha Handover",
        "sections": [
            {
                "section_type": "project_overview",
                "title": "1. Project Overview",
                "confidence": 0.95,
                "content": {
                    "summary": "Project summary",
                    "markdown": "# 1. Project Overview\n\nContent",
                    "structured_data": {"purpose": "Cloud migration"},
                    "claims": [
                        {
                            "claim_id": "claim_1",
                            "statement": "FastAPI backend handles high throughput API traffic.",
                            "source_document_ids": [str(uuid.uuid4())],
                            "source_chunk_ids": [str(uuid.uuid4())],
                            "page_numbers": [1],
                            "quoted_text": "FastAPI backend handles high throughput",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": [
                        {
                            "recommendation_id": "rec_1",
                            "title": "Migrate to Kubernetes",
                            "description": "Recommended for scalability",
                            "timeframe": "short_term",
                            "is_recommendation": True,
                        }
                    ],
                },
            }
        ],
        "conflicts": [],
        "tasks": [
            {"title": "Verify local setup", "description": "Run tests", "priority": "high"}
        ],
    }

    output = HandoverAIGenerationOutput.model_validate(payload)
    assert output.title == "Alpha Handover"
    assert len(output.sections) == 1
    assert output.sections[0].content.claims[0].evidence_status == EvidenceStatus.SUPPORTED
    assert output.sections[0].content.recommendations[0].is_recommendation is True


@pytest.mark.asyncio
async def test_synthesize_all_10_sections_saved_as_draft():
    """Validates that all 10 required sections are generated and saved strictly as DRAFT."""
    mock_db = AsyncMock()
    service = RAGService(db=mock_db)

    project_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    doc = Document(id=doc_id, original_filename="architecture.md")
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        project_id=project_id,
        chunk_index=0,
        content="PostgreSQL 16 with pgvector on port 5432.",
        page_number=1,
    )

    # Mock Gemini returning valid 10 sections
    mock_sections = []
    for spec in HANDOVER_SECTIONS_SPEC:
        mock_sections.append(
            {
                "section_type": spec["type"],
                "title": spec["title"],
                "confidence": 0.95,
                "content": {
                    "summary": f"Summary for {spec['title']}",
                    "markdown": f"# {spec['title']}\n\nDocumentation text.",
                    "structured_data": {},
                    "claims": [
                        {
                            "claim_id": f"claim_{spec['type']}",
                            "statement": f"Verified fact for {spec['type']}",
                            "source_document_ids": [str(doc_id)],
                            "source_chunk_ids": [str(chunk_id)],
                            "page_numbers": [1],
                            "quoted_text": "PostgreSQL 16 with pgvector",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": [
                        {
                            "recommendation_id": f"rec_{spec['type']}",
                            "title": f"Recommendation for {spec['type']}",
                            "description": "Suggested action",
                            "timeframe": "immediate",
                            "is_recommendation": True,
                        }
                    ],
                },
            }
        )

    mock_gemini_output = {
        "title": "Complete 10-Chapter Handover",
        "sections": mock_sections,
        "conflicts": [],
        "tasks": [{"title": "Setup local environment", "priority": "high"}],
    }

    with patch.object(service, "_retrieve_category_targeted_evidence", return_value=("Corpus", {str(chunk_id): (chunk, doc)})), \
         patch("app.services.rag_service.gemini_service.generate_content", return_value=json.dumps(mock_gemini_output)):

        req = GenerationRequest(projectId=project_id, title="Complete 10-Chapter Handover")
        handover = await service.synthesize_handover(req, user_id=uuid.uuid4())

        # STRICT ASSERTION: Handover MUST be saved as DRAFT
        assert handover.status == "draft"
        assert handover.title == "Complete 10-Chapter Handover"
        assert handover.project_id == project_id

        # Verify DB calls
        assert mock_db.add.called
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_missing_section_automatically_marked_unknown():
    """Validates that if Gemini misses a section, it is safely inserted and marked UNKNOWN/UNSUPPORTED."""
    mock_db = AsyncMock()
    service = RAGService(db=mock_db)

    project_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    doc = Document(id=doc_id, original_filename="arch.md")
    chunk = DocumentChunk(id=chunk_id, document_id=doc_id, project_id=project_id, chunk_index=0, content="Content")

    # Gemini only returns 1 section instead of 10
    partial_output = {
        "title": "Partial Handover",
        "sections": [
            {
                "section_type": "project_overview",
                "title": "1. Project Overview",
                "confidence": 0.95,
                "content": {
                    "summary": "Overview",
                    "markdown": "# Overview",
                    "structured_data": {},
                    "claims": [],
                    "recommendations": [],
                },
            }
        ],
        "conflicts": [],
        "tasks": [],
    }

    added_sections = []
    def capture_add(item):
        if isinstance(item, HandoverSection):
            added_sections.append(item)
    mock_db.add.side_effect = capture_add

    with patch.object(service, "_retrieve_category_targeted_evidence", return_value=("Corpus", {str(chunk_id): (chunk, doc)})), \
         patch("app.services.rag_service.gemini_service.generate_content", return_value=json.dumps(partial_output)):

        req = GenerationRequest(projectId=project_id)
        await service.synthesize_handover(req, user_id=uuid.uuid4())

        # All 10 sections must be added to DB
        assert len(added_sections) == 10
        # The 9 missing sections must have UNKNOWN in content
        missing_sec = [s for s in added_sections if s.section_type == "technical_architecture"][0]
        assert "UNKNOWN" in missing_sec.content["markdown"]
        assert missing_sec.content["claims"][0]["evidence_status"] == "UNSUPPORTED"


@pytest.mark.asyncio
async def test_regenerate_single_section():
    """Validates that a single section can be regenerated without touching other sections."""
    mock_db = AsyncMock()
    service = RAGService(db=mock_db)

    handover_id = uuid.uuid4()
    section_id = uuid.uuid4()
    project_id = uuid.uuid4()

    mock_handover = Handover(id=handover_id, project_id=project_id, status="draft")
    mock_section = HandoverSection(
        id=section_id,
        handover_id=handover_id,
        section_type="technical_architecture",
        title="2. Technical Architecture",
        content={"summary": "Old summary", "markdown": "Old markdown"},
        confidence=0.8,
    )

    mock_db.execute.return_value.first.return_value = (mock_section, mock_handover)
    mock_db.execute.return_value.scalars.return_value.first.return_value = mock_section

    mock_regen_output = {
        "section_type": "technical_architecture",
        "title": "2. Technical Architecture",
        "confidence": 0.98,
        "content": {
            "summary": "Regenerated architecture summary",
            "markdown": "# 2. Technical Architecture\n\nFresh architecture content.",
            "structured_data": {"stack": ["FastAPI", "PostgreSQL", "pgvector"]},
            "claims": [
                {
                    "claim_id": "claim_regen_1",
                    "statement": "FastAPI is the ASGI web framework.",
                    "source_document_ids": [],
                    "source_chunk_ids": [],
                    "page_numbers": [],
                    "evidence_status": "SUPPORTED",
                }
            ],
            "recommendations": [],
        },
    }

    with patch.object(service, "retrieve_evidence", return_value=[]), \
         patch("app.services.rag_service.gemini_service.generate_content", return_value=json.dumps(mock_regen_output)):

        updated_sec = await service.regenerate_section(
            handover_id=handover_id,
            section_id=section_id,
            instructions="Focus on the database stack",
            user_id=uuid.uuid4(),
        )

        assert updated_sec.title == "2. Technical Architecture"
        assert updated_sec.confidence == 0.98
        assert updated_sec.content["summary"] == "Regenerated architecture summary"
        assert mock_db.commit.called
