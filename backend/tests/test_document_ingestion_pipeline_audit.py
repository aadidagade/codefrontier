"""
Comprehensive AI Document Processing QA Test Suite.
====================================================
Tests the complete document ingestion pipeline across:
- Formats: PDF, DOCX, TXT, Markdown (.md)
- Complete Workflow:
  1. Upload each file.
  2. Verify upload response.
  3. Verify physical storage on disk.
  4. Verify database metadata persistence.
  5. Verify text extraction accuracy against source.
  6. Verify page numbers where supported (PDF).
  7. Verify chunk generation and heading preservation.
  8. Verify 768-dimensional embeddings generation.
  9. Verify vector database storage.
  10. Verify document indexing status transitions.
  11. Verify semantic search retrieval.

- Edge Cases:
  - Empty files (0 bytes).
  - Corrupted files (invalid magic bytes/headers).
  - Unsupported formats (.exe, .sh, .bin, .py).
  - Duplicate file uploads (storage uniqueness).
  - Large files within supported limits (multi-megabyte).
  - Files with unusual characters (Unicode, emojis, Japanese, German umlauts).
  - Files containing tables (DOCX and Markdown tables).
  - Files with missing or unreadable text (scanned / zero-text PDF).
  - Transaction cleanliness on failed uploads.
"""

import io
import os
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
import fitz  # PyMuPDF
import docx  # python-docx
from fastapi import UploadFile
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.exceptions import ValidationException, NotFoundException
from app.models import (
    Base,
    User,
    Project,
    Document,
    DocumentChunk,
)
from app.services.chunking_service import chunking_service
from app.services.document_processing_service import DocumentProcessingService
from app.services.extractor import extract_document
from app.services.extractor.base import ExtractedDocument
from app.utils.file_validation import validate_file_security, sanitize_filename


@pytest_asyncio.fixture
async def doc_qa_session():
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


@pytest_asyncio.fixture
async def sample_project_and_user(doc_qa_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        full_name="Doc QA Engineer",
        email="docqa@platform.io",
        password_hash="fakehash",
        is_active=True,
    )
    project = Project(
        id=uuid.uuid4(),
        name="Ingestion Pipeline QA Project",
        description="Testing complete document pipeline",
        created_by=user.id,
    )
    doc_qa_session.add_all([user, project])
    await doc_qa_session.commit()
    return user, project


# ==============================================================================
# 1. COMPLETE WORKFLOW: PDF INGESTION PIPELINE
# ==============================================================================

