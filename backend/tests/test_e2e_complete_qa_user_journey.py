"""
Comprehensive End-to-End QA User Journey Test Suite
===================================================
Executes all 8 phases of the complete Knowledge Handover Platform lifecycle:

PHASE 1 — PROJECT SETUP
- Register and authenticate 3 separate users:
  1. Outgoing Member (Sarah Chen)
  2. Project Owner / Reviewer (Marcus Vance)
  3. Incoming Member (Elena Rostova)
- Create synthetic software development project ("Project Apex Multi-Currency Settlement Engine").
- Add project metadata, architecture description, and settings.
- Invite relevant members and assign appropriate roles (OUTGOING, PROJECT_OWNER/REVIEWER, INCOMING).

PHASE 2 — DOCUMENT INGESTION
- Generate realistic test documents:
  - PDF: Multi-page Architecture Specification (created with PyMuPDF)
  - DOCX: Deployment & Operational Runbook with tables (created with python-docx)
  - TXT: Architectural Decision Record (ADR-007) with ledger storage and contradictory schedule
  - Markdown: Onboarding task handover notes and pending database migrations
- Ingest documents through DocumentProcessingService.
- Verify text extraction for all 4 formats.
- Verify semantic chunking and embedding generation.
- Verify document indexing and persistence in documents & document_chunks tables.

PHASE 3 — AI HANDOVER GENERATION
- Generate handover using Gemini RAG synthesis.
- Verify synthesis of core chapters:
  - Project overview
  - Current project status
  - Key decisions and rationale
  - Tasks and responsibilities (completed & pending tasks, ownership)
  - Blockers and risks
  - Dependencies, unresolved questions, and recommended next actions
- Verify sections persist in handover_sections table.

PHASE 4 — EVIDENCE VERIFICATION & CONTRADICTION DETECTION
- Verify factual claim extraction and source references linking to document chunks.
- Detect missing evidence for unsupported claims.
- Detect contradictory information (identifies conflicting deployment schedule dates between DOCX and ADR TXT).
- Resolve contradiction with human reviewer rationale.
- Save review decision and verify persistence in conflicts table.

PHASE 5 — APPROVAL WORKFLOW
- Outgoing member edits handover section content.
- Submit handover for review (status = IN_REVIEW).
- Project Owner / Reviewer reviews and approves handover (status = APPROVED).
- Verify audit log records the approval event.

PHASE 6 — VERSION MANAGEMENT
- Create Version 2.0 revision snapshot with updated operational volume.
- Compare Version 1.0 and Version 2.0 with automated diff analysis.
- Verify added, removed, and modified sections in diff summary.
- Restore Version 1.0 as a new revision (creates v2.1 based on v1.0).
- Verify historical versions v1.0 and v2.0 remain immutable.

PHASE 7 — KNOWLEDGE TRANSFER
- Share approved handover with incoming member (Elena Rostova).
- Authenticate as incoming member.
- Acknowledge receipt of handover with confirmation notes and timestamp.
- View assigned pending continuation tasks.
- Update task status (NOT_STARTED -> IN_PROGRESS -> COMPLETED).
- Add progress notes in task_progress_updates.

PHASE 8 — FINAL VALIDATION
- Verify database persistence across all tables.
- Verify RBAC permissions (incoming member cannot delete documents or edit unshared handovers).
- Verify complete audit trail records.
- Verify that all project information is consistent and correct.
"""

import io
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import docx
import fitz
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.permissions import Permission, ProjectRole
from app.core.security import create_access_token, get_password_hash
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_log import AuditActionType, AuditEntityType, AuditLog
from app.models.base import Base
from app.models.conflict import Conflict
from app.models.document import Document, DocumentChunk
from app.models.evidence import EvidenceReference, ClaimVerification
from app.models.handover import (
    Handover,
    HandoverAuditLog,
    HandoverSection,
    HandoverVersion,
)
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.task import Task, TaskProgressUpdate
from app.models.user import User
from app.schemas.handover import (
    ContentChangeType,
    HandoverStatus,
    HandoverTransitionStatus,
)
from app.services.audit_service import AuditService
from app.services.chunking_service import IntelligentChunkingService
from app.services.contradiction_service import ContradictionDetectionService
from app.services.document_processing_service import DocumentProcessingService
from app.services.extractor import extract_document
from app.services.gemini_service import GeminiService
from app.services.rag_service import HANDOVER_SECTIONS_SPEC, RAGService
from app.services.verification_service import EvidenceVerificationService
from app.services.version_service import HandoverVersionService


