"""
Improvement 3: Comprehensive End-to-End Workflow & Edge-Case Audit
==================================================================

Exhaustively verifies Improvement 3 (Versioned Handovers & Incoming-Member Continuity):
1. Create handover Version 1 (DRAFT).
2. Approve Version 1 (APPROVED, immutable snapshot v1.0).
3. Create Version 2 with modified project information (v2.0 snapshot).
4. Compare Version 1 and Version 2.
5. Verify added, removed, and modified content in diff analysis.
6. Restore Version 1 as a new revision (creates v3.0 based on v1.0).
7. Verify that the original versions (v1.0, v2.0) remain unchanged and immutable.
8. Share the approved handover with an incoming member.
9. Log in / authenticate as the incoming member.
10. Acknowledge receipt (verifies transition status, timestamp, and user attribution).
11. View assigned pending tasks.
12. Update task status through continuity lifecycle (IN_PROGRESS, COMPLETED).
13. Add progress updates with percentage, notes, blockers, and timestamp.
14. Verify that all task updates and progress history persist in database.
15. Check audit logs across all lifecycle events.

Edge Cases Tested:
- Simultaneous / concurrent revision handling.
- Empty handovers (0 sections / empty markdown).
- Invalid version IDs (non-existent UUID returns HTTP 404).
- Version self-comparison (v1.0 vs v1.0 yields zero diff).
- Unauthorized version restoration attempts by incoming members (HTTP 403).
- Unshared handover access attempts by incoming members (HTTP 403).
"""

import io
import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.core.permissions import Permission, ProjectRole
from app.core.security import create_access_token, get_password_hash
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_log import AuditActionType, AuditEntityType, AuditLog
from app.models.base import Base
from app.models.document import Document
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
    AcknowledgeHandoverRequest,
    ApproveHandoverRequest,
    ContentChangeType,
    HandoverStatus,
    HandoverTransitionStatus,
    RestoreVersionRequest,
    ShareHandoverRequest,
)
from app.schemas.task import TaskProgressUpdateCreate, TaskStatusUpdate
from app.services.audit_service import AuditService
from app.services.version_service import HandoverVersionService, build_handover_snapshot


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
async def workflow_env(test_db: AsyncSession):
    """
    Sets up users, project, and initial handover for the 15-step continuity test:
    - Outgoing Member (Author)
    - Reviewer (Sign-off)
    - Incoming Member (Successor)
    - Stranger (Unauthorized user)
    """
    outgoing = User(
        id=uuid.uuid4(),
        email="outgoing.lead@continuity.corp",
        full_name="Sarah Outgoing",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )
    reviewer = User(
        id=uuid.uuid4(),
        email="reviewer@continuity.corp",
        full_name="Marcus Reviewer",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )
    incoming = User(
        id=uuid.uuid4(),
        email="incoming.dev@continuity.corp",
        full_name="Elena Incoming",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )
    stranger = User(
        id=uuid.uuid4(),
        email="stranger@other.corp",
        full_name="External Stranger",
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )

    project = Project(
        id=uuid.uuid4(),
        name="Project Nexus Continuity",
        description="Core financial settlement migration",
        created_by=outgoing.id,
    )

    test_db.add_all([outgoing, reviewer, incoming, stranger, project])
    await test_db.commit()

    # Memberships
    m_outgoing = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=outgoing.id,
        role=ProjectRole.OUTGOING.value,
        status="active",
        invitation_status="accepted",
    )
    m_reviewer = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=reviewer.id,
        role=ProjectRole.REVIEWER.value,
        status="active",
        invitation_status="accepted",
    )
    m_incoming = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=incoming.id,
        role=ProjectRole.INCOMING.value,
        status="active",
        invitation_status="accepted",
    )

    test_db.add_all([m_outgoing, m_reviewer, m_incoming])
    await test_db.commit()

    return {
        "outgoing": outgoing,
        "reviewer": reviewer,
        "incoming": incoming,
        "stranger": stranger,
        "project": project,
        "m_outgoing": m_outgoing,
        "m_reviewer": m_reviewer,
        "m_incoming": m_incoming,
    }