@pytest.mark.asyncio
async def test_complete_workflow_pdf(doc_qa_session: AsyncSession, sample_project_and_user, tmp_path: Path, monkeypatch):
    """
    Tests end-to-end PDF ingestion:
    Upload -> Storage -> Metadata -> Extraction -> Page Numbers -> Chunking -> Embeddings -> Retrieval.
    """
    user, project = sample_project_and_user
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key-qa")

    # 1. Create a real 3-page PDF with distinct headings and facts
    pdf_path = tmp_path / "microservices_architecture.pdf"
    pdf_doc = fitz.open()

    # Page 1
    p1 = pdf_doc.new_page()
    p1.insert_text((50, 50), "1. Microservices System Overview", fontsize=18)
    p1.insert_text((50, 80), "The platform adopts a decoupled microservices architecture deployed on Kubernetes.", fontsize=11)
    p1.insert_text((50, 110), "The central API gateway routes incoming HTTPS requests to backend services.", fontsize=11)

    # Page 2
    p2 = pdf_doc.new_page()
    p2.insert_text((50, 50), "2. Database and Persistent Storage", fontsize=18)
    p2.insert_text((50, 80), "Primary database is PostgreSQL 16 with pgvector extension enabled.", fontsize=11)
    p2.insert_text((50, 110), "All transaction records require point-in-time recovery with 30 days retention.", fontsize=11)

    # Page 3
    p3 = pdf_doc.new_page()
    p3.insert_text((50, 50), "3. Security and Mutual TLS Protocols", fontsize=18)
    p3.insert_text((50, 80), "Inter-service RPC communication is secured using mTLS with TLS 1.3.", fontsize=11)
    p3.insert_text((50, 110), "JWT bearer tokens authenticate external clients with 15-minute expiration.", fontsize=11)

    pdf_doc.save(str(pdf_path))
    pdf_doc.close()

    file_bytes = pdf_path.read_bytes()

    # Step 1: Upload File
    upload_file = UploadFile(
        file=io.BytesIO(file_bytes),
        filename="microservices_architecture.pdf",
        size=len(file_bytes),
        headers={"content-type": "application/pdf"},
    )
    svc = DocumentProcessingService(doc_qa_session)
    doc_record = await svc.save_uploaded_file(upload_file, project.id, user.id)

    # Step 2 & 3: Verify Upload Response and Physical Storage
    assert doc_record.id is not None
    assert doc_record.original_filename == "microservices_architecture.pdf"
    assert doc_record.file_type == "pdf"
    assert doc_record.processing_status == "UPLOADED"
    assert os.path.exists(doc_record.storage_path)
    assert os.path.getsize(doc_record.storage_path) == len(file_bytes)

    # Step 4: Verify Initial Database Metadata
    assert doc_record.extraction_metadata["progress"] == 15
    assert len(doc_record.extraction_metadata["logs"]) >= 5

    # Step 5 & 6 & 7: Execute Extraction and Chunking Pipeline with Page Tracking
    with patch("app.services.gemini_service.gemini_service.generate_embeddings_batch", side_effect=lambda texts, **kwargs: [[0.05] * 768 for _ in texts]):
        processed_doc = await svc.execute_processing_pipeline(doc_record.id)

    assert processed_doc.processing_status == "READY"
    assert processed_doc.extraction_metadata["progress"] == 100
    assert processed_doc.extraction_metadata["page_count"] == 3
    assert processed_doc.extraction_metadata["word_count"] > 30

    # Step 8, 9 & 10: Verify Database Chunks and Embeddings
    chunks = (await doc_qa_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_record.id).order_by(DocumentChunk.chunk_index)
    )).scalars().all()

    assert len(chunks) >= 3
    # Check page numbers
    page_numbers = {c.page_number for c in chunks}
    assert 1 in page_numbers
    assert 2 in page_numbers
    assert 3 in page_numbers

    # Verify embeddings are 768 dimensions
    for c in chunks:
        assert c.embedding is not None
        assert len(c.embedding) == 768

    # Step 11: Verify Exact Content Grounding (Fact Matching)
    all_chunks_text = " ".join([c.content for c in chunks])
    assert "microservices architecture deployed on Kubernetes" in all_chunks_text
    assert "PostgreSQL 16 with pgvector" in all_chunks_text
    assert "mTLS with TLS 1.3" in all_chunks_text


# ==============================================================================
# 2. COMPLETE WORKFLOW: DOCX INGESTION PIPELINE (WITH TABLES)
# ==============================================================================

@pytest.mark.asyncio
async def test_complete_workflow_docx_with_tables(doc_qa_session: AsyncSession, sample_project_and_user, tmp_path: Path, monkeypatch):
    """
    Tests end-to-end Word DOCX ingestion:
    Includes headings, styled paragraphs, and structured 3x3 data tables.
    """
    user, project = sample_project_and_user
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key-qa")

    docx_path = tmp_path / "onboarding_guide.docx"
    doc = docx.Document()

    # Heading 1
    doc.add_heading("Engineering Onboarding Guide", level=1)
    doc.add_paragraph("Welcome to the platform engineering team. This document outlines onboarding protocols.")

    # Heading 2
    doc.add_heading("Service Ownership Matrix", level=2)
    doc.add_paragraph("The following table details core microservice ownership across squads:")

    # Table with 3 rows and 3 columns
    table = doc.add_table(rows=4, cols=3)
    headers = ["Service Name", "Lead Squad", "Tier"]
    for j, h in enumerate(headers):
        table.rows[0].cells[j].text = h

    data_rows = [
        ["auth-service", "Identity Team", "Tier 1"],
        ["payment-gateway", "Billing Squad", "Tier 1"],
        ["notification-worker", "Core Platform", "Tier 2"],
    ]
    for i, row in enumerate(data_rows):
        for j, val in enumerate(row):
            table.rows[i + 1].cells[j].text = val

    doc.save(str(docx_path))
    file_bytes = docx_path.read_bytes()

    upload_file = UploadFile(
        file=io.BytesIO(file_bytes),
        filename="onboarding_guide.docx",
        size=len(file_bytes),
        headers={"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    )
    svc = DocumentProcessingService(doc_qa_session)
    doc_record = await svc.save_uploaded_file(upload_file, project.id, user.id)

    with patch("app.services.gemini_service.gemini_service.generate_embeddings_batch", side_effect=lambda texts, **kwargs: [[0.01] * 768 for _ in texts]):
        processed_doc = await svc.execute_processing_pipeline(doc_record.id)

    assert processed_doc.processing_status == "READY"
    chunks = (await doc_qa_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_record.id)
    )).scalars().all()

    assert len(chunks) >= 1
    full_text = " ".join([c.content for c in chunks])
    # Verify table data was extracted cleanly with column separators
    assert "auth-service | Identity Team | Tier 1" in full_text
    assert "payment-gateway | Billing Squad | Tier 1" in full_text
    assert "notification-worker | Core Platform | Tier 2" in full_text


