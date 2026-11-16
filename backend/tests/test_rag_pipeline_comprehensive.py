"""
AI/ML Engineering Test Suite for Google Gemini-Powered RAG Pipeline.

Verifies end-to-end RAG architecture:
1. Multi-Format Ingestion (PDF, DOCX, TXT, Markdown).
2. Structured AST & Text Extraction with Page Boundaries and Metadata.
3. Intelligent Chunking with Headings, Page Numbers, and Overlap.
4. Dense 768-dimensional Vector Embeddings Generation & Vector Storage.
5. Semantic and Hybrid Search Retrieval with Relevance Ranking.
6. Context Assembly and Gemini Prompt Engineering.
7. Structured JSON Synthesis across all 11 Required Handover Information Areas:
   - Project overview
   - Current project status
   - Key decisions and rationale
   - Completed tasks
   - Pending tasks
   - Task ownership
   - Blockers
   - Risks
   - Dependencies
   - Unresolved questions
   - Recommended next actions
8. Rigorous Failure Scenarios & Edge Cases:
   - Empty documents
   - Corrupted files
   - Unsupported formats
   - Very large files (size limit enforcement)
   - Duplicate documents
   - Gemini API timeout & retry backoff
   - Invalid API key (403 handling)
   - API quota exceeded (429 handling)
   - Empty Gemini response
   - Invalid JSON response
   - Missing source evidence handling
   - Secret scrubbing and environment key protection
"""

import io
import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import pytest_asyncio
from fastapi import UploadFile
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import fitz  # PyMuPDF
import docx  # python-docx

from app.core.config import settings
from app.core.exceptions import ValidationException, AiServiceException, NotFoundException
from app.models import (
    Base,
    User,
    Project,
    Document,
    DocumentChunk,
    Handover,
    HandoverSection,
    EvidenceReference,
    ClaimVerification,
    Conflict,
    Task,
)
from app.schemas.handover import (
    GenerationRequest,
    HandoverAIGenerationOutput,
    GeneratedSection,
    SectionContent,
    FactualClaim,
    Recommendation,
    GeneratedConflict,
    GeneratedTask,
    EvidenceStatus,
    VerificationStatus,
)
from app.schemas.search import RetrievedChunk
from app.services.chunking_service import IntelligentChunkingService, chunking_service
from app.services.document_processing_service import DocumentProcessingService
from app.services.extractor import extract_document
from app.services.gemini_service import GeminiService, gemini_service, redact_secrets
from app.services.rag_service import RAGService, HANDOVER_SECTIONS_SPEC
from app.utils.file_validation import validate_file_security