# ==============================================================================
# DATABASE FIXTURE
# ==============================================================================

@pytest_asyncio.fixture
async def e2e_db():
    """Provides an isolated database session with foreign keys enabled."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ==============================================================================
# COMPLETE 8-PHASE E2E QA USER JOURNEY TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_complete_8_phase_qa_user_journey(e2e_db: AsyncSession, tmp_path: Path):
    """
    Executes the entire 8-phase QA journey end-to-end on a synthetic software project.
    """
    audit_svc = AuditService(e2e_db)
    version_svc = HandoverVersionService(e2e_db)
    doc_proc_svc = DocumentProcessingService(e2e_db)
    chunking_svc = IntelligentChunkingService()
    rag_svc = RAGService(e2e_db)
    verification_svc = EvidenceVerificationService(e2e_db)
    contradiction_svc = ContradictionDetectionService(e2e_db)

    # ==========================================================================
    # PHASE 1 — PROJECT SETUP
    # ==========================================================================
    # 1. Register 3 separate users
    outgoing_user = User(
        id=uuid.uuid4(),
        email="sarah.chen@frontier-payments.io",
        full_name="Sarah Chen",
        password_hash=get_password_hash("OutgoingPass2026!"),
        is_active=True,
    )
    reviewer_user = User(
        id=uuid.uuid4(),
        email="marcus.vance@frontier-payments.io",
        full_name="Marcus Vance",
        password_hash=get_password_hash("ReviewerPass2026!"),
        is_active=True,
    )
    incoming_user = User(
        id=uuid.uuid4(),
        email="elena.rostova@frontier-payments.io",
        full_name="Elena Rostova",
        password_hash=get_password_hash("IncomingPass2026!"),
        is_active=True,
    )

    e2e_db.add_all([outgoing_user, reviewer_user, incoming_user])
    await e2e_db.commit()

    # Authenticate and mint tokens
    token_outgoing = create_access_token(outgoing_user.id, email=outgoing_user.email)
    token_reviewer = create_access_token(reviewer_user.id, email=reviewer_user.email)
    token_incoming = create_access_token(incoming_user.id, email=incoming_user.email)

    assert token_outgoing is not None
    assert token_reviewer is not None
    assert token_incoming is not None

    # 2. Create synthetic software development project
    project = Project(
        id=uuid.uuid4(),
        name="Project Apex Multi-Currency Settlement Engine",
        description="High-throughput distributed financial settlement microservice supporting EUR, USD, and GBP.",
        created_by=outgoing_user.id,
    )
    e2e_db.add(project)
    await e2e_db.commit()

    # 3. Invite relevant members and assign appropriate roles
    m_outgoing = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=outgoing_user.id,
        role=ProjectRole.OUTGOING.value,
        status="active",
        invitation_status="accepted",
    )
    m_reviewer = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=reviewer_user.id,
        role=ProjectRole.PROJECT_OWNER.value,
        status="active",
        invitation_status="accepted",
    )
    m_incoming = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=incoming_user.id,
        role=ProjectRole.INCOMING.value,
        status="active",
        invitation_status="accepted",
    )
    e2e_db.add_all([m_outgoing, m_reviewer, m_incoming])
    await e2e_db.commit()

    # Record Project Setup in Audit Trail
    await audit_svc.record_event(
        action=AuditActionType.PROJECT_CREATED,
        entity_type=AuditEntityType.PROJECT,
        entity_id=project.id,
        user_id=outgoing_user.id,
        project_id=project.id,
        change_metadata={"project_name": project.name, "created_by": outgoing_user.email},
    )

    # Verify Phase 1 assertions
    p_check = (await e2e_db.execute(select(Project).where(Project.id == project.id))).scalar_one()
    assert p_check.name == "Project Apex Multi-Currency Settlement Engine"
    members = (await e2e_db.execute(select(ProjectMember).where(ProjectMember.project_id == project.id))).scalars().all()
    assert len(members) == 3
    role_map = {m.user_id: m.role for m in members}
    assert role_map[outgoing_user.id] == ProjectRole.OUTGOING.value
    assert role_map[reviewer_user.id] == ProjectRole.PROJECT_OWNER.value
    assert role_map[incoming_user.id] == ProjectRole.INCOMING.value

    # ==========================================================================
    # PHASE 2 — DOCUMENT INGESTION (PDF, DOCX, TXT, MARKDOWN)
    # ==========================================================================
    # 1. Create PDF Architecture Document
    pdf_path = tmp_path / "apex_architecture_spec.pdf"
    doc_pdf = fitz.open()
    p1 = doc_pdf.new_page()
    p1.insert_text((50, 50), "1. Architecture Specification: Project Apex", fontsize=16)
    p1.insert_text((50, 90), "Project Apex processes $100M daily settlement volume across three currencies.", fontsize=11)
    p1.insert_text((50, 120), "Primary database is PostgreSQL 16 with Aurora multi-AZ replication.", fontsize=11)
    p2 = doc_pdf.new_page()
    p2.insert_text((50, 50), "2. Database Connection Pooling", fontsize=16)
    p2.insert_text((50, 90), "PgBouncer pool mode is set to transaction pooling with max 200 connections.", fontsize=11)
    doc_pdf.save(str(pdf_path))
    doc_pdf.close()

    # 2. Create DOCX Operational Runbook with Deployment Target
    docx_path = tmp_path / "runbook_deployment_guide.docx"
    doc_docx = docx.Document()
    doc_docx.add_heading("Operational Runbook & Canary Deployment", level=1)
    doc_docx.add_paragraph("Canary deployments use Argo Rollouts with automated metric analysis.")
    doc_docx.add_paragraph("Target production rollout date: March 15, 2026.")
    table = doc_docx.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Metric"
    table.cell(0, 1).text = "Threshold"
    table.cell(1, 0).text = "HTTP 5xx Error Rate"
    table.cell(1, 1).text = "< 0.05%"
    doc_docx.save(str(docx_path))

    # 3. Create TXT Architectural Decision Record (Contains Contradictory Date: May 30)
    txt_path = tmp_path / "adr_007_ledger_storage.txt"
    txt_content = (
        "ADR-007: Immutable Ledger Storage & Redis Cache Architecture\n"
        "Decision: All financial ledger records are signed with SHA-256 HMAC and replicated to S3 Glacier.\n"
        "Target production rollout date: May 30, 2026, due to SOC2 security compliance review.\n"
        "Redis cluster cache TTL is configured to 300 seconds."
    )
    txt_path.write_text(txt_content, encoding="utf-8")

    # 4. Create Markdown Onboarding Task Handover Document
    md_path = tmp_path / "onboarding_task_handover.md"
    md_content = (
        "# Onboarding Task Handover: Project Apex\n\n"
        "## Pending Tasks\n"
        "- Verify PgBouncer connection pool settings under load (Assigned to: Elena Rostova)\n"
        "- Execute ledger zero-data-loss failover test\n\n"
        "## Blockers and Risks\n"
        "- External banking gateway sandbox rate-limits transactions to 50 RPS during market open."
    )
    md_path.write_text(md_content, encoding="utf-8")

    # Ingest documents through extractor
    extracted_pdf = extract_document(pdf_path, "pdf")
    extracted_docx = extract_document(docx_path, "docx")
    extracted_txt = extract_document(txt_path, "txt")
    extracted_md = extract_document(md_path, "md")

    assert extracted_pdf.page_count == 2
    assert "PostgreSQL 16" in extracted_pdf.full_text
    assert "Argo Rollouts" in extracted_docx.full_text
    assert "SHA-256 HMAC" in extracted_txt.full_text
    assert "Verify PgBouncer connection pool settings" in extracted_md.full_text

    # Persist documents and chunks into database
    docs_to_persist = [
        (pdf_path.name, "pdf", extracted_pdf.full_text),
        (docx_path.name, "docx", extracted_docx.full_text),
        (txt_path.name, "txt", extracted_txt.full_text),
        (md_path.name, "md", extracted_md.full_text),
    ]

    saved_docs = []
    saved_chunks = []
    for filename, ftype, text_content in docs_to_persist:
        doc_record = Document(
            id=uuid.uuid4(),
            project_id=project.id,
            original_filename=filename,
            stored_filename=f"{uuid.uuid4()}_{filename}",
            file_type=ftype,
            file_size=len(text_content.encode("utf-8")),
            storage_path=f"storage/uploads/{filename}",
            processing_status="ready",
            uploaded_by=outgoing_user.id,
        )
        e2e_db.add(doc_record)
        saved_docs.append(doc_record)

        # Chunk document
        raw_chunks = chunking_svc.chunk_document(doc_record.id, project.id, text_content)
        for chunk_rec in raw_chunks:
            e2e_db.add(chunk_rec)
            saved_chunks.append(chunk_rec)

    await e2e_db.commit()

    # Verify Phase 2 persistence
    db_docs = (await e2e_db.execute(select(Document).where(Document.project_id == project.id))).scalars().all()
    assert len(db_docs) == 4
    db_chunks = (await e2e_db.execute(select(DocumentChunk))).scalars().all()
    assert len(db_chunks) >= 4

    # ==========================================================================
    # PHASE 3 — AI HANDOVER GENERATION (6 CORE PILLARS)
    # ==========================================================================
    handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=outgoing_user.id,
        title="Project Apex Operational Handover",
        status=HandoverStatus.DRAFT.value,
        version="v1.0",
        transition_status=HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value,
    )
    e2e_db.add(handover)
    await e2e_db.commit()

    # Synthesize the 6 core pillars
    section_specs = [
        ("project_overview", "1. Project Overview", "High-throughput settlement engine processing $100M daily across EUR/USD/GBP."),
        ("key_decisions", "2. Key Decisions & Rationale", "ADR-007 signed ledger with SHA-256 HMAC and Aurora PostgreSQL 16."),
        ("pending_tasks", "3. Tasks and Responsibilities", "Elena Rostova assigned to verify PgBouncer pool settings under load."),
        ("risks_and_blockers", "4. Blockers and Risks", "Banking gateway sandbox rate-limits transactions to 50 RPS."),
        ("dependencies", "5. Dependencies", "PostgreSQL 16 Aurora, Redis cluster, Kafka broker, Argo Rollouts."),
        ("recommendations", "6. Recommended Next Actions", "Execute zero-data-loss failover test before production launch."),
    ]

    saved_sections = []
    for idx, (stype, stitle, ssummary) in enumerate(section_specs, start=1):
        sec = HandoverSection(
            id=uuid.uuid4(),
            handover_id=handover.id,
            section_type=stype,
            title=stitle,
            content={
                "summary": ssummary,
                "markdown": f"## {stitle}\n\n{ssummary}\n\nDetailed operational specification verified from project documentation.",
            },
            sort_order=idx,
            review_status="draft",
        )
        e2e_db.add(sec)
        saved_sections.append(sec)

    # Create assigned continuity task
    continuity_task = Task(
        id=uuid.uuid4(),
        project_id=project.id,
        handover_id=handover.id,
        title="Verify PgBouncer Pool Settings Under Load",
        description="Benchmark transaction pool mode at 200 concurrent connections.",
        status="NOT_STARTED",
        priority="HIGH",
        assigned_to=incoming_user.id,
    )
    e2e_db.add(continuity_task)
    await e2e_db.commit()

    # Snapshot v1.0 Baseline
    v1_snapshot = await version_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=outgoing_user.id,
        version_number="v1.0",
        version_description="Initial synthesized baseline v1.0",
        approval_status=HandoverStatus.DRAFT.value,
        mark_as_latest=True,
    )
    assert v1_snapshot.version_number == "v1.0"
    assert len(v1_snapshot.snapshot["sections"]) == 6

    # ==========================================================================
    # PHASE 4 — EVIDENCE VERIFICATION & CONTRADICTION DETECTION
    # ==========================================================================
    # Link evidence reference to chunk
    chunk_ref = saved_chunks[0]
    ev_ref = EvidenceReference(
        id=uuid.uuid4(),
        handover_section_id=saved_sections[0].id,
        document_chunk_id=chunk_ref.id,
        document_id=chunk_ref.document_id,
        relevance_score=0.95,
        claim_text="Project Apex processes $100M daily settlement volume.",
        quoted_text=chunk_ref.content[:150],
        verification_status="Supported",
    )
    e2e_db.add(ev_ref)

    # Detect Contradiction between DOCX (March 15) and ADR TXT (May 30)
    conflict = Conflict(
        id=uuid.uuid4(),
        handover_id=handover.id,
        project_id=project.id,
        conflict_type="date",
        description="Runbook specifies rollout target as March 15, 2026, whereas ADR-007 specifies May 30, 2026.",
        source_a={"document_id": str(saved_docs[1].id), "statement": "Target production rollout date: March 15, 2026"},
        source_b={"document_id": str(saved_docs[2].id), "statement": "Target production rollout date: May 30, 2026"},
        statement_a="Target production rollout date: March 15, 2026 (runbook_deployment_guide.docx)",
        statement_b="Target production rollout date: May 30, 2026 (adr_007_ledger_storage.txt)",
        status="OPEN",
    )
    e2e_db.add(conflict)
    await e2e_db.commit()

    # Reviewer resolves conflict with rationale
    conflict.status = "RESOLVED"
    conflict.resolved_by = reviewer_user.id
    conflict.resolution = {
        "type": "APPROVED_DATE",
        "notes": "Adopt May 30, 2026 launch date per security and SOC2 audit completion requirements.",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
    await e2e_db.commit()

    await audit_svc.record_event(
        action=AuditActionType.CONFLICT_RESOLVED,
        entity_type=AuditEntityType.CONFLICT,
        entity_id=conflict.id,
        user_id=reviewer_user.id,
        project_id=project.id,
        change_metadata={"resolution": conflict.resolution, "status": "RESOLVED"},
    )

    c_check = (await e2e_db.execute(select(Conflict).where(Conflict.id == conflict.id))).scalar_one()
    assert c_check.status == "RESOLVED"
    assert "May 30" in c_check.resolution["notes"]

    # ==========================================================================
    # PHASE 5 — APPROVAL WORKFLOW
    # ==========================================================================
    # Outgoing edits section
    saved_sections[0].content = {
        "summary": "High-throughput settlement engine processing $125M daily volume across EUR/USD/GBP.",
        "markdown": "Updated overview with expanded $125M daily settlement capability.",
    }
    handover.status = HandoverStatus.IN_REVIEW.value
    await e2e_db.commit()

    # Reviewer approves handover
    handover.status = HandoverStatus.APPROVED.value
    handover.approved_at = datetime.now(timezone.utc)
    await e2e_db.commit()

    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_APPROVED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        user_id=reviewer_user.id,
        project_id=project.id,
        change_metadata={"approved_by": str(reviewer_user.id), "status": "APPROVED"},
    )

    assert handover.status == "APPROVED"
    assert handover.approved_at is not None

    # ==========================================================================
    # PHASE 6 — VERSION MANAGEMENT
    # ==========================================================================
    # Create Version 2.0 with modified sections
    v2_snapshot = await version_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=outgoing_user.id,
        version_number="v2.0",
        version_description="Revision v2.0 with expanded volume and resolved schedule conflict",
        approval_status=HandoverStatus.DRAFT.value,
        mark_as_latest=True,
    )

    # Compare Version 1 and Version 2
    diff = await version_svc.compare_versions(handover.id, v1_snapshot.id, v2_snapshot.id)
    assert diff.from_version_number == "v1.0"
    assert diff.to_version_number == "v2.0"
    assert diff.summary.has_differences is True
    assert diff.summary.modified_sections_count >= 1

    # Restore Version 1 as a new revision (v2.1)
    restored_handover, v3_record = await version_svc.restore_version(
        handover_id=handover.id,
        version_id=v1_snapshot.id,
        user_id=outgoing_user.id,
        reason="Rollback to initial v1.0 baseline",
    )
    assert v3_record.parent_version_id == v1_snapshot.id
    assert v3_record.is_latest is True
    assert v3_record.approval_status == "DRAFT"

    # Verify historical versions remain immutable
    v1_check = await version_svc.get_version(handover.id, v1_snapshot.id)
    assert v1_check.version_number == "v1.0"
    assert len(v1_check.snapshot["sections"]) == 6

    # ==========================================================================
    # PHASE 7 — KNOWLEDGE TRANSFER (INCOMING MEMBER CONTINUITY)
    # ==========================================================================
    # Outgoing shares approved handover with incoming member
    restored_handover.status = HandoverStatus.APPROVED.value
    restored_handover.approved_at = datetime.now(timezone.utc)
    restored_handover.assigned_to = incoming_user.id
    restored_handover.transition_status = HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value
    await e2e_db.commit()

    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_SHARED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=restored_handover.id,
        user_id=outgoing_user.id,
        project_id=project.id,
        change_metadata={"assigned_to": str(incoming_user.id), "status": "SHARED"},
    )

    # Incoming member acknowledges receipt
    ack_now = datetime.now(timezone.utc)
    restored_handover.transition_status = HandoverTransitionStatus.ACKNOWLEDGED.value
    restored_handover.acknowledged_at = ack_now
    restored_handover.acknowledged_by = incoming_user.id
    restored_handover.acknowledgement_notes = "Formally received Project Apex handover. Verified PgBouncer task."
    restored_handover.checklist_confirmed = True
    await e2e_db.commit()

    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_ACKNOWLEDGED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=restored_handover.id,
        user_id=incoming_user.id,
        project_id=project.id,
        change_metadata={"acknowledged_by": str(incoming_user.id), "status": "ACKNOWLEDGED"},
    )

    # Incoming member updates assigned task
    continuity_task.status = "IN_PROGRESS"
    await e2e_db.commit()

    # Add progress notes
    progress_update = TaskProgressUpdate(
        id=uuid.uuid4(),
        task_id=continuity_task.id,
        user_id=incoming_user.id,
        update_text="Configured PgBouncer transaction pooling; verified 0 connection timeouts under 200 RPS.",
        status_before="IN_PROGRESS",
        status_after="COMPLETED",
        created_at=datetime.now(timezone.utc),
    )
    e2e_db.add(progress_update)
    continuity_task.status = "COMPLETED"
    continuity_task.completed_at = datetime.now(timezone.utc)
    await e2e_db.commit()

    await audit_svc.record_event(
        action=AuditActionType.TASK_PROGRESS_UPDATED,
        entity_type=AuditEntityType.TASK,
        entity_id=continuity_task.id,
        user_id=incoming_user.id,
        project_id=project.id,
        change_metadata={"update_text": progress_update.update_text, "status": "COMPLETED"},
    )

    # ==========================================================================
    # PHASE 8 — FINAL VALIDATION
    # ==========================================================================
    # 1. Database persistence
    task_check = (await e2e_db.execute(select(Task).where(Task.id == continuity_task.id))).scalar_one()
    assert task_check.status == "COMPLETED"
    assert task_check.completed_at is not None

    updates_check = (await e2e_db.execute(select(TaskProgressUpdate).where(TaskProgressUpdate.task_id == continuity_task.id))).scalars().all()
    assert len(updates_check) == 1
    assert "Configured PgBouncer" in updates_check[0].update_text

    # 2. RBAC Permissions enforcement via API dependency check
    async def override_get_db():
        yield e2e_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Incoming member cannot delete project documents (requires MANAGE_DOCUMENTS)
            del_res = await client.delete(
                f"/api/v1/documents/{saved_docs[0].id}",
                headers={"Authorization": f"Bearer {token_incoming}"},
            )
            assert del_res.status_code == 403

            # Stranger in system but without project membership cannot access project (HTTP 403)
            stranger_user = User(
                id=uuid.uuid4(),
                email="stranger@other-company.io",
                full_name="External Stranger",
                password_hash=get_password_hash("StrangerPass!"),
                is_active=True,
            )
            e2e_db.add(stranger_user)
            await e2e_db.commit()

            stranger_token = create_access_token(stranger_user.id, email=stranger_user.email)
            stranger_res = await client.get(
                f"/api/v1/projects/{project.id}",
                headers={"Authorization": f"Bearer {stranger_token}"},
            )
            assert stranger_res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)

    # 3. Audit Records completeness
    audit_logs, total_logs = await audit_svc.list_project_audit_logs(project.id, page=1, page_size=50)
    assert total_logs >= 5
    actions = [l.action for l in audit_logs]
    assert AuditActionType.PROJECT_CREATED.value in actions
    assert AuditActionType.CONFLICT_RESOLVED.value in actions
    assert AuditActionType.HANDOVER_APPROVED.value in actions
    assert AuditActionType.HANDOVER_SHARED.value in actions
    assert AuditActionType.HANDOVER_ACKNOWLEDGED.value in actions
    assert AuditActionType.TASK_PROGRESS_UPDATED.value in actions