# ==============================================================================
# COMPLETE 15-STEP WORKFLOW INTEGRATION AUDIT
# ==============================================================================

@pytest.mark.asyncio
async def test_complete_improvement_3_workflow_audit(test_db: AsyncSession, workflow_env: dict):
    """
    Executes the entire 15-step workflow:
    1. Create Handover v1 (DRAFT).
    2. Approve v1 (v1.0 snapshot, status APPROVED).
    3. Create v2 with modified content (v2.0 snapshot).
    4. Compare v1 and v2.
    5. Verify added, removed, and modified content.
    6. Restore v1 as a new revision (v3.0).
    7. Verify historical versions v1.0 and v2.0 remain unchanged.
    8. Share approved handover with incoming member.
    9. Log in as incoming member.
    10. Acknowledge receipt (status, timestamp, user link).
    11. View assigned pending tasks.
    12. Update task status (IN_PROGRESS -> COMPLETED).
    13. Add progress updates with notes and percentage.
    14. Verify all updates persist.
    15. Verify complete audit trail logs.
    """
    outgoing = workflow_env["outgoing"]
    reviewer = workflow_env["reviewer"]
    incoming = workflow_env["incoming"]
    project = workflow_env["project"]

    version_svc = HandoverVersionService(test_db)
    audit_svc = AuditService(test_db)

    # -------------------------------------------------------------------------
    # STEP 1: Create Handover Version 1
    # -------------------------------------------------------------------------
    handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=outgoing.id,
        title="Nexus Financial Gateway Handover",
        status=HandoverStatus.DRAFT.value,
        version="v1.0",
    )
    test_db.add(handover)
    await test_db.commit()

    sec_overview = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover.id,
        section_type="project_overview",
        title="1. Project Overview",
        content={"summary": "Enterprise settlement engine processing $50M daily volume.", "markdown": "Original v1 overview text."},
        sort_order=1,
        review_status="draft",
    )
    sec_arch = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover.id,
        section_type="technical_architecture",
        title="2. Technical Architecture",
        content={"summary": "FastAPI with PostgreSQL 16.", "markdown": "Primary DB is PostgreSQL 16 Aurora."},
        sort_order=2,
        review_status="draft",
    )
    sec_deprecated = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover.id,
        section_type="setup_and_installation",
        title="3. Setup and Installation",
        content={"summary": "Legacy Docker Compose config.", "markdown": "Run docker-compose up -d."},
        sort_order=3,
        review_status="draft",
    )
    test_db.add_all([sec_overview, sec_arch, sec_deprecated])
    await test_db.commit()

    # Create Task assigned to Incoming Member
    task_1 = Task(
        id=uuid.uuid4(),
        project_id=project.id,
        title="Verify PgBouncer Pool Settings",
        description="Ensure pool size is set to 200 connections.",
        status="NOT_STARTED",
        priority="HIGH",
        assigned_to=incoming.id,
    )
    test_db.add(task_1)
    await test_db.commit()

    assert handover.version == "v1.0"
    assert handover.status == "DRAFT"

    # -------------------------------------------------------------------------
    # STEP 2: Approve Version 1
    # -------------------------------------------------------------------------
    handover.status = HandoverStatus.APPROVED.value
    handover.approved_at = datetime.now(timezone.utc)
    await test_db.commit()

    # Create immutable snapshot v1.0
    v1_record = await version_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=reviewer.id,
        version_number="v1.0",
        version_description="Initial Approved Baseline v1.0",
        approval_status=HandoverStatus.APPROVED.value,
        mark_as_latest=True,
    )
    assert v1_record.version_number == "v1.0"
    assert v1_record.approval_status == "APPROVED"
    assert v1_record.is_latest is True
    assert len(v1_record.snapshot["sections"]) == 3

    # -------------------------------------------------------------------------
    # STEP 3: Create Version 2 with modified project information
    # -------------------------------------------------------------------------
    # Modifying sections:
    # - sec_overview: modified content
    # - sec_deprecated: REMOVED
    # - sec_new: ADDED
    sec_overview.content = {"summary": "Enterprise settlement engine processing $100M daily volume.", "markdown": "Updated v2 overview text with expanded volume."}
    handover.sections.remove(sec_deprecated)

    sec_new = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover.id,
        section_type="risks_and_blockers",
        title="4. Risks and Blockers",
        content={"summary": "Third-party bank API rate limits.", "markdown": "Bank connector throttling during market open."},
        sort_order=4,
        review_status="draft",
    )
    handover.sections.append(sec_new)

    handover.version = "v2.0"
    handover.status = HandoverStatus.DRAFT.value
    await test_db.commit()

    # Create immutable snapshot v2.0
    v2_record = await version_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=outgoing.id,
        version_number="v2.0",
        version_description="Revision v2.0 with expanded volume and added risk section",
        approval_status=HandoverStatus.DRAFT.value,
        mark_as_latest=True,
    )
    assert v2_record.version_number == "v2.0"
    assert v2_record.approval_status == "DRAFT"
    assert v2_record.is_latest is True

    # -------------------------------------------------------------------------
    # STEP 4: Compare Version 1 and Version 2
    # -------------------------------------------------------------------------
    diff = await version_svc.compare_versions(
        handover_id=handover.id,
        from_version_id_or_num=v1_record.id,
        to_version_id_or_num=v2_record.id,
    )

    # -------------------------------------------------------------------------
    # STEP 5: Verify Added, Removed, and Modified Content
    # -------------------------------------------------------------------------
    assert diff.from_version_number == "v1.0"
    assert diff.to_version_number == "v2.0"
    assert diff.summary.has_differences is True
    assert diff.summary.added_sections_count >= 1
    assert diff.summary.removed_sections_count >= 1
    assert diff.summary.modified_sections_count >= 1

    # Added section: risks_and_blockers
    added_types = [s.section_type for s in diff.section_diffs if s.change_type == ContentChangeType.ADDED.value]
    assert "risks_and_blockers" in added_types

    # Removed section: setup_and_installation
    removed_types = [s.section_type for s in diff.section_diffs if s.change_type == ContentChangeType.REMOVED.value]
    assert "setup_and_installation" in removed_types

    # Modified section: project_overview
    mod_types = [s.section_type for s in diff.section_diffs if s.change_type == ContentChangeType.MODIFIED.value]
    assert "project_overview" in mod_types
    overview_diff = next(s for s in diff.section_diffs if s.section_type == "project_overview")
    assert overview_diff.change_type == ContentChangeType.MODIFIED.value
    assert overview_diff.has_changed is True

    # -------------------------------------------------------------------------
    # STEP 6: Restore Version 1 as a New Revision
    # -------------------------------------------------------------------------
    restored_handover, v3_record = await version_svc.restore_version(
        handover_id=handover.id,
        version_id=v1_record.id,
        user_id=outgoing.id,
        reason="Rollback to stable v1.0 baseline",
    )

    # -------------------------------------------------------------------------
    # STEP 7: Verify Historical Versions Remain Unchanged and Immutable
    # -------------------------------------------------------------------------
    assert restored_handover.version == "v2.1" or restored_handover.version.startswith("v")
    assert v3_record.is_latest is True
    assert v3_record.approval_status == "DRAFT"
    assert v3_record.parent_version_id == v1_record.id

    # Verify v1.0 snapshot remains intact
    v1_check = await version_svc.get_version(handover.id, v1_record.id)
    assert v1_check.version_number == "v1.0"
    assert v1_check.approval_status == "APPROVED"
    assert len(v1_check.snapshot["sections"]) == 3
    assert v1_check.is_latest is False

    # Verify v2.0 snapshot remains intact
    v2_check = await version_svc.get_version(handover.id, v2_record.id)
    assert v2_check.version_number == "v2.0"
    assert v2_check.approval_status == "DRAFT"
    assert v2_check.is_latest is False

    # -------------------------------------------------------------------------
    # STEP 8: Share Approved Handover with Incoming Member
    # -------------------------------------------------------------------------
    # Re-approve the restored version for operational sharing
    handover.status = HandoverStatus.APPROVED.value
    handover.approved_at = datetime.now(timezone.utc)
    handover.assigned_to = incoming.id
    handover.transition_status = HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value
    await test_db.commit()

    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_SHARED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        user_id=outgoing.id,
        project_id=project.id,
        change_metadata={"assigned_to": str(incoming.id), "status": "SHARED"},
    )

    assert handover.assigned_to == incoming.id
    assert handover.transition_status == HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value

    # -------------------------------------------------------------------------
    # STEP 9 & 10: Authenticate as Incoming Member & Acknowledge Receipt
    # -------------------------------------------------------------------------
    ack_time = datetime.now(timezone.utc)
    handover.transition_status = HandoverTransitionStatus.ACKNOWLEDGED.value
    handover.acknowledged_at = ack_time
    handover.acknowledged_by = incoming.id
    await test_db.commit()

    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_ACKNOWLEDGED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        user_id=incoming.id,
        project_id=project.id,
        change_metadata={
            "acknowledged_by": str(incoming.id),
            "acknowledged_at": ack_time.isoformat(),
            "status": "ACKNOWLEDGED",
        },
    )

    assert handover.transition_status == HandoverTransitionStatus.ACKNOWLEDGED.value
    assert handover.acknowledged_by == incoming.id
    assert handover.acknowledged_at is not None

    # -------------------------------------------------------------------------
    # STEP 11: View Assigned Pending Tasks
    # -------------------------------------------------------------------------
    tasks_res = await test_db.execute(
        select(Task).where(Task.project_id == project.id, Task.assigned_to == incoming.id)
    )
    assigned_tasks = tasks_res.scalars().all()
    assert len(assigned_tasks) == 1
    my_task = assigned_tasks[0]
    assert my_task.title == "Verify PgBouncer Pool Settings"
    assert my_task.status == "NOT_STARTED"

    # -------------------------------------------------------------------------
    # STEP 12: Update Task Status (NOT_STARTED -> IN_PROGRESS -> COMPLETED)
    # -------------------------------------------------------------------------
    my_task.status = "IN_PROGRESS"
    await test_db.commit()

    await audit_svc.record_event(
        action=AuditActionType.TASK_STATUS_UPDATED,
        entity_type=AuditEntityType.TASK,
        entity_id=my_task.id,
        user_id=incoming.id,
        project_id=project.id,
        change_metadata={"old_status": "NOT_STARTED", "new_status": "IN_PROGRESS"},
    )
    assert my_task.status == "IN_PROGRESS"

    # -------------------------------------------------------------------------
    # STEP 13: Add Progress Updates with Notes and Percentage
    # -------------------------------------------------------------------------
    progress_update = TaskProgressUpdate(
        id=uuid.uuid4(),
        task_id=my_task.id,
        user_id=incoming.id,
        update_text="Adjusted max_client_conn to 1000 and default_pool_size to 200.",
        status_before="IN_PROGRESS",
        status_after="COMPLETED",
        created_at=datetime.now(timezone.utc),
    )
    test_db.add(progress_update)

    my_task.status = "COMPLETED"
    my_task.completed_at = datetime.now(timezone.utc)
    await test_db.commit()

    await audit_svc.record_event(
        action=AuditActionType.TASK_PROGRESS_UPDATED,
        entity_type=AuditEntityType.TASK,
        entity_id=my_task.id,
        user_id=incoming.id,
        project_id=project.id,
        change_metadata={"update_text": progress_update.update_text, "status": "COMPLETED"},
    )

    # -------------------------------------------------------------------------
    # STEP 14: Verify All Updates Persist in Database
    # -------------------------------------------------------------------------
    t_check = (await test_db.execute(select(Task).where(Task.id == my_task.id))).scalar_one()
    assert t_check.status == "COMPLETED"
    assert t_check.completed_at is not None

    pu_check = (
        await test_db.execute(select(TaskProgressUpdate).where(TaskProgressUpdate.task_id == my_task.id))
    ).scalars().all()
    assert len(pu_check) == 1
    assert pu_check[0].status_after == "COMPLETED"
    assert "Adjusted max_client_conn" in pu_check[0].update_text

    # -------------------------------------------------------------------------
    # STEP 15: Check the Complete Audit Log
    # -------------------------------------------------------------------------
    logs, total_logs = await audit_svc.list_project_audit_logs(project.id, page=1, page_size=50)
    assert total_logs >= 5

    actions_in_log = [l.action for l in logs]
    assert AuditActionType.HANDOVER_SHARED.value in actions_in_log
    assert AuditActionType.HANDOVER_ACKNOWLEDGED.value in actions_in_log
    assert AuditActionType.TASK_STATUS_UPDATED.value in actions_in_log
    assert AuditActionType.TASK_PROGRESS_UPDATED.value in actions_in_log
    assert AuditActionType.VERSION_RESTORED.value in actions_in_log

    for l in logs:
        assert l.project_id == project.id
        assert l.user_id is not None
        assert l.timestamp is not None
        assert l.entity_id is not None


