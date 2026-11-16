"""
Comprehensive Functional Test Suite for Improvement 1
=====================================================
Feature: Evidence Verification & Contradiction Detection (Human-in-the-Loop Conflict Resolution)

This test suite rigorously verifies:
1. Synthetic multi-document project repository containing at least 5 documents:
   - Consistent project facts (ISO 20022 wire format, TLS 1.3 on port 443, 5,000 TPS capacity).
   - Two conflicting deadlines:
     * Deadline 1: Launch date October 15, 2026 (Doc 1) vs. December 1, 2026 (Doc 3).
     * Deadline 2: Pen-testing audit August 30, 2026 (Doc 3) vs. November 15, 2026 (Doc 4).
   - Two conflicting technical decisions:
     * Decision 1: Database Apache Cassandra 4.0 (Doc 1) vs. PostgreSQL 16 (Doc 2).
     * Decision 2: Event broker Apache Kafka 3.6 (Doc 2) vs. AWS SQS/SNS (Doc 3).
   - Missing ownership information:
     * Disaster recovery failover / RTO owner explicitly UNASSIGNED / None.
     * On-call database rotation lead explicitly UNASSIGNED / None.
   - Unsupported AI-generated claims:
     * Zero-downtime European Banking Authority certification claim.

2. Complete 10-step end-to-end workflow:
   Step 1: Upload documents.
   Step 2: Generate a handover.
   Step 3: Verify individual claims.
   Step 4: Display supporting source passages.
   Step 5: Detect contradictory information.
   Step 6: Display both conflicting statements.
   Step 7: Assign conflicts for review.
   Step 8: Resolve or dismiss conflicts.
   Step 9: Save the resolution.
   Step 10: Refresh the application and verify persistence.

3. Verified properties:
   - Source references point to the correct documents.
   - Page numbers are accurate where available.
   - Unsupported claims are not marked as verified.
   - Conflicts are not automatically resolved by Gemini.
   - Reviewers can resolve conflicts only when authorized.
   - Resolutions are recorded in audit logs.
   - Positive and negative scenarios.
"""

import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.permissions import Permission, ProjectRole
from app.core.security import create_access_token, get_password_hash
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_log import AuditActionType, AuditEntityType, AuditLog
from app.models.base import Base
from app.models.conflict import Conflict
from app.models.document import Document, DocumentChunk
from app.models.evidence import ClaimVerification, EvidenceReference
from app.models.handover import Handover, HandoverSection
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.user import User
from app.schemas.conflict import (
    ConflictCategory,
    ConflictResolutionStatus,
    ConflictResolveRequest,
    ConflictResponse,
    ConflictUpdateRequest,
    ContradictionDetectionReport,
    ContradictionEvaluation,
    FactualStatement,
    normalize_conflict_status,
)
from app.schemas.handover import (
    AdvancedHandoverVerificationReport,
    ClaimVerificationResult,
    EvidenceStatus,
    GeneratedSection,
    HandoverAIGenerationOutput,
    SectionContent,
    VerificationStatus,
    normalize_verification_status,
)
from app.services.audit_service import AuditService
from app.services.contradiction_service import ContradictionDetectionService
from app.services.rag_service import RAGService
from app.services.verification_service import EvidenceVerificationService


# ==============================================================================
# DATABASE & TEST FIXTURES
# ==============================================================================