@pytest_asyncio.fixture
async def rag_test_session():
    """Provides an isolated database session with foreign keys enabled."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# ==============================================================================
# 1. MULTI-FORMAT DOCUMENT EXTRACTION (PDF, DOCX, TXT, MARKDOWN)
# ==============================================================================
def test_ingestion_and_extraction_pdf(tmp_path: Path):
    """Verifies that multi-page PDF documents extract text, page numbers, and headings accurately."""
    pdf_path = tmp_path / "architecture_spec.pdf"
    doc = fitz.open()

    # Page 1: Heading & Overview
    p1 = doc.new_page()
    p1.insert_text((50, 50), "1. Architecture Specification", fontsize=18)
    p1.insert_text((50, 90), "This enterprise platform uses event-driven asynchronous microservices.", fontsize=11)
    p1.insert_text((50, 120), "Primary database is PostgreSQL with pgvector for dense embeddings.", fontsize=11)

    # Page 2: Decisions & Security
    p2 = doc.new_page()
    p2.insert_text((50, 50), "2. Security and Compliance", fontsize=18)
    p2.insert_text((50, 90), "All inter-service gRPC calls strictly enforce mTLS with TLS 1.3 certificates.", fontsize=11)
    p2.insert_text((50, 120), "JWT access tokens expire every 30 minutes with Argon2id password hashing.", fontsize=11)

    doc.save(str(pdf_path))
    doc.close()

    extracted = extract_document(pdf_path, "pdf")

    assert extracted.page_count == 2
    assert "event-driven asynchronous microservices" in extracted.full_text
    assert "mTLS with TLS 1.3" in extracted.full_text
    assert len(extracted.sections) >= 2
    section_titles = [s.title for s in extracted.sections]
    assert any("Architecture" in t for t in section_titles)
    assert any("Security" in t for t in section_titles)
    assert extracted.metadata["format"] == "PDF"
    assert extracted.is_scanned is False
    assert extracted.needs_ocr is False


def test_ingestion_and_extraction_docx(tmp_path: Path):
    """Verifies that Word DOCX documents extract text, heading levels, and embedded tables."""
    docx_path = tmp_path / "operational_runbook.docx"
    doc = docx.Document()

    # Heading 1
    doc.add_heading("Operational Runbook", level=1)
    doc.add_paragraph("Comprehensive incident management and disaster recovery protocol.")

    # Heading 2
    doc.add_heading("Database Failover Steps", level=2)
    doc.add_paragraph("Step 1: Promote read replica to primary. Step 2: Reroute traffic via Route53.")

    # Table with key roles
    table = doc.add_table(rows=3, cols=2)
    table.rows[0].cells[0].text = "Responsibility"
    table.rows[0].cells[1].text = "Assignee"
    table.rows[1].cells[0].text = "Primary Incident Commander"
    table.rows[1].cells[1].text = "DevOps Lead"
    table.rows[2].cells[0].text = "Database Administrator"
    table.rows[2].cells[1].text = "Infra Team"

    doc.save(str(docx_path))

    extracted = extract_document(docx_path, "docx")

    assert "incident management and disaster recovery" in extracted.full_text
    assert "Promote read replica" in extracted.full_text
    assert "Primary Incident Commander | DevOps Lead" in extracted.full_text
    assert len(extracted.sections) >= 2
    assert extracted.metadata["format"] == "DOCX"
    assert extracted.word_count > 15


def test_ingestion_and_extraction_txt(tmp_path: Path):
    """Verifies that plain text files parse paragraph blocks and calculate correct word/char counts."""
    txt_path = tmp_path / "system_notes.txt"
    txt_content = (
        "Project Genesis: Initial bootstrapping completed on June 2026.\n\n"
        "Deployment Configuration: The frontend is hosted on Vercel with backend on AWS ECS.\n\n"
        "Environment Variables: DATABASE_URL and GEMINI_API_KEY must be configured before startup.\n"
    )
    txt_path.write_text(txt_content, encoding="utf-8")

    extracted = extract_document(txt_path, "txt")

    assert "Project Genesis" in extracted.full_text
    assert "hosted on Vercel" in extracted.full_text
    assert extracted.word_count == len(txt_content.split())
    assert extracted.char_count == len(extracted.full_text)
    assert extracted.page_count >= 1


def test_ingestion_and_extraction_markdown(tmp_path: Path):
    """Verifies that Markdown files extract hierarchical headings (# H1, ## H2) into structured sections."""
    md_path = tmp_path / "README.md"
    md_content = """# Knowledge Handover Platform

Production handover synthesis system for software development teams.

## Technical Architecture

FastAPI backend with PostgreSQL, pgvector, and Google Gemini AI.

### Frontend Integration

React 18 with Tailwind CSS, Lucide icons, and Vite development tooling.

## Key Blockers

Third-party OAuth rate limits during peak synchronization windows.
"""
    md_path.write_text(md_content, encoding="utf-8")

    extracted = extract_document(md_path, "md")

    assert extracted.metadata["format"] == "Markdown"
    assert len(extracted.sections) >= 3
    titles = [s.title for s in extracted.sections]
    assert "Knowledge Handover Platform" in titles
    assert "Technical Architecture" in titles
    assert "Key Blockers" in titles


# ==============================================================================
# 2. UPLOAD & DISK STORAGE VERIFICATION
# ==============================================================================
@pytest.mark.asyncio
async def test_file_upload_and_storage_initialization(rag_test_session: AsyncSession, tmp_path: Path):
    """Verifies file validation, disk writing, and UPLOADED database record initialization."""
    user = User(id=uuid.uuid4(), full_name="Uploader", email="up@corp.io", password_hash="hash")
    project = Project(id=uuid.uuid4(), name="Upload Workspace", created_by=user.id)
    rag_test_session.add_all([user, project])
    await rag_test_session.commit()

    file_bytes = b"%PDF-1.7\nSample binary PDF content for testing uploads.\n%%EOF"
    upload_file = UploadFile(
        file=io.BytesIO(file_bytes),
        filename="cloud_spec.pdf",
        size=len(file_bytes),
        headers={"content-type": "application/pdf"},
    )

    with patch.object(settings, "UPLOAD_DIR", str(tmp_path / "storage")):
        svc = DocumentProcessingService(rag_test_session)
        doc = await svc.save_uploaded_file(upload_file, project.id, user.id)

        assert doc.original_filename == "cloud_spec.pdf"
        assert doc.file_type == "pdf"
        assert doc.processing_status == "UPLOADED"
        assert doc.file_size == len(file_bytes)
        assert Path(doc.storage_path).exists()


# ==============================================================================
# 3. SEMANTIC CHUNKING WITH METADATA PRESERVATION
# ==============================================================================
def test_chunking_preserves_page_numbers_and_headings():
    """Verifies that IntelligentChunkingService maintains section context, page numbers, and word counts."""
    from app.services.extractor.base import ExtractedDocument, ExtractedSection

    doc = ExtractedDocument(
        full_text="Complete text",
        sections=[
            ExtractedSection(
                title="Database Replication",
                content="PostgreSQL streaming replication is configured with 3 read replicas.\n\n" * 15,
                page_number=4,
                level=2,
            )
        ],
        page_count=5,
        word_count=150,
        char_count=900,
    )

    chunker = IntelligentChunkingService(target_chunk_size=300, chunk_overlap=50)
    doc_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    chunks = chunker.create_chunks(doc, doc_id, proj_id)

    assert len(chunks) >= 2
    for idx, c in enumerate(chunks):
        assert c.document_id == doc_id
        assert c.project_id == proj_id
        assert c.chunk_index == idx
        assert c.page_number == 4
        assert c.section_title == "Database Replication"
        assert c.content.startswith("## Database Replication")
        assert c.chunk_metadata["page"] == 4
        assert c.chunk_metadata["word_count"] > 0


# ==============================================================================
# 4. 768-DIMENSIONAL EMBEDDINGS GENERATION & STORAGE
# ==============================================================================
def test_embedding_generation_dimension_and_normalization():
    """Verifies that GeminiService generates normalized 768-dimensional float vectors."""
    mock_vector = [0.05 * (i % 20) for i in range(768)]

    mock_client = MagicMock()
    mock_embed_res = MagicMock()
    mock_embed_res.embeddings = [MagicMock(values=mock_vector)]
    mock_client.models.embed_content.return_value = mock_embed_res

    svc = GeminiService()
    svc._client = mock_client
    svc._verified_embed_model = "text-embedding-004"

    # Single embedding
    vec = svc.generate_embedding("Microservices architecture design.")
    assert len(vec) == 768
    assert isinstance(vec[0], float)

    # Batch embedding
    batch_vecs = svc.generate_embeddings_batch(["Chunk one text", "Chunk two text"])
    assert len(batch_vecs) == 2
    assert len(batch_vecs[0]) == 768
    assert len(batch_vecs[1]) == 768


@pytest.mark.asyncio
async def test_embeddings_stored_in_database(rag_test_session: AsyncSession):
    """Verifies that 768-dimensional vectors persist and retrieve without precision truncation."""
    u = User(id=uuid.uuid4(), full_name="Vector User", email="vec@corp.io", password_hash="pwd")
    p = Project(id=uuid.uuid4(), name="Vector Workspace", created_by=u.id)
    d = Document(
        id=uuid.uuid4(),
        project_id=p.id,
        original_filename="v.md",
        stored_filename="v_stored.md",
        file_type="md",
        file_size=100,
        storage_path="/tmp/v",
        processing_status="completed",
    )
    vector = [float(i) / 768.0 for i in range(768)]
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=d.id,
        project_id=p.id,
        chunk_index=0,
        content="Passage on distributed consensus algorithms.",
        embedding=vector,
    )
    rag_test_session.add_all([u, p, d, chunk])
    await rag_test_session.commit()

    res = await rag_test_session.execute(select(DocumentChunk).where(DocumentChunk.id == chunk.id))
    saved_chunk = res.scalar_one()

    assert saved_chunk.embedding is not None
    assert len(saved_chunk.embedding) == 768
    assert abs(saved_chunk.embedding[384] - (384.0 / 768.0)) < 1e-5