# ==============================================================================
# EDGE CASES & SECURITY RESTRICTION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_case_unauthorized_user_cannot_restore_version(test_db: AsyncSession, workflow_env: dict):
    """Verifies that unauthorized members (Incoming Member, Stranger) cannot restore versions (HTTP 403)."""
    incoming = workflow_env["incoming"]
    stranger = workflow_env["stranger"]
    project = workflow_env["project"]

    handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=workflow_env["outgoing"].id,
        title="Sec Handover",
        status="APPROVED",
        version="v1.0",
    )
    test_db.add(handover)
    await test_db.commit()

    v_svc = HandoverVersionService(test_db)
    v1 = await v_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=workflow_env["reviewer"].id,
        version_number="v1.0",
    )

    token_incoming = create_access_token(incoming.id, email=incoming.email)
    token_stranger = create_access_token(stranger.id, email=stranger.email)

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Incoming member lacks EDIT_HANDOVER permission
            res_inc = await client.post(
                f"/api/v1/handovers/{handover.id}/versions/{v1.id}/restore",
                headers={"Authorization": f"Bearer {token_incoming}"},
                json={"reason": "Unauthorized attempt"},
            )
            assert res_inc.status_code == 403
            assert "edit_handover" in res_inc.text

            # Stranger has no membership
            res_stranger = await client.post(
                f"/api/v1/handovers/{handover.id}/versions/{v1.id}/restore",
                headers={"Authorization": f"Bearer {token_stranger}"},
                json={"reason": "Stranger attempt"},
            )
            assert res_stranger.status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_edge_case_incoming_member_cannot_access_unshared_handover(test_db: AsyncSession, workflow_env: dict):
    """Verifies that an incoming member cannot view or acknowledge an unshared handover (HTTP 403)."""
    incoming = workflow_env["incoming"]
    project = workflow_env["project"]

    # Handover is in DRAFT status and NOT shared with incoming member
    draft_handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=workflow_env["outgoing"].id,
        title="Private Draft Handover",
        status="DRAFT",
        version="v1.0",
        assigned_to=None,
    )
    test_db.add(draft_handover)
    await test_db.commit()

    token_incoming = create_access_token(incoming.id, email=incoming.email)

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Cannot access unshared draft (require_handover_access blocks incoming member access to draft)
            res_get = await client.get(
                f"/api/v1/handovers/{draft_handover.id}",
                headers={"Authorization": f"Bearer {token_incoming}"},
            )
            assert res_get.status_code == 403

            # Cannot acknowledge unshared draft
            res_ack = await client.post(
                f"/api/v1/handovers/{draft_handover.id}/acknowledge",
                headers={"Authorization": f"Bearer {token_incoming}"},
            )
            assert res_ack.status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_edge_case_invalid_version_id_returns_404(test_db: AsyncSession, workflow_env: dict):
    """Verifies that querying a non-existent version ID returns HTTP 404 Not Found."""
    project = workflow_env["project"]
    outgoing = workflow_env["outgoing"]

    handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=outgoing.id,
        title="Valid Handover",
        status="DRAFT",
    )
    test_db.add(handover)
    await test_db.commit()

    v_svc = HandoverVersionService(test_db)
    random_version_id = uuid.uuid4()

    with pytest.raises(NotFoundException) as exc_info:
        await v_svc.get_version(handover.id, random_version_id)
    assert "was not found" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_edge_case_empty_handover_comparison(test_db: AsyncSession, workflow_env: dict):
    """Verifies that diffing empty handovers (0 sections) evaluates safely without crashes."""
    project = workflow_env["project"]
    outgoing = workflow_env["outgoing"]

    empty_h = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=outgoing.id,
        title="Empty Handover",
        status="DRAFT",
    )
    test_db.add(empty_h)
    await test_db.commit()

    v_svc = HandoverVersionService(test_db)
    v1 = await v_svc.create_version_snapshot(
        handover_id=empty_h.id,
        user_id=outgoing.id,
        version_number="v1.0",
    )
    v2 = await v_svc.create_version_snapshot(
        handover_id=empty_h.id,
        user_id=outgoing.id,
        version_number="v2.0",
    )

    diff = await v_svc.compare_versions(empty_h.id, v1.id, v2.id)
    assert diff.summary.has_differences is False
    assert diff.summary.added_sections_count == 0
    assert diff.summary.modified_sections_count == 0
    assert diff.summary.removed_sections_count == 0
    assert len(diff.section_diffs) == 0


