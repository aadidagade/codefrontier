import io
import uuid
import pytest
from pathlib import Path
from app.utils.file_validation import validate_file_security, sanitize_filename
from app.core.exceptions import ValidationException
from app.services.extractor.base import ExtractedDocument, ExtractedSection
from app.services.extractor.text_extractor import extract_text_and_markdown
from app.services.chunking_service import IntelligentChunkingService


def test_filename_sanitization_and_path_traversal():
    """Verifies that directory traversal attacks and null bytes are stripped."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\Windows\\System32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("safe_report.pdf") == "safe_report.pdf"


def test_dangerous_extensions_rejected():
    """Ensures executable and script file formats are strictly blocked."""
    with pytest.raises(ValidationException) as exc_info:
        validate_file_security("malicious.exe", b"MZ\x90\x00")
    assert "Executable and script files" in str(exc_info.value)

    with pytest.raises(ValidationException):
        validate_file_security("script.sh", b"#!/bin/bash")

    with pytest.raises(ValidationException):
        validate_file_security("payload.bat", b"@echo off")


def test_magic_bytes_validation():
    """Tests header signature checks for PDF and text."""
    # Valid PDF magic bytes
    clean_name, file_type = validate_file_security("valid.pdf", b"%PDF-1.7\n%sample")
    assert file_type == "pdf"

    # Corrupt/disguised PDF
    with pytest.raises(ValidationException):
        validate_file_security("fake.pdf", b"NOT_A_PDF_HEADER")

    # Valid TXT and Markdown
    clean_txt, txt_type = validate_file_security("notes.txt", b"Standard ASCII text")
    assert txt_type == "txt"

    clean_md, md_type = validate_file_security("readme.md", b"# Markdown Header\nSome text")
    assert md_type == "md"


def test_markdown_extraction(tmp_path: Path):
    """Verifies markdown heading and paragraph extraction."""
    md_file = tmp_path / "architecture.md"
    md_content = """# Payment Orchestration Engine

Overview of the payment gateway failover system.

## Circuit Breakers

Envoy sidecar handles timeouts in <1.4ms with Redis heartbeats.

## Kafka DLQ Retention

Settlement audits require 14 days retention.
"""
    md_file.write_text(md_content, encoding="utf-8")

    extracted = extract_text_and_markdown(md_file, is_markdown=True)
    assert extracted.word_count > 10
    assert len(extracted.sections) >= 3
    assert extracted.sections[0].title == "Payment Orchestration Engine"
    assert "Envoy sidecar" in extracted.sections[1].content


def test_semantic_chunking_preserves_headings():
    """Tests that chunking preserves section titles, paragraph integrity, and sentence breaks."""
    doc = ExtractedDocument(
        full_text="Test document",
        sections=[
            ExtractedSection(
                title="Database Partitioning",
                content=(
                    "PostgreSQL 16 zero-downtime cutover. "
                    "All 1.4 million sessions migrate on Nov 20 during the scheduled maintenance window. "
                    "Downstream analytics verified."
                ),
                page_number=3,
            )
        ],
        page_count=3,
        word_count=25,
    )

    chunker = IntelligentChunkingService(target_chunk_size=120, chunk_overlap=30)
    doc_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    chunks = chunker.create_chunks(doc, doc_id, proj_id)
    assert len(chunks) >= 1
    # Check heading prefix attached
    assert "## Database Partitioning" in chunks[0].content
    assert chunks[0].page_number == 3
    assert chunks[0].section_title == "Database Partitioning"
    assert chunks[0].document_id == doc_id
    assert chunks[0].project_id == proj_id


def test_scanned_pdf_detection_flag():
    """Verifies that an extracted document with insufficient text is flagged as needing OCR."""
    scanned_doc = ExtractedDocument(
        full_text="Scan",
        sections=[],
        page_count=10,
        word_count=1,
        char_count=4,
        is_scanned=True,
        needs_ocr=True,
    )
    assert scanned_doc.needs_ocr is True
    assert scanned_doc.is_scanned is True