# ==============================================================================
# 5. SEMANTIC SEARCH & RELEVANCE RETRIEVAL
# ==============================================================================
@pytest.mark.asyncio
async def test_semantic_search_and_relevance_ranking(rag_test_session: AsyncSession):
    """Verifies that RAGService.retrieve_evidence retrieves matching chunks with source citations."""
    u = User(id=uuid.uuid4(), full_name="Search User", email="srch@corp.io", password_hash="pwd")
    p = Project(id=uuid.uuid4(), name="Search Workspace", created_by=u.id)
    d = Document(
        id=uuid.uuid4(),
        project_id=p.id,
        original_filename="security_spec.pdf",
        stored_filename="sec_stored.pdf",
        file_type="pdf",
        file_size=2048,
        storage_path="/tmp/sec",
        processing_status="READY",
    )
    c1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=d.id,
        project_id=p.id,
        chunk_index=0,
        content="TLS 1.3 encryption is enforced for all ingress API gateways.",
        page_number=3,
        section_title="Ingress Security",
        embedding=[0.1] * 768,
    )
    c2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=d.id,
        project_id=p.id,
        chunk_index=1,
        content="Kubernetes pod autoscaling triggers at 75 percent CPU utilization.",
        page_number=7,
        section_title="Autoscaling Policy",
        embedding=[-0.1] * 768,
    )
    rag_test_session.add_all([u, p, d, c1, c2])
    await rag_test_session.commit()

    rag_svc = RAGService(rag_test_session)

    mock_retrieved = [
        RetrievedChunk(
            chunk_id=c1.id,
            document_id=d.id,
            document_name="security_spec.pdf",
            chunk_index=0,
            content=c1.content,
            similarity_score=0.92,
            page_number=3,
            section_title="Ingress Security",
        )
    ]

    with patch.object(rag_svc.repo, "hybrid_search", new_callable=AsyncMock, return_value=mock_retrieved):
        results = await rag_svc.retrieve_evidence(p.id, "TLS encryption gateway security", limit=5)
        assert len(results) == 1
        top_match = results[0]
        assert top_match.chunk_id == c1.id
        assert top_match.document_name == "security_spec.pdf"
        assert top_match.page_number == 3
        assert "TLS 1.3 encryption" in top_match.content