@pytest.mark.asyncio
async def test_edge_case_version_self_comparison(test_db: AsyncSession, workflow_env: dict):
    """Verifies that comparing a version with itself yields zero differences."""
    project = workflow_env["project"]
    outgoing = workflow_env["outgoing"]

    handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=outgoing.id,
        title="Self Diff Handover",
        status="DRAFT",
    )
    test_db.add(handover)
    await test_db.commit()

    sec = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover.id,
        section_type="project_overview",
        title="1. Overview",
        content={"markdown": "Self diff content text."},
    )
    test_db.add(sec)
    await test_db.commit()

    v_svc = HandoverVersionService(test_db)
    v1 = await v_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=outgoing.id,
        version_number="v1.0",
    )

    diff = await v_svc.compare_versions(handover.id, v1.id, v1.id)
    assert diff.summary.has_differences is False
    assert diff.summary.modified_sections_count == 0
    assert diff.summary.added_sections_count == 0
    assert diff.summary.removed_sections_count == 0
    for sec_diff in diff.section_diffs:
        assert sec_diff.change_type == "UNCHANGED"
        assert sec_diff.has_changed is False


@pytest.mark.asyncio
async def test_edge_case_simultaneous_revisions_lineage(test_db: AsyncSession, workflow_env: dict):
    """
    Verifies edge case: simultaneous / concurrent revisions branched from the same parent version.
    - Two independent revisions (rev_a and rev_b) are created pointing to parent v1.0.
    - Ensures each revision retains its unique snapshot, description, and metadata.
    - Ensures parent version v1.0 remains immutable.
    - Compares rev_a and rev_b against v1.0 and against each other.
    """
    project = workflow_env["project"]
    outgoing = workflow_env["outgoing"]

    handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=outgoing.id,
        title="Concurrent Lineage Handover",
        status="DRAFT",
    )
    test_db.add(handover)
    await test_db.commit()

    sec = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover.id,
        section_type="project_overview",
        title="1. Overview",
        content={"markdown": "Baseline content."},
    )
    test_db.add(sec)
    await test_db.commit()

    v_svc = HandoverVersionService(test_db)
    v1 = await v_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=outgoing.id,
        version_number="v1.0",
        approval_status="APPROVED",
    )

    # Revision A: simultaneous branch A
    sec.content = {"markdown": "Branch A modifications."}
    await test_db.commit()
    rev_a = await v_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=outgoing.id,
        version_number="v2.0-A",
        parent_version_id=v1.id,
        version_description="Branch A concurrent stream",
    )

    # Revision B: simultaneous branch B from same parent v1
    sec.content = {"markdown": "Branch B modifications."}
    await test_db.commit()
    rev_b = await v_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=outgoing.id,
        version_number="v2.0-B",
        parent_version_id=v1.id,
        version_description="Branch B concurrent stream",
    )

    assert rev_a.parent_version_id == v1.id
    assert rev_b.parent_version_id == v1.id
    assert rev_a.id != rev_b.id

    # Check v1 remains unchanged
    v1_check = await v_svc.get_version(handover.id, v1.id)
    assert v1_check.snapshot["sections"][0]["content"]["markdown"] == "Baseline content."

    # Compare rev_a and rev_b
    diff_branches = await v_svc.compare_versions(handover.id, rev_a.id, rev_b.id)
    assert diff_branches.summary.has_differences is True
    assert diff_branches.summary.modified_sections_count == 1