# ==============================================================================
# 3. COMPLETE WORKFLOW: TXT INGESTION PIPELINE
# ==============================================================================

@pytest.mark.asyncio
async def test_complete_workflow_txt(doc_qa_session: AsyncSession, sample_project_and_user, tmp_path: Path, monkeypatch):
    """Tests plain text ingestion, paragraph block preservation, and word counts."""
    user, project = sample_project_and_user
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key-qa")

    txt_content = (
        "Project Frontier Handover Notes\n\n"
        "1. Current Status: Production release v1.4 is stable.\n\n"
        "2. Database Cutover: Upgraded PostgreSQL without customer interruption.\n\n"
        "3. Critical Monitoring: Datadog dashboard #42 tracks p99 latency under 45ms.\n"
    )
    file_bytes = txt_content.encode("utf-8")

    upload_file = UploadFile(
        file=io.BytesIO(file_bytes),
        filename="handover_notes.txt",
        size=len(file_bytes),
        headers={"content-type": "text/plain"},
    )
    svc = DocumentProcessingService(doc_qa_session)
    doc_record = await svc.save_uploaded_file(upload_file, project.id, user.id)

    with patch("app.services.gemini_service.gemini_service.generate_embeddings_batch", side_effect=lambda texts, **kwargs: [[0.05] * 768 for _ in texts]):
        processed_doc = await svc.execute_processing_pipeline(doc_record.id)

    assert processed_doc.processing_status == "READY"
    assert processed_doc.extraction_metadata["word_count"] == len(txt_content.split())
    chunks = (await doc_qa_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_record.id)
    )).scalars().all()

    assert len(chunks) >= 1
    assert "Datadog dashboard #42" in chunks[0].content


# ==============================================================================
# 4. COMPLETE WORKFLOW: MARKDOWN INGESTION PIPELINE (WITH MD TABLES)
# ==============================================================================

@pytest.mark.asyncio
async def test_complete_workflow_markdown_with_tables(doc_qa_session: AsyncSession, sample_project_and_user, tmp_path: Path, monkeypatch):
    """Tests Markdown AST extraction with hierarchical headers and markdown table formatting."""
    user, project = sample_project_and_user
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key-qa")

    md_content = """# Release Runbook v2.0

Comprehensive checklist for production releases.

## Pre-Release Verification

Verify staging deployment matches production manifest.

| Check Item | Owner | Tool |
| :--- | :--- | :--- |
| Security Scan | SecOps | Snyk |
| Load Testing | QA Lead | k6 |
| Database Migration | DBA | Flyway |

## Rollback Strategy

In case of error rate > 0.5%, execute automated blue-green rollback within 60 seconds.
"""
    file_bytes = md_content.encode("utf-8")

    upload_file = UploadFile(
        file=io.BytesIO(file_bytes),
        filename="release_runbook.md",
        size=len(file_bytes),
        headers={"content-type": "text/markdown"},
    )
    svc = DocumentProcessingService(doc_qa_session)
    doc_record = await svc.save_uploaded_file(upload_file, project.id, user.id)

    with patch("app.services.gemini_service.gemini_service.generate_embeddings_batch", side_effect=lambda texts, **kwargs: [[0.03] * 768 for _ in texts]):
        processed_doc = await svc.execute_processing_pipeline(doc_record.id)

    assert processed_doc.processing_status == "READY"
    chunks = (await doc_qa_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_record.id)
    )).scalars().all()

    full_chunks_text = " ".join([c.content for c in chunks])
    assert "Security Scan" in full_chunks_text
    assert "Rollback Strategy" in full_chunks_text
    assert "k6" in full_chunks_text


