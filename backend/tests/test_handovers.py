"""
Unit and integration tests for Step 8: RAG Synthesis, Evidence Linking, and Handover Lifecycle.
"""

import json
import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from app.services.rag_service import RAGService
from app.models.document import Document, DocumentChunk
from app.models.handover import Handover, HandoverSection
from app.models.project import ProjectMemberRole
from app.schemas.handover import GenerationRequest
from app.core.exceptions import ValidationException, AiServiceException


def test_clean_json_response_clean():
    valid = {"title": "Test Title", "sections": []}
    res = RAGService._clean_json_response(json.dumps(valid))
    assert res["title"] == "Test Title"


def test_clean_json_response_markdown_fences():
    valid = {"title": "Fenced Title", "sections": []}
    fenced = f"```json\n{json.dumps(valid)}\n```"
    res = RAGService._clean_json_response(fenced)
    assert res["title"] == "Fenced Title"


def test_clean_json_response_with_surrounding_prose():
    valid = {"title": "Embedded Title", "sections": []}
    prose = f"Here is the generated handover package:\n```\n{json.dumps(valid)}\n```\nHope this helps!"
    res = RAGService._clean_json_response(prose)
    assert res["title"] == "Embedded Title"


def test_build_rag_prompt():
    service = RAGService(db=MagicMock())
    doc = Document(id=uuid.uuid4(), original_filename="architecture.pdf")
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        project_id=uuid.uuid4(),
        chunk_index=0,
        content="Microservices communicate via gRPC on port 50051.",
        page_number=3,
        section_title="Communication Protocols",
    )

    req = GenerationRequest(
        projectId=chunk.project_id,
        targetRole="Incoming Tech Lead",
        handoverScope="Architecture & Operational",
        timelineScope="All Time",
        additionalInstructions="Focus on latency bottlenecks",
    )

    prompt = service._build_rag_prompt([(chunk, doc)], req)
    assert str(chunk.id) in prompt
    assert "architecture.pdf" in prompt
    assert "Microservices communicate via gRPC" in prompt
    assert "Incoming Tech Lead" in prompt
    assert "Focus on latency bottlenecks" in prompt


@pytest.mark.asyncio
async def test_synthesize_handover_success():
    mock_db = AsyncMock()
    service = RAGService(db=mock_db)

    project_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    doc = Document(id=doc_id, original_filename="system_design.md")
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        project_id=project_id,
        chunk_index=0,
        content="Primary database is PostgreSQL 16 with pgvector extension.",
        page_number=1,
    )

    # Mock fetch chunks
    with patch.object(service, "_fetch_project_chunks", return_value=[(chunk, doc)]):
        mock_output = {
            "title": "Platform Knowledge Handover",
            "sections": [
                {
                    "section_type": "overview",
                    "title": "System Architecture Overview",
                    "confidence": 0.98,
                    "content": {
                        "markdown": "System relies on PostgreSQL and FastAPI.",
                        "summary": "Core platform design.",
                    },
                    "citations": [
                        {
                            "chunk_id": str(chunk_id),
                            "quoted_text": "Primary database is PostgreSQL 16 with pgvector extension.",
                            "relevance_score": 0.98,
                        }
                    ],
                },
                {
                    "section_type": "key_decisions",
                    "title": "Key Decisions",
                    "confidence": 0.95,
                    "content": {"markdown": "Adopted asyncpg for asynchronous database IO."},
                    "citations": [],
                },
            ],
            "conflicts": [
                {
                    "conflict_type": "architecture",
                    "description": "Port mismatch between deployment scripts and docs.",
                    "source_a_chunk_id": str(chunk_id),
                    "source_a_quote": "Port 50051",
                    "source_b_chunk_id": str(chunk_id),
                    "source_b_quote": "Port 8080",
                }
            ],
            "tasks": [
                {
                    "title": "Verify local pgvector connection",
                    "description": "Run verify_db.py script",
                    "priority": "high",
                }
            ],
        }

        with patch("app.services.rag_service.gemini_service.generate_content", return_value=json.dumps(mock_output)):
            req = GenerationRequest(projectId=project_id, title="Platform Knowledge Handover")
            handover = await service.synthesize_handover(req, user_id=uuid.uuid4())

            assert handover.title == "Platform Knowledge Handover"
            assert handover.status == "draft"
            assert handover.project_id == project_id
            # Verify DB operations called
            assert mock_db.add.called
            assert mock_db.commit.called


@pytest.mark.asyncio
async def test_synthesize_handover_no_chunks_raises_validation():
    mock_db = AsyncMock()
    service = RAGService(db=mock_db)

    with patch.object(service, "_fetch_project_chunks", return_value=[]):
        req = GenerationRequest(projectId=uuid.uuid4())
        with pytest.raises(ValidationException) as exc_info:
            await service.synthesize_handover(req, user_id=uuid.uuid4())
        assert "No processed documents" in str(exc_info.value)