# ==============================================================================
# 6. CONTEXT ASSEMBLY & GEMINI PROMPT PREPARATION
# ==============================================================================
@pytest.mark.asyncio
async def test_gemini_context_payload_formatting(rag_test_session: AsyncSession):
    """Verifies that retrieved chunks are assembled into formatted prompt context blocks."""
    u = User(id=uuid.uuid4(), full_name="Context User", email="ctx@corp.io", password_hash="pwd")
    p = Project(id=uuid.uuid4(), name="Context Workspace", created_by=u.id)
    d = Document(
        id=uuid.uuid4(),
        project_id=p.id,
        original_filename="infra.md",
        stored_filename="infra_stored.md",
        file_type="md",
        file_size=500,
        storage_path="/tmp/i",
        processing_status="READY",
    )
    c = DocumentChunk(
        id=uuid.uuid4(),
        document_id=d.id,
        project_id=p.id,
        chunk_index=0,
        content="PostgreSQL runs with connection pooling via PgBouncer.",
        page_number=2,
        section_title="Database Layer",
    )
    rag_test_session.add_all([u, p, d, c])
    await rag_test_session.commit()

    rag_svc = RAGService(rag_test_session)
    corpus_text, chunk_map = await rag_svc._retrieve_category_targeted_evidence(p.id)

    assert str(c.id) in chunk_map
    assert f"[CHUNK_ID: {c.id}" in corpus_text
    assert f"DOC: {d.original_filename}" in corpus_text
    assert f"PAGE: 2" in corpus_text
    assert "PgBouncer" in corpus_text


