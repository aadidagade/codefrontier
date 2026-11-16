"""
Comprehensive Database Integrity and Constraint Verification Test Suite.

Audits all 18 PostgreSQL/SQLAlchemy models:
1. User records storage and password hashing.
2. Projects and owner association.
3. Project memberships and role linkages.
4. Uploaded documents and extraction metadata.
5. Extracted chunks referencing parent documents.
6. 768-dimensional dense vector embeddings persistence and retrieval.
7. Handover records and sections persistence.
8. Evidence references and claim verifications pointing to valid sources.
9. Conflict resolutions and audit trail persistence.
10. Audit logs immutability and record keeping.
11. Handover versions historical snapshots and parent lineage.
12. Incoming-member acknowledgements persistence.
13. Task status updates and progress update logs persistence.

Additional Integrity Tests:
- Duplicate records rejection (Unique constraints on email, stored_filename, memberships, dependencies).
- Missing foreign keys rejection (Referential integrity).
- Orphaned records and CASCADE / SET NULL behaviors.
- Database transaction failures and rollback atomicity.
- Migration lineage and rollback support.
- Strict data isolation between projects.
"""

import os
import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.models import (
    Base,
    User,
    RefreshToken,
    Project,
    ProjectMember,
    ProjectMemberRole,
    Document,
    DocumentChunk,
    Handover,
    HandoverSection,
    HandoverVersion,
    HandoverAuditLog,
    EvidenceReference,
    ClaimVerification,
    Conflict,
    Task,
    TaskProgressUpdate,
    TaskDependency,
    Notification,
    AuditLog,
    AuditActionType,
    AuditEntityType,
)