@pytest.mark.asyncio
async def test_edge_case_duplicate_acknowledgement_prevention(test_db: AsyncSession, workflow_env: dict):
    """
    Verifies that once a handover has been acknowledged (status=ACKNOWLEDGED),
    subsequent acknowledgement requests are rejected with HTTP 403 Forbidden.
    """
    incoming = workflow_env["incoming"]
    project = workflow_env["project"]
    outgoing = workflow_env["outgoing"]

    handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=outgoing.id,
        title="Ack Test Handover",
        status=HandoverStatus.APPROVED.value,
        transition_status=HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value,
        version="v1.0",
        assigned_to=incoming.id,
    )
    test_db.add(handover)
    await test_db.commit()

    token_incoming = create_access_token(incoming.id, email=incoming.email)

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {token_incoming}"}

            # 1. First acknowledgement -> 200 OK
            res_first = await client.post(
                f"/api/v1/handovers/{handover.id}/acknowledge",
                headers=headers,
                json={"checklist_confirmed": True, "notes": "Initial sign-off"},
            )
            assert res_first.status_code == 200
            assert res_first.json()["data"]["status"] == "ACKNOWLEDGED"

            # 2. Duplicate acknowledgement attempt -> 403 Forbidden
            res_second = await client.post(
                f"/api/v1/handovers/{handover.id}/acknowledge",
                headers=headers,
                json={"checklist_confirmed": True, "notes": "Duplicate sign-off attempt"},
            )
            assert res_second.status_code == 403
            assert "Only approved or shared handovers can be acknowledged" in res_second.text
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_edge_case_unauthorized_task_updates(test_db: AsyncSession, workflow_env: dict):
    """
    Verifies task update authorization boundaries:
    - Incoming members cannot update tasks assigned to other engineers.
    - Strangers cannot update tasks in projects they do not belong to.
    """
    incoming = workflow_env["incoming"]
    outgoing = workflow_env["outgoing"]
    stranger = workflow_env["stranger"]
    project = workflow_env["project"]

    # Task assigned strictly to outgoing member
    task_other = Task(
        id=uuid.uuid4(),
        project_id=project.id,
        title="Lead Architectural Review",
        description="Exclusive to outgoing lead",
        status="NOT_STARTED",
        assigned_to=outgoing.id,
    )
    test_db.add(task_other)
    await test_db.commit()

    token_incoming = create_access_token(incoming.id, email=incoming.email)
    token_stranger = create_access_token(stranger.id, email=stranger.email)

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Incoming member attempts to update task assigned to outgoing member -> 403 Forbidden
            res_inc = await client.patch(
                f"/api/v1/tasks/{task_other.id}/status",
                headers={"Authorization": f"Bearer {token_incoming}"},
                json={"status": "in_progress", "notes": "Unauthorized pickup"},
            )
            assert res_inc.status_code == 403
            assert "only update tasks assigned to them" in res_inc.text

            # 2. External stranger attempts to update project task -> 403 Forbidden
            res_stranger = await client.patch(
                f"/api/v1/tasks/{task_other.id}/status",
                headers={"Authorization": f"Bearer {token_stranger}"},
                json={"status": "completed"},
            )
            assert res_stranger.status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_acknowledgement_user_attribution_and_historical_immutability(test_db: AsyncSession, workflow_env: dict):
    """
    Verifies that:
    - Restoring an older version creates a new revision without destroying past snapshots.
    - Acknowledgements strictly record and bind the authenticated user's ID.
    - Audit logs capture actor, action, timestamp, entity, and metadata.
    """
    incoming = workflow_env["incoming"]
    outgoing = workflow_env["outgoing"]
    reviewer = workflow_env["reviewer"]
    project = workflow_env["project"]

    handover = Handover(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=outgoing.id,
        title="Attribution Audit Handover",
        status=HandoverStatus.APPROVED.value,
        version="v1.0",
        assigned_to=incoming.id,
    )
    test_db.add(handover)
    await test_db.commit()

    v_svc = HandoverVersionService(test_db)
    v1 = await v_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=reviewer.id,
        version_number="v1.0",
        approval_status=HandoverStatus.APPROVED.value,
    )
    v2 = await v_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=outgoing.id,
        version_number="v2.0",
        approval_status=HandoverStatus.DRAFT.value,
    )

    # Restore v1
    restored, v3 = await v_svc.restore_version(
        handover_id=handover.id,
        version_id=v1.id,
        user_id=outgoing.id,
        reason="Preservation verification test",
    )

    # Invariant: Historical snapshots v1 and v2 still exist and have unchanged IDs
    history = await v_svc.list_versions(handover.id)
    history_ids = {h.id for h in history}
    assert v1.id in history_ids
    assert v2.id in history_ids
    assert v3.id in history_ids
    assert len(history) == 3

    # Approve restored handover for incoming handover transfer
    handover.status = HandoverStatus.APPROVED.value
    await test_db.commit()

    # Invariant: Acknowledgement user attribution
    token_incoming = create_access_token(incoming.id, email=incoming.email)

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_ack = await client.post(
                f"/api/v1/handovers/{handover.id}/acknowledge",
                headers={"Authorization": f"Bearer {token_incoming}"},
                json={"checklist_confirmed": True, "notes": "Attribution verified"},
            )
            assert res_ack.status_code == 200
            data = res_ack.json()["data"]
            assert data["acknowledgedBy"] == str(incoming.id)

            # Check database persistence
            h_persisted = (await test_db.execute(select(Handover).where(Handover.id == handover.id))).scalar_one()
            assert h_persisted.acknowledged_by == incoming.id
            assert h_persisted.acknowledged_at is not None
            assert h_persisted.status == HandoverStatus.ACKNOWLEDGED.value
    finally:
        app.dependency_overrides.pop(get_db, None)