# ==============================================================================
# 5. EDGE CASE: EMPTY FILES (0 BYTES)
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_case_empty_file_rejected(sample_project_and_user):
    """Verifies that empty (0 bytes) PDF, DOCX, or text files are rejected during validation."""
    # Empty PDF (fails magic byte check)
    with pytest.raises(ValidationException) as exc1:
        validate_file_security("empty.pdf", b"")
    assert "Invalid PDF magic bytes signature header" in str(exc1.value)

    # Empty DOCX (fails zip header check)
    with pytest.raises(ValidationException) as exc2:
        validate_file_security("empty.docx", b"")
    assert "Invalid DOCX magic bytes signature header" in str(exc2.value)


# ==============================================================================
# 6. EDGE CASE: CORRUPTED FILES
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_case_corrupted_files(sample_project_and_user):
    """Verifies that corrupted files masquerading with false extensions are rejected."""
    # Fake PDF containing plain text
    with pytest.raises(ValidationException):
        validate_file_security("malicious_fake.pdf", b"This is not a real PDF document.")

    # Fake DOCX containing random garbage bytes
    with pytest.raises(ValidationException):
        validate_file_security("broken.docx", b"\x00\x01\x02\x03\x04\x05")


# ==============================================================================
# 7. EDGE CASE: UNSUPPORTED & DANGEROUS FORMATS
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_case_unsupported_formats(sample_project_and_user):
    """Verifies that executables, scripts, and disallowed extensions are strictly blocked."""
    # Executable
    with pytest.raises(ValidationException) as exc1:
        validate_file_security("installer.exe", b"MZ\x90\x00")
    assert "strictly forbidden" in str(exc1.value)

    # Shell script
    with pytest.raises(ValidationException) as exc2:
        validate_file_security("deploy.sh", b"#!/bin/bash\nrm -rf /")
    assert "strictly forbidden" in str(exc2.value)

    # Python file
    with pytest.raises(ValidationException) as exc3:
        validate_file_security("exploit.py", b"import os\nos.system('calc')")
    assert "strictly forbidden" in str(exc3.value)

    # Image format
    with pytest.raises(ValidationException) as exc4:
        validate_file_security("screenshot.png", b"\x89PNG\r\n\x1a\n")
    assert "Unsupported format" in str(exc4.value)


# ==============================================================================
# 8. EDGE CASE: DUPLICATE UPLOADS (STORAGE UNIQUENESS)
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_case_duplicate_uploads(doc_qa_session: AsyncSession, sample_project_and_user):
    """
    Verifies that uploading the exact same document twice generates distinct stored filenames
    and separate database records without disk collision.
    """
    user, project = sample_project_and_user
    content = b"Identical documentation payload for duplicate upload testing."

    svc = DocumentProcessingService(doc_qa_session)

    upload1 = UploadFile(file=io.BytesIO(content), filename="handbook.txt", size=len(content))
    doc1 = await svc.save_uploaded_file(upload1, project.id, user.id)

    upload2 = UploadFile(file=io.BytesIO(content), filename="handbook.txt", size=len(content))
    doc2 = await svc.save_uploaded_file(upload2, project.id, user.id)

    assert doc1.id != doc2.id
    assert doc1.stored_filename != doc2.stored_filename
    assert doc1.original_filename == doc2.original_filename == "handbook.txt"
    assert os.path.exists(doc1.storage_path)
    assert os.path.exists(doc2.storage_path)
    assert doc1.storage_path != doc2.storage_path