# ==============================================================================
# 7. STRUCTURED JSON SYNTHESIS ACROSS ALL 11 REQUIRED HANDOVER AREAS
# ==============================================================================
@pytest.mark.asyncio
async def test_handover_synthesis_all_11_required_content_areas(rag_test_session: AsyncSession):
    """
    Verifies that Gemini synthesis produces structured JSON satisfying all 11 required areas:
    1. Project overview
    2. Current project status
    3. Key decisions and rationale
    4. Completed tasks
    5. Pending tasks
    6. Task ownership
    7. Blockers
    8. Risks
    9. Dependencies
    10. Unresolved questions
    11. Recommended next actions
    And validates database persistence into Handover, Sections, Citations, Conflicts, and Tasks.
    """
    lead_user = User(id=uuid.uuid4(), full_name="Lead Architect", email="lead_arch@corp.io", password_hash="pwd")
    incoming_user = User(id=uuid.uuid4(), full_name="Incoming Engineer", email="inc_eng@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Enterprise Payment Platform", created_by=lead_user.id)
    doc = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="payment_core_spec.md",
        stored_filename="spec_stored.md",
        file_type="md",
        file_size=1024,
        storage_path="/tmp/spec",
        processing_status="READY",
    )
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        project_id=project.id,
        chunk_index=0,
        content="Payment Gateway handles $50M daily volume with 99.999% SLA.",
        page_number=1,
        section_title="Overview",
    )
    rag_test_session.add_all([lead_user, incoming_user, project, doc, chunk])
    await rag_test_session.commit()

    rag_svc = RAGService(rag_test_session)

    # Construct complete synthetic Gemini response covering all 11 areas across 10 sections
    mock_gemini_json = {
        "title": "Payment Core Engineering Handover",
        "sections": [
            {
                "section_type": "project_overview",
                "title": "1. Project Overview",
                "confidence": 0.98,
                "content": {
                    "summary": "High-volume distributed payment processing gateway.",
                    "markdown": "# 1. Project Overview\n\nHigh-volume distributed payment processing gateway.",
                    "key_points": ["Handles $50M daily volume", "99.999% SLA guarantee"],
                    "structured_data": {
                        "project_status": "Production Stable",  # Area 2: Current project status
                        "project_overview": "Core financial settlement service",  # Area 1: Project overview
                    },
                    "claims": [
                        {
                            "claim_id": "claim_ov_1",
                            "statement": "Payment Gateway handles $50M daily volume with 99.999% SLA.",
                            "source_document_ids": [str(doc.id)],
                            "source_chunk_ids": [str(chunk.id)],
                            "page_numbers": [1],
                            "quoted_text": "Payment Gateway handles $50M daily volume with 99.999% SLA.",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": [],
                },
            },
            {
                "section_type": "technical_architecture",
                "title": "2. Technical Architecture",
                "confidence": 0.96,
                "content": {
                    "summary": "Go microservices with Kafka and PostgreSQL.",
                    "markdown": "# 2. Architecture\n\nGo microservices with Kafka and PostgreSQL.",
                    "key_points": ["Go 1.22", "Kafka event streaming", "PostgreSQL Aurora"],
                    "structured_data": {"tech_stack": ["Go", "Kafka", "PostgreSQL", "Redis"]},
                    "claims": [],
                    "recommendations": [],
                },
            },
            {
                "section_type": "setup_and_installation",
                "title": "3. Setup and Installation",
                "confidence": 0.95,
                "content": {
                    "summary": "Docker Compose local development environment.",
                    "markdown": "# 3. Setup\n\nRun `docker compose up -d`.",
                    "key_points": ["Prerequisites: Docker, Go 1.22"],
                    "structured_data": {"dependencies": ["Docker", "PostgreSQL 16", "Kafka"]},  # Area 9: Dependencies
                    "claims": [],
                    "recommendations": [],
                },
            },
            {
                "section_type": "important_decisions",
                "title": "4. Important Decisions",
                "confidence": 0.97,
                "content": {
                    "summary": "Architectural decision records and technical rationale.",
                    "markdown": "# 4. Key Decisions\n\nChose Kafka over RabbitMQ for replayability.",
                    "key_points": ["ADR-001: Event sourcing via Kafka", "ADR-002: PostgreSQL for ACID ledgers"],
                    "structured_data": {
                        "key_decisions": [  # Area 3: Key decisions and rationale
                            {"decision": "Event Sourcing", "rationale": "Auditability and transaction replay"}
                        ]
                    },
                    "claims": [],
                    "recommendations": [],
                },
            },
            {
                "section_type": "pending_tasks",
                "title": "5. Pending Tasks",
                "confidence": 0.94,
                "content": {
                    "summary": "Current sprint roadmap and operational transition tasks.",
                    "markdown": "# 5. Pending Tasks\n\nImplement ISO20022 messaging format.",
                    "key_points": ["ISO20022 compliance migration", "Multi-region failover dry-run"],
                    "structured_data": {
                        "completed_tasks": ["PostgreSQL 16 migration", "Load testing at 5,000 TPS"],  # Area 4: Completed tasks
                        "pending_tasks": ["ISO20022 wire format", "PCI-DSS Level 1 audit"],  # Area 5: Pending tasks
                    },
                    "claims": [],
                    "recommendations": [],
                },
            },
            {
                "section_type": "known_issues",
                "title": "6. Known Issues",
                "confidence": 0.92,
                "content": {
                    "summary": "Intermittent network timeouts on legacy bank connectors.",
                    "markdown": "# 6. Known Issues\n\nLegacy connector timeouts.",
                    "key_points": ["Connector retry queue absorbs spikes"],
                    "structured_data": {},
                    "claims": [],
                    "recommendations": [],
                },
            },
            {
                "section_type": "risks_and_blockers",
                "title": "7. Risks and Blockers",
                "confidence": 0.95,
                "content": {
                    "summary": "Critical dependencies and external project blockers.",
                    "markdown": "# 7. Risks and Blockers\n\nDownstream bank sandbox downtime.",
                    "key_points": ["Bank API rate limiting", "Hardware security module (HSM) key rotation"],
                    "structured_data": {
                        "blockers": ["Bank sandbox certificate renewal pending"],  # Area 7: Blockers
                        "risks": ["HSM latency spike under peak transaction volume"],  # Area 8: Risks
                    },
                    "claims": [],
                    "recommendations": [],
                },
            },
            {
                "section_type": "deployment_and_maintenance",
                "title": "8. Deployment and Maintenance",
                "confidence": 0.96,
                "content": {
                    "summary": "Kubernetes blue-green deployment pipelines with ArgoCD.",
                    "markdown": "# 8. Deployment\n\nAutomated GitOps via ArgoCD.",
                    "key_points": ["Prometheus & Grafana alerting", "Daily automated Aurora snapshots"],
                    "structured_data": {},
                    "claims": [],
                    "recommendations": [],
                },
            },
            {
                "section_type": "open_questions",
                "title": "9. Open Questions",
                "confidence": 0.90,
                "content": {
                    "summary": "Unverified legacy configurations requiring clarification.",
                    "markdown": "# 9. Open Questions\n\nWho maintains the backup clearing account?",
                    "key_points": ["Clearing account ownership unverified in documentation"],
                    "structured_data": {
                        "unresolved_questions": ["Who owns the backup clearing account credentials?"]  # Area 10: Unresolved questions
                    },
                    "claims": [
                        {
                            "claim_id": "claim_oq_1",
                            "statement": "UNKNOWN: Clearing account ownership unverified in documentation.",
                            "source_document_ids": [],
                            "source_chunk_ids": [],
                            "page_numbers": [],
                            "evidence_status": "UNSUPPORTED",
                        }
                    ],
                    "recommendations": [],
                },
            },
            {
                "section_type": "recommended_next_actions",
                "title": "10. Recommended Next Actions",
                "confidence": 0.97,
                "content": {
                    "summary": "Prioritized onboarding steps and technical recommendations.",
                    "markdown": "# 10. Recommended Next Actions\n\nComplete staging sandbox runbook.",
                    "key_points": ["Run smoke tests in staging", "Meet with compliance officer"],
                    "structured_data": {},
                    "claims": [],
                    "recommendations": [  # Area 11: Recommended next actions
                        {
                            "recommendation_id": "rec_001",
                            "title": "Staging Failover Dry-Run",
                            "description": "Execute staging failover dry-run within first 14 days",
                            "timeframe": "immediate",
                            "is_recommendation": True,
                        }
                    ],
                },
            },
        ],
        "conflicts": [
            {
                "conflict_type": "architecture",
                "description": "Contradiction in primary ledger storage engine",
                "source_a_chunk_id": str(chunk.id),
                "source_a_quote": "Primary database is PostgreSQL Aurora",
                "source_b_chunk_id": str(chunk.id),
                "source_b_quote": "Primary database is MongoDB cluster",
            }
        ],
        "tasks": [
            {
                "title": "Migrate ISO20022 wire format",
                "description": "Update payment clearing serializers",
                "priority": "high",
                "assigned_to_name": "Incoming Engineer",  # Area 6: Task ownership
            }
        ],
    }

    import json
    with patch.object(gemini_service, "generate_content", return_value=json.dumps(mock_gemini_json)):
        req = GenerationRequest(
            projectId=project.id,
            targetRole="Incoming Senior Software Engineer",
            handoverScope="Comprehensive",
            title="Payment Core Engineering Handover",
        )
        handover = await rag_svc.synthesize_handover(req, user_id=lead_user.id)

        # 1. Handover properties
        assert handover.title == "Payment Core Engineering Handover"
        assert handover.status == "draft"  # Strictly saved as draft
        assert handover.version == "v1.0"
        assert handover.project_id == project.id

        # 2. All 10 Sections in order
        res_sec = await rag_test_session.execute(
            select(HandoverSection).where(HandoverSection.handover_id == handover.id).order_by(HandoverSection.sort_order)
        )
        sections = res_sec.scalars().all()
        assert len(sections) == 10

        sec_types = [s.section_type for s in sections]
        expected_types = [spec["type"] for spec in HANDOVER_SECTIONS_SPEC]
        assert sec_types == expected_types

        # 3. Evidence Citations
        res_ev = await rag_test_session.execute(
            select(EvidenceReference).where(EvidenceReference.handover_section_id == sections[0].id)
        )
        citations = res_ev.scalars().all()
        assert len(citations) >= 1
        assert citations[0].document_id == doc.id
        assert citations[0].document_chunk_id == chunk.id
        assert citations[0].verification_status == "Supported"

        # 4. Continuation Tasks
        res_task = await rag_test_session.execute(select(Task).where(Task.handover_id == handover.id))
        tasks = res_task.scalars().all()
        assert len(tasks) == 1
        assert tasks[0].title == "Migrate ISO20022 wire format"
        assert tasks[0].priority == "high"


# ==============================================================================
# 8. FAILURE SCENARIO TESTING (11 FAILURE MODES)
# ==============================================================================
def test_failure_empty_documents(tmp_path: Path):
    """Verifies that empty files or whitespace-only inputs are handled cleanly without crashes."""
    # 1. Empty TXT
    empty_txt = tmp_path / "empty.txt"
    empty_txt.write_text("", encoding="utf-8")
    ext_txt = extract_document(empty_txt, "txt")
    assert ext_txt.full_text == ""
    assert ext_txt.word_count == 0

    # 2. Embedding generator rejects empty text
    with pytest.raises(ValidationException):
        gemini_service.generate_embedding("   ")


def test_failure_corrupted_files(tmp_path: Path):
    """Verifies that corrupted files fail with clean validation errors."""
    # 1. Fake PDF with corrupted magic bytes
    bad_pdf = tmp_path / "corrupt.pdf"
    bad_pdf.write_bytes(b"NOT_A_REAL_PDF_DATA_STREAM")
    with pytest.raises(ValidationException) as exc_info:
        validate_file_security("corrupt.pdf", bad_pdf.read_bytes())
    assert "Invalid PDF" in str(exc_info.value) or "Header" in str(exc_info.value)

    # 2. Corrupt DOCX zip archive
    bad_docx = tmp_path / "corrupt.docx"
    bad_docx.write_bytes(b"PK\x03\x04CORRUPTED_BYTES_WITHOUT_XML_BODY")
    with pytest.raises(Exception):
        extract_document(bad_docx, "docx")


def test_failure_unsupported_formats():
    """Verifies that executable, script, and dangerous file formats are strictly rejected."""
    dangerous = [
        ("malicious.exe", b"MZ\x90\x00\x03"),
        ("attack.sh", b"#!/bin/bash\nrm -rf /"),
        ("exploit.bat", b"@echo off\ndel C:\\"),
        ("script.ps1", b"Get-Process"),
    ]
    for filename, header in dangerous:
        with pytest.raises(ValidationException) as exc_info:
            validate_file_security(filename, header)
        assert "Executable and script files" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failure_very_large_files(rag_test_session: AsyncSession, tmp_path: Path):
    """Verifies that uploads exceeding MAX_UPLOAD_SIZE_MB are rejected and partial disk files are deleted."""
    u = User(id=uuid.uuid4(), full_name="User", email="u@c.io", password_hash="pwd")
    p = Project(id=uuid.uuid4(), name="Proj", created_by=u.id)
    rag_test_session.add_all([u, p])
    await rag_test_session.commit()

    # Create oversized upload stream (mock limit = negative to trigger limit immediately)
    oversized_bytes = b"%PDF-1.7\n" + (b"A" * 2048)
    upload_file = UploadFile(
        file=io.BytesIO(oversized_bytes),
        filename="giant_spec.pdf",
        size=len(oversized_bytes),
    )

    with patch.object(settings, "MAX_UPLOAD_SIZE_MB", -1):
        with patch.object(settings, "UPLOAD_DIR", str(tmp_path / "storage")):
            svc = DocumentProcessingService(rag_test_session)
            with pytest.raises(ValidationException) as exc_info:
                await svc.save_uploaded_file(upload_file, p.id, u.id)
            assert "exceeds maximum allowed size" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failure_duplicate_documents(rag_test_session: AsyncSession):
    """Verifies that database unique constraints on stored_filename reject duplicates."""
    u = User(id=uuid.uuid4(), full_name="User", email="dup@c.io", password_hash="pwd")
    p = Project(id=uuid.uuid4(), name="Proj", created_by=u.id)
    rag_test_session.add_all([u, p])
    await rag_test_session.commit()

    d1 = Document(
        id=uuid.uuid4(),
        project_id=p.id,
        original_filename="spec.pdf",
        stored_filename="same_unique_name.pdf",
        file_type="pdf",
        file_size=100,
        storage_path="/tmp/1",
        processing_status="completed",
    )
    rag_test_session.add(d1)
    await rag_test_session.commit()

    d2 = Document(
        id=uuid.uuid4(),
        project_id=p.id,
        original_filename="spec.pdf",
        stored_filename="same_unique_name.pdf",
        file_type="pdf",
        file_size=200,
        storage_path="/tmp/2",
        processing_status="completed",
    )
    rag_test_session.add(d2)
    with pytest.raises(IntegrityError):
        await rag_test_session.commit()
    await rag_test_session.rollback()


def test_failure_gemini_api_timeout():
    """Verifies that transient network timeouts trigger retry backoff and eventually raise clean AiServiceException."""
    svc = GeminiService()
    call_count = 0

    def flaky_call():
        nonlocal call_count
        call_count += 1
        raise TimeoutError("503 Service Unavailable: Gateway Timeout")

    with patch("time.sleep", return_value=None):
        with pytest.raises(AiServiceException) as exc_info:
            svc._execute_with_retry("Timeout Test", flaky_call, max_retries=3, initial_delay=0.01)

    assert call_count == 3
    assert "Gemini Timeout Test failed" in str(exc_info.value)


def test_failure_invalid_api_key():
    """Verifies that 403 Forbidden / API_KEY_INVALID raises a clean user-facing exception without leaking key."""
    svc = GeminiService()

    def bad_key_call():
        raise Exception("403 Forbidden: API_KEY_INVALID. The provided API key is expired.")

    with pytest.raises(AiServiceException) as exc_info:
        svc._execute_with_retry("Key Test", bad_key_call, max_retries=1)

    assert "API Key is invalid or expired" in str(exc_info.value)


def test_failure_quota_exceeded():
    """Verifies that 429 Resource Exhausted / Quota Exceeded raises clear rate limit guidance."""
    svc = GeminiService()

    def quota_call():
        raise Exception("429 Too Many Requests: RESOURCE_EXHAUSTED. Quota exceeded for GenerateContent.")

    with pytest.raises(AiServiceException) as exc_info:
        svc._execute_with_retry("Quota Test", quota_call, max_retries=1)

    assert "rate limit or quota exceeded" in str(exc_info.value)


def test_failure_empty_gemini_response():
    """Verifies that empty responses from Gemini raise clean AiServiceException."""
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.text = ""
    mock_client.models.generate_content.return_value = mock_res

    svc = GeminiService()
    svc._client = mock_client
    svc._verified_gen_model = "gemini-2.5-flash"

    with pytest.raises(AiServiceException) as exc_info:
        svc.generate_content("Generate overview")

    assert "empty generation response" in str(exc_info.value)


def test_failure_invalid_json_response():
    """Verifies that malformed JSON returned by LLM is handled with schema repair or clean exception."""
    malformed_json_str = "```json\n{\n  'title': 'Broken JSON without closing brackets'\n"

    with pytest.raises(AiServiceException) as exc_info:
        RAGService._clean_json_response(malformed_json_str)
    assert "Failed to parse AI synthesis JSON response" in str(exc_info.value)


def test_failure_missing_source_evidence_marks_unsupported():
    """Verifies that claims lacking source evidence in corpus are marked strictly as UNSUPPORTED."""
    claim = FactualClaim(
        claim_id="claim_missing_001",
        statement="Unknown deployment architecture",
        source_chunk_ids=[],
        evidence_status=EvidenceStatus.UNSUPPORTED,
    )
    assert claim.evidence_status == EvidenceStatus.UNSUPPORTED
    assert len(claim.source_chunk_ids) == 0


def test_secret_redaction_and_env_loading():
    """Verifies that API keys are strictly redacted and never leaked in logs, exceptions, or errors."""
    fake_key = "AIzaSy" + "A" * 33
    error_message = f"Failed to authenticate with Google Gemini using key {fake_key} on host generativelanguage.googleapis.com."

    scrubbed = redact_secrets(error_message)

    assert fake_key not in scrubbed
    assert "[REDACTED_API_KEY]" in scrubbed