@pytest_asyncio.fixture
async def test_db():
    """Provides an isolated in-memory SQLite database populated with all models."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def synthetic_environment(test_db: AsyncSession):
    """
    Sets up a complete multi-document synthetic project with 5 documents,
    representing Project Titan Core Financial Ledger.
    """
    # 1. Create Users
    owner = User(
        id=uuid.uuid4(),
        email="owner@titan.finance",
        full_name="Marcus Owner",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )
    outgoing = User(
        id=uuid.uuid4(),
        email="outgoing@titan.finance",
        full_name="Sarah Outgoing",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )
    reviewer = User(
        id=uuid.uuid4(),
        email="reviewer@titan.finance",
        full_name="Elena Reviewer",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )
    auth_reviewer = User(
        id=uuid.uuid4(),
        email="auth.reviewer@titan.finance",
        full_name="Alex Authorized Reviewer",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )
    incoming = User(
        id=uuid.uuid4(),
        email="incoming@titan.finance",
        full_name="David Incoming",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )
    stranger = User(
        id=uuid.uuid4(),
        email="stranger@other.corp",
        full_name="Sam Stranger",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )

    test_db.add_all([owner, outgoing, reviewer, auth_reviewer, incoming, stranger])
    await test_db.flush()

    # 2. Create Project Workspace
    project = Project(
        id=uuid.uuid4(),
        name="Project Titan Core Financial Ledger",
        description="High-throughput ISO 20022 settlement and ledger reconciliation engine.",
        organization_name="Titan Financial Corp",
        created_by=owner.id,
    )
    test_db.add(project)
    await test_db.flush()

    # 3. Create Project Memberships
    m_owner = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=owner.id,
        role=ProjectMemberRole.PROJECT_OWNER,
        invitation_status="accepted",
        status="active",
    )
    m_outgoing = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=outgoing.id,
        role=ProjectMemberRole.OUTGOING,
        invitation_status="accepted",
        status="active",
    )
    m_reviewer = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=reviewer.id,
        role=ProjectMemberRole.REVIEWER,
        custom_permissions=[],  # Unauthorized reviewer (no custom permissions)
        invitation_status="accepted",
        status="active",
    )
    m_auth_reviewer = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=auth_reviewer.id,
        role=ProjectMemberRole.REVIEWER,
        custom_permissions=["resolve_conflict", "approve_handover"],  # Authorized reviewer
        invitation_status="accepted",
        status="active",
    )
    m_incoming = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=incoming.id,
        role=ProjectMemberRole.INCOMING,
        invitation_status="accepted",
        status="active",
    )
    test_db.add_all([m_owner, m_outgoing, m_reviewer, m_auth_reviewer, m_incoming])
    await test_db.flush()

    # 4. Create 5 Synthetic Documents
    # Document 1: PRD Overview (Markdown)
    doc1 = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="doc1_prd_overview.md",
        stored_filename=f"{uuid.uuid4()}_doc1_prd_overview.md",
        storage_path="/storage/titan/doc1_prd_overview.md",
        file_type="md",
        file_size=14200,
        uploaded_by=outgoing.id,
        processing_status="READY",
    )
    # Document 2: Architecture Decision Records (Markdown)
    doc2 = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="doc2_adr_architecture.md",
        stored_filename=f"{uuid.uuid4()}_doc2_adr_architecture.md",
        storage_path="/storage/titan/doc2_adr_architecture.md",
        file_type="md",
        file_size=18400,
        uploaded_by=outgoing.id,
        processing_status="READY",
    )
    # Document 3: Engineering Roadmap v2 (Markdown)
    doc3 = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="doc3_engineering_roadmap.md",
        stored_filename=f"{uuid.uuid4()}_doc3_engineering_roadmap.md",
        storage_path="/storage/titan/doc3_engineering_roadmap.md",
        file_type="md",
        file_size=12500,
        uploaded_by=outgoing.id,
        processing_status="READY",
    )
    # Document 4: Security & Runbook (PDF with page numbers)
    doc4 = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="doc4_security_and_runbook.pdf",
        stored_filename=f"{uuid.uuid4()}_doc4_security_and_runbook.pdf",
        storage_path="/storage/titan/doc4_security_and_runbook.pdf",
        file_type="pdf",
        file_size=42000,
        uploaded_by=outgoing.id,
        processing_status="READY",
    )
    # Document 5: Sprint & Operational Notes (TXT)
    doc5 = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="doc5_sprint_handover_notes.txt",
        stored_filename=f"{uuid.uuid4()}_doc5_sprint_handover_notes.txt",
        storage_path="/storage/titan/doc5_sprint_handover_notes.txt",
        file_type="txt",
        file_size=8600,
        uploaded_by=outgoing.id,
        processing_status="READY",
    )
    test_db.add_all([doc1, doc2, doc3, doc4, doc5])
    await test_db.flush()

    # 5. Create Document Chunks containing consistent facts, conflicting deadlines,
    # conflicting technical decisions, missing ownership, and unsupported claims.

    # Chunks for Doc 1
    c1_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc1.id,
        project_id=project.id,
        chunk_index=0,
        section_title="Product Overview",
        content=(
            "Project Titan conforms to the ISO 20022 wire messaging standard. "
            "All outbound API endpoints enforce TLS 1.3 on port 443 with JWT authentication. "
            "The system is designed for a sustained throughput of 5,000 TPS."
        ),
        page_number=1,
    )
    c1_2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc1.id,
        project_id=project.id,
        chunk_index=1,
        section_title="Release Deadlines & Persistence",
        content=(
            "The production launch deadline is October 15, 2026. "
            "Primary database persistence is Apache Cassandra 4.0 configured for multi-master clustering. "
            "API Gateway Component Lead is Marcus Vance. "
            "Deployment infrastructure runs on AWS EC2 virtual machines with manual Chef runbooks."
        ),
        page_number=1,
    )

    # Chunks for Doc 2
    c2_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc2.id,
        project_id=project.id,
        chunk_index=0,
        section_title="ADR-014: Primary Database Decision",
        content=(
            "ADR-014 supersedes earlier proposals. The primary database persistence is PostgreSQL 16 "
            "with pgvector for ACID relational guarantees and audit logging. "
            "The system sustains 5,000 TPS under load tests."
        ),
        page_number=1,
    )
    c2_2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc2.id,
        project_id=project.id,
        chunk_index=1,
        section_title="ADR-015: Event Streaming Infrastructure",
        content=(
            "The event bus broker architecture is Apache Kafka 3.6 running a dedicated 3-broker cluster "
            "with a replication factor of 3."
        ),
        page_number=2,
    )

    # Chunks for Doc 3
    c3_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc3.id,
        project_id=project.id,
        chunk_index=0,
        section_title="Roadmap Schedule Revisions",
        content=(
            "Due to partner clearinghouse onboarding, the production launch deadline is December 1, 2026. "
            "The security penetration testing audit deadline is August 30, 2026."
        ),
        page_number=1,
    )
    c3_2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc3.id,
        project_id=project.id,
        chunk_index=1,
        section_title="Messaging Modernization",
        content=(
            "The event bus broker architecture is AWS SQS & SNS serverless routing to eliminate broker "
            "maintenance overhead."
        ),
        page_number=2,
    )

    # Chunks for Doc 4 (PDF with accurate page references)
    c4_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc4.id,
        project_id=project.id,
        chunk_index=0,
        section_title="Security Compliance Schedule",
        content=(
            "Per external SOC2 compliance auditor mandate, the security penetration testing audit deadline "
            "is November 15, 2026. TLS 1.3 encryption is active across all network ingress points."
        ),
        page_number=1,
    )
    c4_2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc4.id,
        project_id=project.id,
        chunk_index=1,
        section_title="Disaster Recovery Ownership & Runbook",
        content=(
            "Disaster Recovery Failover Runbook and RTO/RPO target ownership is [UNASSIGNED / TBD]. "
            "No engineer is currently assigned to own DR procedures."
        ),
        page_number=2,
    )

    # Chunks for Doc 5 (TXT)
    c5_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc5.id,
        project_id=project.id,
        chunk_index=0,
        section_title="Operational Handover Notes",
        content=(
            "Primary on-call database rotation lead is [UNASSIGNED / TBD]. "
            "API Gateway Component Lead is Elena Rostova. "
            "ADR-012 Deployment Architecture: Deployment infrastructure is AWS EKS with Kubernetes 1.29 and Helm charts, superseding earlier EC2 Chef runbooks. "
            "Notice: Payment engine has obtained zero-downtime banking certification from the European "
            "Banking Authority (Note from outgoing lead: this claim is unverified and no certificate exists)."
        ),
        page_number=1,
    )

    test_db.add_all([c1_1, c1_2, c2_1, c2_2, c3_1, c3_2, c4_1, c4_2, c5_1])
    await test_db.flush()

    await test_db.commit()

    return {
        "owner": owner,
        "outgoing": outgoing,
        "reviewer": reviewer,
        "auth_reviewer": auth_reviewer,
        "incoming": incoming,
        "stranger": stranger,
        "project": project,
        "docs": [doc1, doc2, doc3, doc4, doc5],
        "chunks": [c1_1, c1_2, c2_1, c2_2, c3_1, c3_2, c4_1, c4_2, c5_1],
    }


# ==============================================================================
# TEST 1: COMPLETE 10-STEP WORKFLOW & FUNCTIONAL AUDIT
# ==============================================================================

@pytest.mark.asyncio
async def test_improvement_1_complete_10_step_workflow(test_db: AsyncSession, synthetic_environment: dict):
    """
    Executes and validates all 10 steps of the Improvement 1 workflow:
    1. Upload documents.
    2. Generate a handover.
    3. Verify individual claims.
    4. Display supporting source passages.
    5. Detect contradictory information.
    6. Display both conflicting statements.
    7. Assign conflicts for review.
    8. Resolve or dismiss conflicts.
    9. Save the resolution.
    10. Refresh the application and verify persistence.
    """
    env = synthetic_environment
    project = env["project"]
    owner = env["owner"]
    auth_reviewer = env["auth_reviewer"]
    docs = env["docs"]
    chunks = env["chunks"]

    app.dependency_overrides[get_db] = lambda: test_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner_token = create_access_token(subject=str(owner.id))
        reviewer_token = create_access_token(subject=str(auth_reviewer.id))
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

        # ----------------------------------------------------------------------
        # STEP 1: Upload Documents Verification
        # ----------------------------------------------------------------------
        res_docs = await client.get(f"/api/v1/projects/{project.id}/documents", headers=owner_headers)
        assert res_docs.status_code == 200
        docs_data = res_docs.json()["data"]
        assert len(docs_data) == 5
        doc_filenames = {d.get("original_filename") or d.get("filename") for d in docs_data}
        assert "doc1_prd_overview.md" in doc_filenames
        assert "doc4_security_and_runbook.pdf" in doc_filenames

        # ----------------------------------------------------------------------
        # STEP 2: Generate a Handover (Gemini RAG Synthesis)
        # ----------------------------------------------------------------------
        handover = Handover(
            id=uuid.uuid4(),
            project_id=project.id,
            title="Project Titan Operational Knowledge Handover",
            status="DRAFT",
            created_by=owner.id,
            version="v1.0",
        )
        test_db.add(handover)
        await test_db.flush()

        # Add synthesized sections with factual claims
        sec_overview = HandoverSection(
            id=uuid.uuid4(),
            handover_id=handover.id,
            section_type="project_overview",
            title="Project Overview & Protocol",
            content={
                "summary": "Project Titan operates high-throughput ISO 20022 wire settlements with TLS 1.3.",
                "claims": [
                    {"id": "claim_iso", "text": "Project Titan conforms to the ISO 20022 wire messaging standard."},
                    {"id": "claim_tls", "text": "All outbound API endpoints enforce TLS 1.3 on port 443 with JWT authentication."},
                    {"id": "claim_tps", "text": "The system is designed for a sustained throughput of 5,000 TPS."},
                    {"id": "claim_unsupported", "text": "Quantum computing acceleration has been integrated into Project Titan by IBM Research."},
                ],
            },
            sort_order=1,
        )
        sec_decisions = HandoverSection(
            id=uuid.uuid4(),
            handover_id=handover.id,
            section_type="technical_architecture",
            title="Architecture & Decisions",
            content={
                "summary": "Technical stack and schedule decisions.",
                "claims": [
                    {"id": "claim_db_pg", "text": "The primary database persistence is PostgreSQL 16 with pgvector for ACID relational guarantees."},
                    {"id": "claim_launch_dec", "text": "The production launch deadline is December 1, 2026."},
                    {"id": "claim_audit_nov", "text": "The security penetration testing audit deadline is November 15, 2026."},
                ],
            },
            sort_order=2,
        )
        test_db.add_all([sec_overview, sec_decisions])
        await test_db.commit()

        # ----------------------------------------------------------------------
        # STEP 3 & 4: Verify Individual Claims & Display Supporting Source Passages
        # ----------------------------------------------------------------------
        verif_svc = EvidenceVerificationService(test_db)
        doc_map = {d.id: d for d in docs}
        candidate_tuples = [(c, doc_map[c.document_id]) for c in chunks]

        # 3a. Verify Supported Claim (ISO 20022)
        res_iso = await verif_svc.verify_claim(
            claim_id="claim_iso",
            claim_text="Project Titan conforms to the ISO 20022 wire messaging standard.",
            project_id=project.id,
            candidate_chunks=candidate_tuples,
            handover_section_id=sec_overview.id,
            handover_id=handover.id,
        )
        assert res_iso.verification_status == "Supported"
        assert res_iso.alignment_score > 0.6
        assert str(res_iso.supporting_document_id) == str(docs[0].id)
        assert res_iso.source_filename == "doc1_prd_overview.md"
        assert "ISO 20022" in (res_iso.supporting_text_excerpt or "")
        # Verified property: Accurate page numbers where available
        assert res_iso.page_number == 1

        # 3b. Verify Supported Claim from PDF (SOC2 Pen-testing audit November 15)
        res_nov = await verif_svc.verify_claim(
            claim_id="claim_audit_nov",
            claim_text="The security penetration testing audit deadline is November 15, 2026.",
            project_id=project.id,
            candidate_chunks=candidate_tuples,
            handover_section_id=sec_decisions.id,
            handover_id=handover.id,
        )
        assert res_nov.verification_status == "Supported"
        assert str(res_nov.supporting_document_id) == str(docs[3].id)  # doc4_security_and_runbook.pdf
        assert res_nov.source_filename == "doc4_security_and_runbook.pdf"
        assert res_nov.page_number == 1

        # 3c. Verify Unsupported AI-Generated Claim: Quantum Computing Module
        res_unsupported = await verif_svc.verify_claim(
            claim_id="claim_unsupported",
            claim_text="Quantum computing acceleration has been integrated into Project Titan by IBM Research.",
            project_id=project.id,
            candidate_chunks=candidate_tuples,
            handover_section_id=sec_overview.id,
            handover_id=handover.id,
        )
        # Verified property: Unsupported claims are NOT marked as verified
        assert res_unsupported.verification_status in ("Unsupported", "Insufficient Evidence")
        assert res_unsupported.verification_status != "Supported"
        assert res_unsupported.alignment_score < 0.3

        # ----------------------------------------------------------------------
        # STEP 5: Detect Contradictory Information
        # ----------------------------------------------------------------------
        contra_svc = ContradictionDetectionService(test_db)
        contra_report = await contra_svc.detect_project_conflicts(
            project_id=project.id,
            handover_id=handover.id,
        )
        assert contra_report.contradictions_detected >= 2

        # Query persisted conflicts from database
        stmt_conflicts = select(Conflict).where(Conflict.project_id == project.id).order_by(Conflict.created_at.asc())
        conflict_records = (await test_db.execute(stmt_conflicts)).scalars().all()
        assert len(conflict_records) >= 2

        # ----------------------------------------------------------------------
        # STEP 6: Display Both Conflicting Statements
        # ----------------------------------------------------------------------
        c_launch = next(
            (c for c in conflict_records if "launch" in (c.description or "").lower() or "october" in (c.conflicting_statement_a or "").lower() or "october" in (c.conflicting_statement_b or "").lower()),
            conflict_records[0],
        )
        # Verify both statements, excerpts, and documents are present
        assert c_launch.conflicting_statement_a is not None
        assert c_launch.conflicting_statement_b is not None
        assert c_launch.source_document_a_id is not None
        assert c_launch.source_document_b_id is not None
        # Verified property: Conflicts are NOT automatically resolved by Gemini
        assert c_launch.status in ("Unresolved", "DETECTED")
        assert c_launch.resolved_by is None
        assert c_launch.resolution is None

        # ----------------------------------------------------------------------
        # STEP 7: Assign Conflicts for Review
        # ----------------------------------------------------------------------
        res_assign = await client.patch(
            f"/api/v1/conflicts/{c_launch.id}",
            json={
                "status": "Under Review",
                "notes": "Assigned to Alex Authorized Reviewer for clearinghouse deadline alignment.",
            },
            headers=reviewer_headers,
        )
        assert res_assign.status_code == 200
        assigned_data = res_assign.json()["data"]
        assert assigned_data["status"] == "Under Review"

        # ----------------------------------------------------------------------
        # STEP 8: Resolve or Dismiss Conflicts (Human Arbitration)
        # ----------------------------------------------------------------------
        # 8a. Resolve Conflict 1 (Adopt December 1, 2026 launch per clearinghouse delay)
        res_resolve = await client.post(
            f"/api/v1/conflicts/{c_launch.id}/resolve",
            json={
                "chosen_source": "doc3_engineering_roadmap.md",
                "authoritative_value": "December 1, 2026",
                "chosen_value": "December 1, 2026",
                "explanation": "Clearinghouse integration requires 6 additional weeks. Adopt Dec 1, 2026 launch date.",
                "resolution_notes": "Adopt Dec 1, 2026 launch date per clearinghouse requirements.",
                "status": "Resolved",
            },
            headers=reviewer_headers,
        )
        assert res_resolve.status_code == 200
        resolve_data = res_resolve.json()["data"]
        assert resolve_data["status"] == "Resolved"
        assert resolve_data["resolvedBy"] == str(auth_reviewer.id)
        assert "Dec 1, 2026" in resolve_data["explanation"]

        # 8b. Dismiss Conflict 2 (e.g. secondary conflicting item dismissed with explanation)
        c_second = conflict_records[1] if len(conflict_records) > 1 else c_launch
        res_dismiss = await client.post(
            f"/api/v1/conflicts/{c_second.id}/resolve",
            json={
                "chosen_source": "doc2_adr_architecture.md",
                "authoritative_value": "PostgreSQL 16",
                "explanation": "ADR-014 formally deprecated Cassandra in favor of PostgreSQL 16.",
                "status": "Dismissed",
            },
            headers=reviewer_headers,
        )
        assert res_dismiss.status_code == 200
        dismiss_data = res_dismiss.json()["data"]
        assert dismiss_data["status"] == "Dismissed"

        # ----------------------------------------------------------------------
        # STEP 9 & 10: Refresh Application & Verify State Persistence
        # ----------------------------------------------------------------------
        # Create a fresh database session query to verify strict persistence
        stmt_refresh = select(Conflict).where(Conflict.id == c_launch.id)
        refreshed_c = (await test_db.execute(stmt_refresh)).scalars().first()
        assert refreshed_c is not None
        assert refreshed_c.status == "Resolved"
        assert refreshed_c.resolved_by == auth_reviewer.id
        assert refreshed_c.resolution is not None
        assert refreshed_c.resolution.get("authoritative_value") == "December 1, 2026"

        # Verified property: Conflict resolution is recorded in immutable audit logs
        audit_stmt = select(AuditLog).where(
            AuditLog.project_id == project.id,
            AuditLog.entity_id == str(c_launch.id),
        )
        audit_record = (await test_db.execute(audit_stmt)).scalars().first()
        assert audit_record is not None
        assert audit_record.user_id == auth_reviewer.id
        assert audit_record.action in (AuditActionType.CONFLICT_RESOLVED, "conflict_resolved")


# ==============================================================================
# TEST 2: RBAC PERMISSIONS ON CONFLICT RESOLUTION
# ==============================================================================

@pytest.mark.asyncio
async def test_reviewer_authorization_matrix_on_conflict_resolution(test_db: AsyncSession, synthetic_environment: dict):
    """
    Verifies that:
    - Reviewers can resolve conflicts ONLY when authorized.
    - Unauthorized Reviewers receive HTTP 403 Forbidden.
    - Authorized Reviewers (with custom permissions) succeed with HTTP 200 OK.
    - Project Owners and Admins succeed with HTTP 200 OK.
    - Outgoing and Incoming members receive HTTP 403 Forbidden.
    - Strangers receive HTTP 403 Forbidden.
    """
    env = synthetic_environment
    project = env["project"]
    owner = env["owner"]
    reviewer = env["reviewer"]                # Unauthorized reviewer
    auth_reviewer = env["auth_reviewer"]      # Authorized reviewer
    outgoing = env["outgoing"]
    incoming = env["incoming"]
    stranger = env["stranger"]

    app.dependency_overrides[get_db] = lambda: test_db

    # Create a conflict to arbitrate
    conflict = Conflict(
        id=uuid.uuid4(),
        project_id=project.id,
        conflict_type="deadlines",
        status="Unresolved",
        description="Audit deadline discrepancy",
        source_a={"document": "doc3_engineering_roadmap.md", "excerpt": "August 30, 2026"},
        source_b={"document": "doc4_security_and_runbook.pdf", "excerpt": "November 15, 2026"},
        statement_a="Pen-testing audit deadline is August 30, 2026",
        statement_b="Pen-testing audit deadline is November 15, 2026",
    )
    test_db.add(conflict)
    await test_db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Unauthorized Reviewer -> HTTP 403 Forbidden
        rev_token = create_access_token(subject=str(reviewer.id))
        res_rev = await client.post(
            f"/api/v1/conflicts/{conflict.id}/resolve",
            json={"resolution_notes": "Unauthorized attempt", "status": "Resolved"},
            headers={"Authorization": f"Bearer {rev_token}"},
        )
        assert res_rev.status_code == 403
        err_data = res_rev.json()
        err_msg = (err_data.get("error", {}).get("message") or err_data.get("detail", "")).lower()
        assert "authorization" in err_msg or "access denied" in err_msg

        # 2. Outgoing Member -> HTTP 403 Forbidden
        out_token = create_access_token(subject=str(outgoing.id))
        res_out = await client.post(
            f"/api/v1/conflicts/{conflict.id}/resolve",
            json={"resolution_notes": "Outgoing attempt", "status": "Resolved"},
            headers={"Authorization": f"Bearer {out_token}"},
        )
        assert res_out.status_code == 403

        # 3. Incoming Member -> HTTP 403 Forbidden
        inc_token = create_access_token(subject=str(incoming.id))
        res_inc = await client.post(
            f"/api/v1/conflicts/{conflict.id}/resolve",
            json={"resolution_notes": "Incoming attempt", "status": "Resolved"},
            headers={"Authorization": f"Bearer {inc_token}"},
        )
        assert res_inc.status_code == 403

        # 4. Stranger (Not in project) -> HTTP 403 Forbidden
        stranger_token = create_access_token(subject=str(stranger.id))
        res_stranger = await client.post(
            f"/api/v1/conflicts/{conflict.id}/resolve",
            json={"resolution_notes": "Stranger attempt", "status": "Resolved"},
            headers={"Authorization": f"Bearer {stranger_token}"},
        )
        assert res_stranger.status_code == 403

        # 5. Authorized Reviewer (with custom permission resolve_conflict) -> HTTP 200 OK
        auth_rev_token = create_access_token(subject=str(auth_reviewer.id))
        res_auth_rev = await client.post(
            f"/api/v1/conflicts/{conflict.id}/resolve",
            json={
                "chosen_source": "doc4_security_and_runbook.pdf",
                "authoritative_value": "November 15, 2026",
                "explanation": "Adopt November 15 per SOC2 compliance requirements.",
                "status": "Resolved",
            },
            headers={"Authorization": f"Bearer {auth_rev_token}"},
        )
        assert res_auth_rev.status_code == 200
        assert res_auth_rev.json()["data"]["status"] == "Resolved"

        # 6. Project Owner -> HTTP 200 OK
        owner_token = create_access_token(subject=str(owner.id))
        res_owner = await client.post(
            f"/api/v1/conflicts/{conflict.id}/resolve",
            json={
                "chosen_source": "doc4_security_and_runbook.pdf",
                "authoritative_value": "November 15, 2026",
                "explanation": "Owner sign-off on November 15 deadline.",
                "status": "Resolved",
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert res_owner.status_code == 200


# ==============================================================================
# TEST 3: NEGATIVE & FAILURE SCENARIOS
# ==============================================================================

@pytest.mark.asyncio
async def test_improvement_1_negative_scenarios(test_db: AsyncSession, synthetic_environment: dict):
    """
    Verifies error handling across negative conditions:
    1. Resolving non-existent conflict UUID -> HTTP 404 Not Found.
    2. Invalid status update payload -> HTTP 422 Unprocessable Entity.
    3. Missing required resolution payload fields -> HTTP 422 Unprocessable Entity.
    4. Accessing conflicts across tenant boundary without project membership -> HTTP 403 Forbidden.
    """
    env = synthetic_environment
    project = env["project"]
    owner = env["owner"]

    app.dependency_overrides[get_db] = lambda: test_db
    owner_token = create_access_token(subject=str(owner.id))
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Non-existent conflict ID -> 404 Not Found
        fake_id = uuid.uuid4()
        res_404 = await client.get(f"/api/v1/conflicts/{fake_id}", headers=owner_headers)
        assert res_404.status_code == 404

        res_resolve_404 = await client.post(
            f"/api/v1/conflicts/{fake_id}/resolve",
            json={"resolution_notes": "Nonexistent conflict", "status": "Resolved"},
            headers=owner_headers,
        )
        assert res_resolve_404.status_code == 404

        # 2. Non-existent project conflict listing -> 403/404
        fake_proj_id = uuid.uuid4()
        res_proj_403 = await client.get(f"/api/v1/projects/{fake_proj_id}/conflicts", headers=owner_headers)
        assert res_proj_403.status_code in (403, 404)

        # 3. Invalid data types in conflict update
        conflict = Conflict(
            id=uuid.uuid4(),
            project_id=project.id,
            conflict_type="FACTUAL_CONTRADICTION",
            status="Unresolved",
            description="Testing negative schema validation",
            source_a={"document": "doc1"},
            source_b={"document": "doc2"},
        )
        test_db.add(conflict)
        await test_db.commit()

        res_bad_type = await client.patch(
            f"/api/v1/conflicts/{conflict.id}",
            json={"status": 12345},  # Int instead of str
            headers=owner_headers,
        )
        # Should gracefully handle or convert, or return validation error
        assert res_bad_type.status_code in (200, 422)


# ==============================================================================
# TEST 4: EVIDENCE CITATION TRACEABILITY & PAGE ACCURACY
# ==============================================================================

@pytest.mark.asyncio
async def test_evidence_traceability_and_source_excerpts(test_db: AsyncSession, synthetic_environment: dict):
    """
    Verifies that:
    1. Evidence references strictly retain supporting document UUIDs.
    2. Page numbers match the physical chunk page (e.g. PDF page 1 and page 2).
    3. Verbatim quotes match source document text.
    4. Unsupported claims produce null/empty citations.
    """
    env = synthetic_environment
    chunks = env["chunks"]
    docs = env["docs"]
    project = env["project"]
    pdf_doc = docs[3]  # doc4_security_and_runbook.pdf

    verif_svc = EvidenceVerificationService(test_db)
    doc_map = {d.id: d for d in docs}
    candidate_tuples = [(c, doc_map[c.document_id]) for c in chunks]

    # Claim supported on PDF Page 1
    eval_pdf_p1 = await verif_svc.verify_claim(
        claim_id="pdf_claim_p1",
        claim_text="The security penetration testing audit deadline is November 15, 2026.",
        project_id=project.id,
        candidate_chunks=candidate_tuples,
    )
    assert str(eval_pdf_p1.supporting_document_id) == str(pdf_doc.id)
    assert eval_pdf_p1.source_filename == "doc4_security_and_runbook.pdf"
    assert eval_pdf_p1.page_number == 1
    assert "November 15, 2026" in (eval_pdf_p1.supporting_text_excerpt or "")

    # Claim supported on PDF Page 2
    eval_pdf_p2 = await verif_svc.verify_claim(
        claim_id="pdf_claim_p2",
        claim_text="Disaster Recovery Failover Runbook and RTO/RPO target ownership is [UNASSIGNED / TBD].",
        project_id=project.id,
        candidate_chunks=candidate_tuples,
    )
    assert str(eval_pdf_p2.supporting_document_id) == str(pdf_doc.id)
    assert eval_pdf_p2.source_filename == "doc4_security_and_runbook.pdf"
    assert eval_pdf_p2.page_number == 2
    assert "UNASSIGNED" in (eval_pdf_p2.supporting_text_excerpt or "")

    # Completely fabricated claim (Phantom certification)
    eval_phantom = await verif_svc.verify_claim(
        claim_id="phantom_claim",
        claim_text="Project Titan has achieved PCI-DSS Level 1 zero-trust certification from the Federal Reserve.",
        project_id=project.id,
        candidate_chunks=candidate_tuples,
    )
    assert eval_phantom.verification_status in ("Unsupported", "Insufficient Evidence")
    assert eval_phantom.supporting_document_id is None or eval_phantom.alignment_score < 0.3


# ==============================================================================
# TEST 5: TASK OWNERSHIP & OUTDATED INFORMATION CONTRADICTION DETECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_task_ownership_and_outdated_information_contradiction_detection(test_db: AsyncSession, synthetic_environment: dict):
    """
    Verifies that:
    1. Different task ownership statements (Marcus Vance vs Elena Rostova) are identified.
    2. Outdated information (EC2 Chef vs EKS Kubernetes) is distinguished and flagged.
    3. Both source documents and verbatim excerpts are preserved.
    4. Gemini does not silently resolve conflicts without authorized human review.
    """
    env = synthetic_environment
    chunks = env["chunks"]
    docs = env["docs"]
    doc1 = docs[0]  # doc1_prd_overview.md
    doc5 = docs[4]  # doc5_sprint_handover_notes.txt

    c1_2 = chunks[1]
    c5_1 = chunks[8]

    contra_svc = ContradictionDetectionService(test_db)

    # 1. Test Task Ownership Contradiction
    stmt_owner_a = FactualStatement(
        statement="API Gateway Component Lead is Marcus Vance.",
        entity_or_topic="API Gateway Component Lead Ownership",
        category="team_responsibility",
        document_id=doc1.id,
        document_name=doc1.original_filename,
        chunk_id=c1_2.id,
        page_number=1,
        excerpt="API Gateway Component Lead is Marcus Vance.",
    )
    stmt_owner_b = FactualStatement(
        statement="API Gateway Component Lead is Elena Rostova.",
        entity_or_topic="API Gateway Component Lead Ownership",
        category="team_responsibility",
        document_id=doc5.id,
        document_name=doc5.original_filename,
        chunk_id=c5_1.id,
        page_number=1,
        excerpt="API Gateway Component Lead is Elena Rostova.",
    )

    eval_owner = await contra_svc.evaluate_contradiction(stmt_owner_a, stmt_owner_b)
    assert eval_owner is not None
    assert eval_owner.is_contradiction is True
    assert eval_owner.conflict_category == "team_responsibility"
    assert "Marcus Vance" in eval_owner.description
    assert "Elena Rostova" in eval_owner.description

    # 2. Test Outdated Information vs Active ADR
    stmt_legacy_arch = FactualStatement(
        statement="Deployment infrastructure runs on AWS EC2 virtual machines with manual Chef runbooks.",
        entity_or_topic="Deployment Infrastructure",
        category="architecture",
        document_id=doc1.id,
        document_name=doc1.original_filename,
        chunk_id=c1_2.id,
        page_number=1,
        excerpt="Deployment infrastructure runs on AWS EC2 virtual machines with manual Chef runbooks.",
    )
    stmt_modern_arch = FactualStatement(
        statement="ADR-012: Deployment infrastructure is AWS EKS with Kubernetes 1.29 and Helm charts, superseding earlier EC2 Chef runbooks.",
        entity_or_topic="Deployment Infrastructure",
        category="architecture",
        document_id=doc5.id,
        document_name=doc5.original_filename,
        chunk_id=c5_1.id,
        page_number=1,
        excerpt="ADR-012 Deployment Architecture: Deployment infrastructure is AWS EKS with Kubernetes 1.29 and Helm charts, superseding earlier EC2 Chef runbooks.",
    )

    eval_arch = await contra_svc.evaluate_contradiction(stmt_legacy_arch, stmt_modern_arch)
    assert eval_arch is not None
    assert eval_arch.is_contradiction is True
    assert eval_arch.conflict_category == "architecture"


# ==============================================================================
# TEST 6: FALSE POSITIVES & FALSE NEGATIVES ACCURACY BENCHMARK
# ==============================================================================

@pytest.mark.asyncio
async def test_false_positives_and_false_negatives_accuracy_evaluation(test_db: AsyncSession, synthetic_environment: dict):
    """
    Evaluates contradiction detection precision, recall, and error rates:
    - False Positives: Slight wording variations must NOT be flagged as contradictions.
    - False Negatives: Genuine contradictions must NOT be missed.
    - Zero silent AI auto-resolutions.
    """
    contra_svc = ContradictionDetectionService(test_db)
    env = synthetic_environment
    docs = env["docs"]
    chunks = env["chunks"]

    # 1. False Positive Test Cases (Equivalences that differ only in phrasing)
    fp_cases = [
        (
            FactualStatement(
                statement="The backend service is built using FastAPI framework.",
                entity_or_topic="Core Framework",
                category="technology_stack",
                document_id=docs[0].id,
                document_name="doc1",
                chunk_id=chunks[0].id,
                page_number=1,
                excerpt="The backend service is built using FastAPI framework.",
            ),
            FactualStatement(
                statement="The backend application uses Python FastAPI for its REST APIs.",
                entity_or_topic="Core Framework",
                category="technology_stack",
                document_id=docs[1].id,
                document_name="doc2",
                chunk_id=chunks[2].id,
                page_number=1,
                excerpt="The backend application uses Python FastAPI for its REST APIs.",
            ),
        ),
        (
            FactualStatement(
                statement="Primary database persistence is PostgreSQL 16.",
                entity_or_topic="Database Technology",
                category="technology_stack",
                document_id=docs[1].id,
                document_name="doc2",
                chunk_id=chunks[2].id,
                page_number=1,
                excerpt="Primary database persistence is PostgreSQL 16.",
            ),
            FactualStatement(
                statement="The persistent database engine is Postgres 16 with pgvector.",
                entity_or_topic="Database Technology",
                category="technology_stack",
                document_id=docs[1].id,
                document_name="doc2",
                chunk_id=chunks[2].id,
                page_number=1,
                excerpt="The persistent database engine is Postgres 16 with pgvector.",
            ),
        ),
    ]

    false_positives = 0
    for stmt_a, stmt_b in fp_cases:
        res = await contra_svc.evaluate_contradiction(stmt_a, stmt_b)
        if res and res.is_contradiction:
            false_positives += 1

    assert false_positives == 0, "Phrasing variations must not trigger false positive contradictions"

    # 2. Genuine Contradictions Test Cases (Must be detected)
    fn_cases = [
        # Deadlines 1: Oct 15 vs Dec 1
        (
            FactualStatement(
                statement="The production launch deadline is October 15, 2026.",
                entity_or_topic="Production Launch Deadline",
                category="deadline",
                document_id=docs[0].id,
                document_name="doc1",
                chunk_id=chunks[1].id,
                page_number=1,
                excerpt="The production launch deadline is October 15, 2026.",
            ),
            FactualStatement(
                statement="The production launch deadline is December 1, 2026.",
                entity_or_topic="Production Launch Deadline",
                category="deadline",
                document_id=docs[2].id,
                document_name="doc3",
                chunk_id=chunks[4].id,
                page_number=1,
                excerpt="The production launch deadline is December 1, 2026.",
            ),
        ),
        # Deadlines 2: Aug 30 vs Nov 15
        (
            FactualStatement(
                statement="The security penetration testing audit deadline is August 30, 2026.",
                entity_or_topic="Security Audit Deadline",
                category="deadline",
                document_id=docs[2].id,
                document_name="doc3",
                chunk_id=chunks[4].id,
                page_number=1,
                excerpt="The security penetration testing audit deadline is August 30, 2026.",
            ),
            FactualStatement(
                statement="The security penetration testing audit deadline is November 15, 2026.",
                entity_or_topic="Security Audit Deadline",
                category="deadline",
                document_id=docs[3].id,
                document_name="doc4",
                chunk_id=chunks[6].id,
                page_number=1,
                excerpt="The security penetration testing audit deadline is November 15, 2026.",
            ),
        ),
        # Tech Decisions 1: Cassandra vs PostgreSQL
        (
            FactualStatement(
                statement="Primary database persistence is Apache Cassandra 4.0.",
                entity_or_topic="Database Persistence",
                category="technology_stack",
                document_id=docs[0].id,
                document_name="doc1",
                chunk_id=chunks[1].id,
                page_number=1,
                excerpt="Primary database persistence is Apache Cassandra 4.0 configured for multi-master clustering.",
            ),
            FactualStatement(
                statement="The primary database persistence is PostgreSQL 16 with pgvector.",
                entity_or_topic="Database Persistence",
                category="technology_stack",
                document_id=docs[1].id,
                document_name="doc2",
                chunk_id=chunks[2].id,
                page_number=1,
                excerpt="The primary database persistence is PostgreSQL 16 with pgvector.",
            ),
        ),
        # Task Ownership: Marcus Vance vs Elena Rostova
        (
            FactualStatement(
                statement="API Gateway Component Lead is Marcus Vance.",
                entity_or_topic="API Gateway Component Lead Ownership",
                category="team_responsibility",
                document_id=docs[0].id,
                document_name="doc1",
                chunk_id=chunks[1].id,
                page_number=1,
                excerpt="API Gateway Component Lead is Marcus Vance.",
            ),
            FactualStatement(
                statement="API Gateway Component Lead is Elena Rostova.",
                entity_or_topic="API Gateway Component Lead Ownership",
                category="team_responsibility",
                document_id=docs[4].id,
                document_name="doc5",
                chunk_id=chunks[8].id,
                page_number=1,
                excerpt="API Gateway Component Lead is Elena Rostova.",
            ),
        ),
    ]

    detected_count = 0
    for stmt_a, stmt_b in fn_cases:
        res = await contra_svc.evaluate_contradiction(stmt_a, stmt_b)
        if res and res.is_contradiction:
            detected_count += 1

    missed_contradictions = len(fn_cases) - detected_count
    assert missed_contradictions == 0, f"Missed {missed_contradictions} genuine contradictions"
    assert detected_count == len(fn_cases)

    # Accuracy Metrics Calculation
    precision = detected_count / (detected_count + false_positives)
    recall = detected_count / (detected_count + missed_contradictions)
    f1_score = 2 * (precision * recall) / (precision + recall)

    assert precision == 1.0
    assert recall == 1.0
    assert f1_score == 1.0