# ==============================================================================
# 9. EDGE CASE: UNUSUAL & SPECIAL CHARACTERS (UNICODE, EMOJIS, I18N)
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_case_unusual_characters(doc_qa_session: AsyncSession, sample_project_and_user, monkeypatch):
    """Verifies that non-ASCII Unicode, German umlauts, Japanese text, and emojis extract cleanly."""
    user, project = sample_project_and_user
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key-qa")

    special_content = (
        "# International Infrastructure Specification 🌐\n\n"
        "Deployment Regions: Frankfurt (Zürich: Überwachungsbericht für Geräte 🇩🇪), "
        "Tokyo (東京リージョン: 高可用性クラスタ 🇯🇵), and São Paulo (Brasil 🇧🇷).\n\n"
        "Mathematical Constraints: Target latency Δt ≤ 15ms with throughput ∑(QPS) ≥ 10,000/s ± 2.5%."
    )
    file_bytes = special_content.encode("utf-8")

    upload_file = UploadFile(file=io.BytesIO(file_bytes), filename="i18n_spec.md", size=len(file_bytes))
    svc = DocumentProcessingService(doc_qa_session)
    doc_record = await svc.save_uploaded_file(upload_file, project.id, user.id)

    with patch("app.services.gemini_service.gemini_service.generate_embeddings_batch", side_effect=lambda texts, **kwargs: [[0.01] * 768 for _ in texts]):
        processed_doc = await svc.execute_processing_pipeline(doc_record.id)

    assert processed_doc.processing_status == "READY"
    chunks = (await doc_qa_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_record.id)
    )).scalars().all()

    full_text = " ".join([c.content for c in chunks])
    assert "Überwachungsbericht" in full_text
    assert "高可用性クラスタ" in full_text
    assert "Δt ≤ 15ms" in full_text


# ==============================================================================
# 10. EDGE CASE: SCANNED / UNREADABLE PDF (NEEDS_OCR DETECTION)
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_case_scanned_pdf_needs_ocr(doc_qa_session: AsyncSession, sample_project_and_user, tmp_path: Path):
    """
    Verifies that a multi-page PDF lacking a machine-readable text layer is correctly flagged
    as NEEDS_OCR rather than silently succeeding with empty chunks.
    """
    user, project = sample_project_and_user

    # Create a 2-page PDF with no text (empty canvas mimicking a scanned image)
    pdf_path = tmp_path / "scanned_invoice.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    file_bytes = pdf_path.read_bytes()
    upload_file = UploadFile(file=io.BytesIO(file_bytes), filename="scanned_invoice.pdf", size=len(file_bytes))
    svc = DocumentProcessingService(doc_qa_session)
    doc_record = await svc.save_uploaded_file(upload_file, project.id, user.id)

    processed_doc = await svc.execute_processing_pipeline(doc_record.id)

    assert processed_doc.processing_status == "NEEDS_OCR"
    assert processed_doc.extraction_metadata.get("needs_ocr") is True
    # Zero chunks created for unreadable text
    chunks = (await doc_qa_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_record.id)
    )).scalars().all()
    assert len(chunks) == 0


# ==============================================================================
# 12. SEMANTIC RETRIEVAL & VECTOR DATABASE SEARCH (STEP 11)
# ==============================================================================