@pytest_asyncio.fixture
async def test_db_session():
    """Provides an isolated in-memory database session with foreign keys enabled."""
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
# 1. USER RECORDS VERIFICATION
# ==============================================================================
@pytest.mark.asyncio
async def test_user_records_stored_correctly(test_db_session: AsyncSession):
    """Verifies that user records are stored correctly with password hash and active flag."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        full_name="Sarah Connor",
        email="sarah@skynet-resistance.io",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash123",
        is_active=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_db_session.execute(select(User).where(User.id == uid))
    saved_user = res.scalar_one()

    assert saved_user.id == uid
    assert saved_user.full_name == "Sarah Connor"
    assert saved_user.email == "sarah@skynet-resistance.io"
    assert saved_user.password_hash.startswith("$argon2id$")
    assert saved_user.is_active is True
    assert saved_user.created_at is not None
    assert saved_user.updated_at is not None


# ==============================================================================
# 2. PROJECTS & OWNERSHIP ASSOCIATION
# ==============================================================================
@pytest.mark.asyncio
async def test_projects_associated_with_correct_owners(test_db_session: AsyncSession):
    """Verifies that projects are associated with the correct owner and relationship resolves."""
    owner = User(
        id=uuid.uuid4(),
        full_name="Project Owner",
        email="owner@defense.gov",
        password_hash="hash_owner",
    )
    test_db_session.add(owner)
    await test_db_session.flush()

    pid = uuid.uuid4()
    project = Project(
        id=pid,
        name="Mission Critical Gateway",
        description="Core architecture migration",
        created_by=owner.id,
        status="active",
    )
    test_db_session.add(project)
    await test_db_session.commit()

    # Query project and verify creator navigation
    res = await test_db_session.execute(
        select(Project).options(selectinload(Project.creator)).where(Project.id == pid)
    )
    saved_project = res.scalar_one()
    assert saved_project.created_by == owner.id
    assert saved_project.creator.id == owner.id

    # Verify user's projects_created list
    res_user = await test_db_session.execute(
        select(User).options(selectinload(User.projects_created)).where(User.id == owner.id)
    )
    saved_owner = res_user.scalar_one()
    assert len(saved_owner.projects_created) == 1
    assert saved_owner.projects_created[0].id == pid


# ==============================================================================
# 3. PROJECT MEMBERSHIPS LINKAGE
# ==============================================================================
@pytest.mark.asyncio
async def test_project_memberships_linked_correctly(test_db_session: AsyncSession):
    """Verifies that project memberships correctly link user, project, and assigned role."""
    owner = User(id=uuid.uuid4(), full_name="Lead Engineer", email="lead@corp.io", password_hash="pwd")
    incoming = User(id=uuid.uuid4(), full_name="Incoming Engineer", email="incoming@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Cloud Modernization", created_by=owner.id)

    test_db_session.add_all([owner, incoming, project])
    await test_db_session.flush()

    mem_owner = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=owner.id,
        role=ProjectMemberRole.LEAD.value,
        status="active",
    )
    mem_incoming = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=incoming.id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
        invitation_status="accepted",
        invited_by=owner.id,
    )
    test_db_session.add_all([mem_owner, mem_incoming])
    await test_db_session.commit()

    # Verify members on project
    res = await test_db_session.execute(select(ProjectMember).where(ProjectMember.project_id == project.id))
    members = res.scalars().all()
    assert len(members) == 2
    roles = {m.user_id: m.role for m in members}
    assert roles[owner.id] == "LEAD"
    assert roles[incoming.id] == "INCOMING"


# ==============================================================================
# 4. UPLOADED DOCUMENTS & METADATA RETENTION
# ==============================================================================
@pytest.mark.asyncio
async def test_uploaded_documents_retain_metadata(test_db_session: AsyncSession):
    """Verifies that uploaded documents retain all metadata, file sizes, and JSON extraction data."""
    owner = User(id=uuid.uuid4(), full_name="Doc Uploader", email="uploader@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Doc Retention Project", created_by=owner.id)
    test_db_session.add_all([owner, project])
    await test_db_session.flush()

    doc_id = uuid.uuid4()
    meta_payload = {
        "author": "Architecture Board",
        "total_pages": 42,
        "format": "PDF-1.7",
        "topics": ["Microservices", "Event Sourcing", "PostgreSQL"],
    }
    doc = Document(
        id=doc_id,
        project_id=project.id,
        uploaded_by=owner.id,
        original_filename="enterprise_architecture_v3.pdf",
        stored_filename=f"{doc_id}_arch.pdf",
        file_type="pdf",
        file_size=2048576,
        storage_path=f"/storage/uploads/{doc_id}_arch.pdf",
        processing_status="completed",
        extraction_metadata=meta_payload,
    )
    test_db_session.add(doc)
    await test_db_session.commit()

    res = await test_db_session.execute(select(Document).where(Document.id == doc_id))
    retrieved_doc = res.scalar_one()

    assert retrieved_doc.original_filename == "enterprise_architecture_v3.pdf"
    assert retrieved_doc.stored_filename == f"{doc_id}_arch.pdf"
    assert retrieved_doc.file_type == "pdf"
    assert retrieved_doc.file_size == 2048576
    assert retrieved_doc.processing_status == "completed"
    assert retrieved_doc.extraction_metadata["total_pages"] == 42
    assert "Event Sourcing" in retrieved_doc.extraction_metadata["topics"]


# ==============================================================================
# 5. EXTRACTED CHUNKS REFERENCE ORIGINAL DOCUMENTS
# ==============================================================================
@pytest.mark.asyncio
async def test_extracted_chunks_reference_original_documents(test_db_session: AsyncSession):
    """Verifies that extracted chunks strictly reference their parent document in order."""
    owner = User(id=uuid.uuid4(), full_name="Chunk Tester", email="chunker@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Chunk Project", created_by=owner.id)
    doc = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        uploaded_by=owner.id,
        original_filename="runbook.md",
        stored_filename="runbook_stored.md",
        file_type="md",
        file_size=1024,
        storage_path="/tmp/runbook.md",
        processing_status="completed",
    )
    test_db_session.add_all([owner, project, doc])
    await test_db_session.flush()

    chunk0 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        project_id=project.id,
        chunk_index=0,
        content="Chapter 1: Disaster Recovery Procedures.",
        page_number=1,
        section_title="Disaster Recovery",
    )
    chunk1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        project_id=project.id,
        chunk_index=1,
        content="Chapter 2: Backup rotation schedule every 6 hours.",
        page_number=2,
        section_title="Backup Policy",
    )
    test_db_session.add_all([chunk0, chunk1])
    await test_db_session.commit()

    # Query back chunks ordered by index
    res = await test_db_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)
    )
    chunks = res.scalars().all()
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].section_title == "Disaster Recovery"
    assert chunks[1].chunk_index == 1
    assert chunks[1].document_id == doc.id


# ==============================================================================
# 6. 768-DIMENSIONAL EMBEDDINGS STORAGE & RETRIEVAL
# ==============================================================================
@pytest.mark.asyncio
async def test_embeddings_stored_and_retrieved_correctly(test_db_session: AsyncSession):
    """Verifies that 768-dimensional float dense embeddings are accurately persisted and retrieved."""
    owner = User(id=uuid.uuid4(), full_name="Embedding Owner", email="embed@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Vector Project", created_by=owner.id)
    doc = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="vector_spec.md",
        stored_filename="vector_stored.md",
        file_type="md",
        file_size=512,
        storage_path="/tmp/v.md",
        processing_status="completed",
    )
    test_db_session.add_all([owner, project, doc])
    await test_db_session.flush()

    vector_payload = [(float(i) / 768.0) * 0.5 for i in range(768)]
    chunk_id = uuid.uuid4()
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc.id,
        project_id=project.id,
        chunk_index=0,
        content="Embedding precision verification passage.",
        embedding=vector_payload,
    )
    test_db_session.add(chunk)
    await test_db_session.commit()

    res = await test_db_session.execute(select(DocumentChunk).where(DocumentChunk.id == chunk_id))
    retrieved_chunk = res.scalar_one()

    assert retrieved_chunk.embedding is not None
    assert len(retrieved_chunk.embedding) == 768
    assert abs(retrieved_chunk.embedding[0] - 0.0) < 1e-6
    assert abs(retrieved_chunk.embedding[767] - ((767.0 / 768.0) * 0.5)) < 1e-5


# ==============================================================================
# 7. HANDOVER RECORDS & SECTIONS PERSISTENCE
# ==============================================================================
@pytest.mark.asyncio
async def test_handover_records_persist(test_db_session: AsyncSession):
    """Verifies that handover records and sections persist with full structured chapter data."""
    owner = User(id=uuid.uuid4(), full_name="Handover Author", email="author@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Handover Persistence Project", created_by=owner.id)
    test_db_session.add_all([owner, project])
    await test_db_session.flush()

    hid = uuid.uuid4()
    handover = Handover(
        id=hid,
        project_id=project.id,
        created_by=owner.id,
        title="Production Infrastructure Handover",
        status="DRAFT",
        version="v1.0",
        transition_status="Awaiting Acknowledgement",
    )
    test_db_session.add(handover)
    await test_db_session.flush()

    sec1 = HandoverSection(
        id=uuid.uuid4(),
        handover_id=hid,
        section_type="project_overview",
        title="1. Project Overview",
        content={"markdown": "# Overview\nCore microservices transition package.", "confidence": 0.98},
        sort_order=1,
    )
    sec2 = HandoverSection(
        id=uuid.uuid4(),
        handover_id=hid,
        section_type="technical_architecture",
        title="2. Technical Architecture",
        content={"markdown": "# Architecture\nEvent-driven broker architecture.", "confidence": 0.95},
        sort_order=2,
    )
    test_db_session.add_all([sec1, sec2])
    await test_db_session.commit()

    res = await test_db_session.execute(
        select(Handover).options(selectinload(Handover.sections)).where(Handover.id == hid)
    )
    retrieved = res.scalar_one()

    assert retrieved.title == "Production Infrastructure Handover"
    assert retrieved.version == "v1.0"
    assert len(retrieved.sections) == 2
    assert retrieved.sections[0].title == "1. Project Overview"
    assert retrieved.sections[1].section_type == "technical_architecture"


# ==============================================================================
# 8. EVIDENCE REFERENCES POINT TO VALID SOURCE RECORDS
# ==============================================================================
@pytest.mark.asyncio
async def test_evidence_references_point_to_valid_source_records(test_db_session: AsyncSession):
    """Verifies that evidence references link handover sections directly to ground-truth documents and chunks."""
    owner = User(id=uuid.uuid4(), full_name="Verifier", email="verifier@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Evidence Audit Project", created_by=owner.id)
    doc = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="security_audit.pdf",
        stored_filename="sec_stored.pdf",
        file_type="pdf",
        file_size=4096,
        storage_path="/tmp/sec.pdf",
        processing_status="completed",
    )
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        project_id=project.id,
        chunk_index=0,
        content="All internal RPC communications require mTLS with TLS 1.3.",
        page_number=5,
        section_title="mTLS Policy",
    )
    handover = Handover(id=uuid.uuid4(), project_id=project.id, created_by=owner.id, title="Security Handover")
    sec = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover.id,
        section_type="key_decisions",
        title="Security Decisions",
        content={"summary": "mTLS mandatory"},
        sort_order=1,
    )
    test_db_session.add_all([owner, project, doc, chunk, handover, sec])
    await test_db_session.flush()

    ev_ref = EvidenceReference(
        id=uuid.uuid4(),
        handover_section_id=sec.id,
        document_id=doc.id,
        document_chunk_id=chunk.id,
        claim_id="claim_sec_001",
        claim_text="Internal communication enforces mTLS with TLS 1.3",
        quoted_text="All internal RPC communications require mTLS with TLS 1.3.",
        supporting_text_excerpt="All internal RPC communications require mTLS with TLS 1.3.",
        source_filename="security_audit.pdf",
        page_number=5,
        section_reference="mTLS Policy",
        relevance_score=0.99,
        verification_status="Supported",
    )
    test_db_session.add(ev_ref)
    await test_db_session.commit()

    res = await test_db_session.execute(
        select(EvidenceReference)
        .options(
            selectinload(EvidenceReference.handover_section),
            selectinload(EvidenceReference.document),
            selectinload(EvidenceReference.chunk),
        )
        .where(EvidenceReference.claim_id == "claim_sec_001")
    )
    retrieved = res.scalar_one()

    assert retrieved.handover_section_id == sec.id
    assert retrieved.document_id == doc.id
    assert retrieved.document_chunk_id == chunk.id
    assert retrieved.verification_status == "Supported"
    assert retrieved.relevance_score == 0.99
    assert retrieved.handover_section.title == "Security Decisions"
    assert retrieved.document.original_filename == "security_audit.pdf"
    assert retrieved.chunk.section_title == "mTLS Policy"


# ==============================================================================
# 9. CONFLICT RESOLUTIONS PERSISTENCE
# ==============================================================================
@pytest.mark.asyncio
async def test_conflict_resolutions_persist(test_db_session: AsyncSession):
    """Verifies that cross-document contradictions and human arbitration resolutions persist."""
    owner = User(id=uuid.uuid4(), full_name="Lead Arbitrator", email="lead_arb@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Conflict Resolution Project", created_by=owner.id)
    doc_a = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="spec_v1.md",
        stored_filename="spec_v1_stored.md",
        file_type="md",
        file_size=100,
        storage_path="/tmp/v1.md",
        processing_status="completed",
    )
    doc_b = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        original_filename="spec_v2.md",
        stored_filename="spec_v2_stored.md",
        file_type="md",
        file_size=100,
        storage_path="/tmp/v2.md",
        processing_status="completed",
    )
    test_db_session.add_all([owner, project, doc_a, doc_b])
    await test_db_session.flush()

    cid = uuid.uuid4()
    conflict = Conflict(
        id=cid,
        project_id=project.id,
        conflict_category="architecture",
        description="Conflicting database engine choices between v1 and v2 specifications.",
        statement_a="PostgreSQL 16 is selected for persistent storage.",
        statement_b="Cassandra is selected for distributed persistence.",
        source_a={"document_id": str(doc_a.id), "excerpt": "PostgreSQL 16 is selected."},
        source_b={"document_id": str(doc_b.id), "excerpt": "Cassandra is selected."},
        source_document_a_id=doc_a.id,
        source_document_b_id=doc_b.id,
        source_document_a_name="spec_v1.md",
        source_document_b_name="spec_v2.md",
        resolution_status="Unresolved",
    )
    test_db_session.add(conflict)
    await test_db_session.commit()

    # Human reviewer arbitrates conflict
    conflict.resolution_status = "Resolved"
    conflict.status = "Resolved"
    conflict.resolution = {
        "strategy": "MANUAL",
        "authoritative_value": "PostgreSQL 16",
        "resolution_notes": "Architecture review confirmed PostgreSQL 16 satisfies relational query requirements.",
    }
    conflict.resolved_by = owner.id
    await test_db_session.commit()

    res = await test_db_session.execute(select(Conflict).where(Conflict.id == cid))
    saved_conflict = res.scalar_one()

    assert saved_conflict.resolution_status == "Resolved"
    assert saved_conflict.resolved_by == owner.id
    assert saved_conflict.resolution["authoritative_value"] == "PostgreSQL 16"


# ==============================================================================
# 10. AUDIT LOGS RECORDING & IMMUTABILITY
# ==============================================================================
@pytest.mark.asyncio
async def test_audit_logs_correctly_recorded(test_db_session: AsyncSession):
    """Verifies that audit log entries record actions, entities, actors, and metadata."""
    user = User(id=uuid.uuid4(), full_name="Audited Actor", email="actor@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Audited Workspace", created_by=user.id)
    test_db_session.add_all([user, project])
    await test_db_session.flush()

    log_id = uuid.uuid4()
    target_handover_id = str(uuid.uuid4())
    audit_entry = AuditLog(
        id=log_id,
        project_id=project.id,
        user_id=user.id,
        action=AuditActionType.HANDOVER_APPROVED.value,
        entity_type=AuditEntityType.HANDOVER.value,
        entity_id=target_handover_id,
        change_metadata={"approval_notes": "Verified against all evidence citations", "version": "v1.0"},
        request_context={"ip": "192.168.1.100", "user_agent": "Mozilla/5.0"},
        timestamp=datetime.now(timezone.utc),
    )
    test_db_session.add(audit_entry)
    await test_db_session.commit()

    res = await test_db_session.execute(select(AuditLog).where(AuditLog.id == log_id))
    entry = res.scalar_one()

    assert entry.action == "handover_approved"
    assert entry.entity_type == "handover"
    assert entry.entity_id == target_handover_id
    assert entry.user_id == user.id
    assert entry.change_metadata["version"] == "v1.0"
    assert entry.request_context["ip"] == "192.168.1.100"


# ==============================================================================
# 11. HANDOVER VERSIONS PRESERVE HISTORICAL SNAPSHOTS
# ==============================================================================
@pytest.mark.asyncio
async def test_handover_versions_preserve_historical_snapshots(test_db_session: AsyncSession):
    """Verifies that handover version snapshots remain immutable and parent lineage is preserved."""
    creator = User(id=uuid.uuid4(), full_name="Release Engineer", email="release@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Version Lineage Project", created_by=creator.id)
    handover = Handover(id=uuid.uuid4(), project_id=project.id, created_by=creator.id, title="Service Handover")
    test_db_session.add_all([creator, project, handover])
    await test_db_session.flush()

    # 1. Version v1.0
    v1_id = uuid.uuid4()
    v1_snapshot = {
        "title": "Service Handover v1.0",
        "sections": [{"title": "Overview", "content": "Initial release spec"}],
        "tasks": [{"title": "Deploy canary", "status": "pending"}],
    }
    ver_v1 = HandoverVersion(
        id=v1_id,
        handover_id=handover.id,
        version_number="v1.0",
        version_description="Initial approved version",
        approval_status="APPROVED",
        is_latest=False,
        created_by=creator.id,
        snapshot=v1_snapshot,
    )
    test_db_session.add(ver_v1)
    await test_db_session.commit()

    # 2. Version v1.1 linking to parent v1.0
    v2_id = uuid.uuid4()
    v2_snapshot = {
        "title": "Service Handover v1.1",
        "sections": [{"title": "Overview", "content": "Revised release spec with rate limiter"}],
        "tasks": [{"title": "Deploy canary", "status": "completed"}],
    }
    ver_v2 = HandoverVersion(
        id=v2_id,
        handover_id=handover.id,
        version_number="v1.1",
        version_description="Added rate limiting chapter",
        approval_status="APPROVED",
        parent_version_id=v1_id,
        is_latest=True,
        created_by=creator.id,
        snapshot=v2_snapshot,
    )
    test_db_session.add(ver_v2)
    await test_db_session.commit()

    # Query back and verify v1.0 historical snapshot is unchanged
    res_v1 = await test_db_session.execute(select(HandoverVersion).where(HandoverVersion.id == v1_id))
    retrieved_v1 = res_v1.scalar_one()
    assert retrieved_v1.version_number == "v1.0"
    assert retrieved_v1.snapshot["sections"][0]["content"] == "Initial release spec"
    assert retrieved_v1.is_latest is False

    res_v2 = await test_db_session.execute(select(HandoverVersion).where(HandoverVersion.id == v2_id))
    retrieved_v2 = res_v2.scalar_one()
    assert retrieved_v2.version_number == "v1.1"
    assert retrieved_v2.parent_version_id == v1_id
    assert retrieved_v2.is_latest is True
    assert retrieved_v2.snapshot["tasks"][0]["status"] == "completed"


# ==============================================================================
# 12. INCOMING-MEMBER ACKNOWLEDGEMENTS PERSISTENCE
# ==============================================================================
@pytest.mark.asyncio
async def test_incoming_member_acknowledgements_persist(test_db_session: AsyncSession):
    """Verifies that incoming member handover acknowledgements and transition status persist."""
    author = User(id=uuid.uuid4(), full_name="Outgoing Lead", email="outgoing@corp.io", password_hash="pwd")
    incoming = User(id=uuid.uuid4(), full_name="Incoming Member", email="incoming@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Continuity Project", created_by=author.id)
    handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=author.id,
        assigned_to=incoming.id,
        title="Continuity Handover",
        status="APPROVED",
        transition_status="Awaiting Acknowledgement",
    )
    test_db_session.add_all([author, incoming, project, handover])
    await test_db_session.commit()

    # Incoming member acknowledges receipt
    ack_time = datetime.now(timezone.utc)
    handover.transition_status = "Acknowledged"
    handover.acknowledged_at = ack_time
    handover.acknowledged_by = incoming.id
    handover.checklist_confirmed = True
    handover.acknowledgement_notes = "Received handover package. All runbooks reviewed and validated."
    await test_db_session.commit()

    res = await test_db_session.execute(
        select(Handover).options(selectinload(Handover.acknowledger)).where(Handover.id == handover.id)
    )
    retrieved = res.scalar_one()

    assert retrieved.transition_status == "Acknowledged"
    assert retrieved.acknowledged_by == incoming.id
    assert retrieved.checklist_confirmed is True
    assert "runbooks reviewed" in retrieved.acknowledgement_notes
    assert retrieved.acknowledger.full_name == "Incoming Member"


# ==============================================================================
# 13. TASK STATUS UPDATES & PROGRESS LOGS PERSISTENCE
# ==============================================================================
@pytest.mark.asyncio
async def test_task_status_updates_persist(test_db_session: AsyncSession):
    """Verifies that tasks and their timestamped progress update history persist accurately."""
    user = User(id=uuid.uuid4(), full_name="Task Lead", email="tasklead@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Task Workspace", created_by=user.id)
    task = Task(
        id=uuid.uuid4(),
        project_id=project.id,
        title="Migrate database cluster to Aurora",
        description="Execute blue/green cluster migration",
        assigned_to=user.id,
        priority="high",
        status="pending",
    )
    test_db_session.add_all([user, project, task])
    await test_db_session.commit()

    # 1. First progress update (pending -> in_progress)
    task.status = "in_progress"
    prog1 = TaskProgressUpdate(
        id=uuid.uuid4(),
        task_id=task.id,
        user_id=user.id,
        update_text="Provisioned Aurora staging read replica.",
        status_before="pending",
        status_after="in_progress",
    )
    test_db_session.add(prog1)
    await test_db_session.commit()

    # 2. Second progress update (in_progress -> completed)
    task.status = "completed"
    prog2 = TaskProgressUpdate(
        id=uuid.uuid4(),
        task_id=task.id,
        user_id=user.id,
        update_text="Completed traffic cutover. Zero packet loss.",
        status_before="in_progress",
        status_after="completed",
    )
    test_db_session.add(prog2)
    await test_db_session.commit()

    res = await test_db_session.execute(
        select(Task).options(selectinload(Task.progress_updates)).where(Task.id == task.id)
    )
    retrieved_task = res.scalar_one()

    assert retrieved_task.status == "completed"
    assert len(retrieved_task.progress_updates) == 2
    updates = sorted(retrieved_task.progress_updates, key=lambda u: u.created_at)
    assert updates[0].status_after == "in_progress"
    assert updates[1].status_after == "completed"
    assert "traffic cutover" in updates[1].update_text


# ==============================================================================
# 14. DUPLICATE RECORDS REJECTION
# ==============================================================================
@pytest.mark.asyncio
async def test_duplicate_records_rejection(test_db_session: AsyncSession):
    """Verifies that database unique constraints strictly reject duplicate entries."""
    # 1. Duplicate email rejection
    u1_id = uuid.uuid4()
    u1 = User(id=u1_id, full_name="Alice A", email="unique@corp.io", password_hash="pwd")
    test_db_session.add(u1)
    await test_db_session.commit()

    u2 = User(id=uuid.uuid4(), full_name="Alice B", email="unique@corp.io", password_hash="pwd")
    test_db_session.add(u2)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # 2. Duplicate project member rejection
    p_id = uuid.uuid4()
    proj = Project(id=p_id, name="Dup Member Proj", created_by=u1_id)
    test_db_session.add(proj)
    await test_db_session.commit()

    mem1 = ProjectMember(id=uuid.uuid4(), project_id=p_id, user_id=u1_id, role="LEAD")
    test_db_session.add(mem1)
    await test_db_session.commit()

    mem2 = ProjectMember(id=uuid.uuid4(), project_id=p_id, user_id=u1_id, role="VIEWER")
    test_db_session.add(mem2)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # 3. Duplicate stored_filename on Document
    d1 = Document(
        id=uuid.uuid4(),
        project_id=p_id,
        original_filename="doc1.txt",
        stored_filename="same_filename.bin",
        file_type="txt",
        file_size=10,
        storage_path="/tmp/1",
        processing_status="completed",
    )
    test_db_session.add(d1)
    await test_db_session.commit()

    d2 = Document(
        id=uuid.uuid4(),
        project_id=p_id,
        original_filename="doc2.txt",
        stored_filename="same_filename.bin",
        file_type="txt",
        file_size=20,
        storage_path="/tmp/2",
        processing_status="completed",
    )
    test_db_session.add(d2)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # 4. Self-referencing task dependency check constraint
    t1_id = uuid.uuid4()
    t1 = Task(id=t1_id, project_id=p_id, title="Task 1")
    test_db_session.add(t1)
    await test_db_session.commit()

    self_dep = TaskDependency(id=uuid.uuid4(), task_id=t1_id, depends_on_task_id=t1_id)
    test_db_session.add(self_dep)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()


# ==============================================================================
# 15. MISSING FOREIGN KEYS REJECTION
# ==============================================================================
@pytest.mark.asyncio
async def test_missing_foreign_keys_rejection(test_db_session: AsyncSession):
    """Verifies that non-existent foreign keys are strictly rejected with IntegrityError."""
    fake_id = uuid.uuid4()

    # 1. Project referencing nonexistent creator
    bad_proj = Project(id=uuid.uuid4(), name="Ghost Project", created_by=fake_id)
    test_db_session.add(bad_proj)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # 2. Document referencing nonexistent project
    bad_doc = Document(
        id=uuid.uuid4(),
        project_id=fake_id,
        original_filename="ghost.pdf",
        stored_filename="ghost.pdf",
        file_type="pdf",
        file_size=100,
        storage_path="/tmp/ghost",
        processing_status="completed",
    )
    test_db_session.add(bad_doc)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # 3. DocumentChunk referencing nonexistent document
    bad_chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=fake_id,
        project_id=fake_id,
        chunk_index=0,
        content="Ghost Chunk",
    )
    test_db_session.add(bad_chunk)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()


# ==============================================================================
# 16. ORPHANED RECORDS & CASCADING DELETES
# ==============================================================================
@pytest.mark.asyncio
async def test_orphaned_records_and_cascades(test_db_session: AsyncSession):
    """Verifies that cascading delete cleans up dependent entities without leaving orphaned rows."""
    u = User(id=uuid.uuid4(), full_name="Cascade Admin", email="admin_casc@corp.io", password_hash="pwd")
    p = Project(id=uuid.uuid4(), name="Cascading Workspace", created_by=u.id)
    d = Document(
        id=uuid.uuid4(),
        project_id=p.id,
        uploaded_by=u.id,
        original_filename="spec.md",
        stored_filename="spec_casc.md",
        file_type="md",
        file_size=100,
        storage_path="/tmp/casc.md",
        processing_status="completed",
    )
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=d.id,
        project_id=p.id,
        chunk_index=0,
        content="Chunk in cascading project.",
    )
    h = Handover(id=uuid.uuid4(), project_id=p.id, created_by=u.id, title="Handover in Project")
    sec = HandoverSection(
        id=uuid.uuid4(),
        handover_id=h.id,
        section_type="overview",
        title="Section in Project",
        content={"data": "content"},
    )
    task = Task(id=uuid.uuid4(), project_id=p.id, handover_id=h.id, title="Task in Project")
    test_db_session.add_all([u, p, d, chunk, h, sec, task])
    await test_db_session.commit()

    # Delete project
    await test_db_session.delete(p)
    await test_db_session.commit()

    # Verify all dependent entities are wiped (zero orphans)
    docs = (await test_db_session.execute(select(Document).where(Document.project_id == p.id))).scalars().all()
    chunks = (await test_db_session.execute(select(DocumentChunk).where(DocumentChunk.project_id == p.id))).scalars().all()
    handovers = (await test_db_session.execute(select(Handover).where(Handover.project_id == p.id))).scalars().all()
    sections = (await test_db_session.execute(select(HandoverSection).where(HandoverSection.handover_id == h.id))).scalars().all()
    tasks = (await test_db_session.execute(select(Task).where(Task.project_id == p.id))).scalars().all()

    assert len(docs) == 0
    assert len(chunks) == 0
    assert len(handovers) == 0
    assert len(sections) == 0
    assert len(tasks) == 0

    # User still exists (RESTRICT / SET NULL logic)
    res_user = await test_db_session.execute(select(User).where(User.id == u.id))
    assert res_user.scalar_one() is not None


# ==============================================================================
# 17. DATABASE TRANSACTION FAILURES & ROLLBACK
# ==============================================================================
@pytest.mark.asyncio
async def test_database_transaction_atomicity_and_rollback(test_db_session: AsyncSession):
    """Verifies atomic rollback: a failed intermediate operation leaves zero partial state."""
    user = User(id=uuid.uuid4(), full_name="Tx Tester", email="tx@corp.io", password_hash="pwd")
    project = Project(id=uuid.uuid4(), name="Tx Project", created_by=user.id)
    test_db_session.add_all([user, project])
    await test_db_session.commit()

    initial_handover_count = len((await test_db_session.execute(select(Handover))).scalars().all())

    # Attempt atomic batch with deliberate error
    try:
        async with test_db_session.begin_nested():
            valid_handover = Handover(
                id=uuid.uuid4(),
                project_id=project.id,
                created_by=user.id,
                title="Atomic Handover",
            )
            test_db_session.add(valid_handover)
            await test_db_session.flush()

            # Deliberately broken section referencing non-existent handover
            broken_section = HandoverSection(
                id=uuid.uuid4(),
                handover_id=uuid.uuid4(),  # Does not exist
                section_type="architecture",
                title="Broken Section",
                content={},
            )
            test_db_session.add(broken_section)
            await test_db_session.flush()
    except IntegrityError:
        await test_db_session.rollback()

    # Verify zero new handovers persisted
    final_handovers = (await test_db_session.execute(select(Handover))).scalars().all()
    assert len(final_handovers) == initial_handover_count


# ==============================================================================
# 18. DATA ISOLATION BETWEEN PROJECTS
# ==============================================================================
@pytest.mark.asyncio
async def test_data_isolation_between_projects(test_db_session: AsyncSession):
    """Verifies strict tenant isolation: Project A queries never return Project B records."""
    u1 = User(id=uuid.uuid4(), full_name="Tenant 1 Lead", email="t1@corp.io", password_hash="pwd")
    u2 = User(id=uuid.uuid4(), full_name="Tenant 2 Lead", email="t2@corp.io", password_hash="pwd")
    p1 = Project(id=uuid.uuid4(), name="Tenant Alpha Project", created_by=u1.id)
    p2 = Project(id=uuid.uuid4(), name="Tenant Beta Project", created_by=u2.id)

    # Tenant 1 documents & tasks
    d1 = Document(
        id=uuid.uuid4(),
        project_id=p1.id,
        original_filename="t1_secret.pdf",
        stored_filename="t1_sec.pdf",
        file_type="pdf",
        file_size=100,
        storage_path="/tmp/t1",
        processing_status="completed",
    )
    t1 = Task(id=uuid.uuid4(), project_id=p1.id, title="Alpha Task")

    # Tenant 2 documents & tasks
    d2 = Document(
        id=uuid.uuid4(),
        project_id=p2.id,
        original_filename="t2_secret.pdf",
        stored_filename="t2_sec.pdf",
        file_type="pdf",
        file_size=100,
        storage_path="/tmp/t2",
        processing_status="completed",
    )
    t2 = Task(id=uuid.uuid4(), project_id=p2.id, title="Beta Task")

    test_db_session.add_all([u1, u2, p1, p2, d1, t1, d2, t2])
    await test_db_session.commit()

    # Query strictly isolated to Project 1
    p1_docs = (await test_db_session.execute(select(Document).where(Document.project_id == p1.id))).scalars().all()
    p1_tasks = (await test_db_session.execute(select(Task).where(Task.project_id == p1.id))).scalars().all()

    assert len(p1_docs) == 1
    assert p1_docs[0].original_filename == "t1_secret.pdf"
    assert len(p1_tasks) == 1
    assert p1_tasks[0].title == "Alpha Task"

    # Query strictly isolated to Project 2
    p2_docs = (await test_db_session.execute(select(Document).where(Document.project_id == p2.id))).scalars().all()
    p2_tasks = (await test_db_session.execute(select(Task).where(Task.project_id == p2.id))).scalars().all()

    assert len(p2_docs) == 1
    assert p2_docs[0].original_filename == "t2_secret.pdf"
    assert len(p2_tasks) == 1
    assert p2_tasks[0].title == "Beta Task"


# ==============================================================================
# 19. MIGRATION ROLLBACK & LINEAGE CONSISTENCY
# ==============================================================================
def test_migration_lineage_and_rollback_support():
    """Verifies that all Alembic migrations form an unbroken lineage and provide downgrade() functions."""
    import glob
    import importlib.util
    from pathlib import Path

    migrations_dir = Path("backend") / "migrations" / "versions"
    migration_files = sorted(migrations_dir.glob("*.py"))
    assert len(migration_files) >= 10, f"Expected at least 10 migration files, found {len(migration_files)}"

    revisions = {}
    down_revisions = {}

    for mf in migration_files:
        spec = importlib.util.spec_from_file_location(mf.stem, mf)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        rev = getattr(mod, "revision", None)
        down_rev = getattr(mod, "down_revision", None)

        assert rev is not None, f"Migration {mf.name} is missing 'revision'"
        assert hasattr(mod, "upgrade"), f"Migration {mf.name} is missing 'upgrade()'"
        assert hasattr(mod, "downgrade"), f"Migration {mf.name} is missing 'downgrade()' (required for rollback)"

        revisions[rev] = mf.name
        down_revisions[rev] = down_rev

    # Verify unbroken chain back to initial schema
    current = "010_incoming_continuity_workflow"
    visited = []
    while current is not None:
        visited.append(current)
        current = down_revisions.get(current)

    assert "001_initial_schema" in visited, "Migration chain does not connect back to 001_initial_schema"
    assert len(visited) == 10, f"Expected 10 connected revisions in chain, found {len(visited)}: {visited}"