@pytest.mark.asyncio
async def test_semantic_retrieval_and_hybrid_search(doc_qa_session: AsyncSession, sample_project_and_user):
    """
    Verifies step 11: Document chunks indexed with embeddings are retrievable via
    semantic vector similarity and full-text keyword search.
    """
    from app.repositories.document_repository import DocumentRepository

    user, project = sample_project_and_user

    # Create document with 2 chunks
    doc = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        uploaded_by=user.id,
        original_filename="security_playbook.md",
        stored_filename="sec_playbook.md",
        file_type="md",
        file_size=1024,
        storage_path="/tmp/sec.md",
        processing_status="READY",
    )
    doc_qa_session.add(doc)
    await doc_qa_session.flush()

    chunk1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        project_id=project.id,
        chunk_index=0,
        content="Zero Trust Architecture: All microservices must enforce mutual TLS with TLS 1.3.",
        page_number=1,
        section_title="Zero Trust Network",
        embedding=[0.2] * 768,
    )
    chunk2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        project_id=project.id,
        chunk_index=1,
        content="Disaster Recovery: S3 buckets replicate to us-west-2 region every 15 minutes.",
        page_number=2,
        section_title="Disaster Recovery Policy",
        embedding=[-0.2] * 768,
    )
    doc_qa_session.add_all([chunk1, chunk2])
    await doc_qa_session.commit()

    repo = DocumentRepository(doc_qa_session)

    # 1. Semantic Vector Search
    query_vector = [0.2] * 768
    vector_results = await repo.search_similar_chunks(
        project_id=project.id,
        query_embedding=query_vector,
        top_k=5,
    )
    assert len(vector_results) >= 1
    top_chunk, doc_name, sim_score = vector_results[0]
    assert doc_name == "security_playbook.md"
    assert top_chunk.section_title == "Zero Trust Network"
    assert "mutual TLS" in top_chunk.content

    # 2. Keyword Search
    kw_results = await repo.search_keyword_chunks(
        project_id=project.id,
        query_text="Disaster Recovery S3 replicate",
        top_k=5,
    )
    assert len(kw_results) >= 1
    top_kw_chunk, kw_doc_name, kw_score = kw_results[0]
    assert kw_doc_name == "security_playbook.md"
    assert "us-west-2" in top_kw_chunk.content


# ==============================================================================
# 13. EDGE CASE: LARGE FILES WITHIN & EXCEEDING LIMITS
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_case_large_file_within_supported_limits(doc_qa_session: AsyncSession, sample_project_and_user, monkeypatch):
    """
    Verifies that a large document (e.g. 2MB within 20MB limit) is accepted, stored,
    and processed without memory or buffer issues.
    """
    user, project = sample_project_and_user
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key-qa")

    # Generate a 1.2MB Markdown document
    repeat_block = "# Architecture Section\n\nHigh throughput distributed event broker using Kafka.\n\n" * 15000
    file_bytes = repeat_block.encode("utf-8")
    assert len(file_bytes) > 1024 * 1024  # > 1MB

    upload_file = UploadFile(file=io.BytesIO(file_bytes), filename="large_arch_spec.md", size=len(file_bytes))
    svc = DocumentProcessingService(doc_qa_session)
    doc_record = await svc.save_uploaded_file(upload_file, project.id, user.id)

    assert doc_record.file_size == len(file_bytes)
    assert os.path.exists(doc_record.storage_path)

    # Process large document
    with patch("app.services.gemini_service.gemini_service.generate_embeddings_batch", side_effect=lambda texts, **kwargs: [[0.01] * 768 for _ in texts]):
        processed_doc = await svc.execute_processing_pipeline(doc_record.id)

    assert processed_doc.processing_status == "READY"
    assert processed_doc.extraction_metadata["chunk_count"] > 1


@pytest.mark.asyncio
async def test_edge_case_file_exceeding_size_limit_rejected(doc_qa_session: AsyncSession, sample_project_and_user, monkeypatch):
    """
    Verifies that an uploaded file exceeding MAX_UPLOAD_SIZE_MB is rejected immediately
    with ValidationException and does not leave orphaned files or database records.
    """
    user, project = sample_project_and_user

    # Set temporary low limit to 1MB
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)

    # Payload 1.5MB (exceeds 1MB limit)
    oversized_bytes = b"%PDF-1.7\n" + (b"A" * (1500 * 1024))
    upload_file = UploadFile(file=io.BytesIO(oversized_bytes), filename="oversized.pdf", size=len(oversized_bytes))

    svc = DocumentProcessingService(doc_qa_session)
    with pytest.raises(ValidationException) as exc:
        await svc.save_uploaded_file(upload_file, project.id, user.id)

    assert "exceeds maximum allowed size" in str(exc.value)

    # Ensure zero documents persisted
    docs = (await doc_qa_session.execute(select(Document).where(Document.project_id == project.id))).scalars().all()
    assert len(docs) == 0
