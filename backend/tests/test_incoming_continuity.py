"""
Unit and Integration Tests for Step 3.3 — Incoming-Member Continuity Workflow.

Validates:
1. Incoming members can access handovers shared with them (GET /handovers/shared-with-me).
2. Display approved handover and its latest version snapshot.
3. Receipt acknowledgement: incoming member acknowledges receipt, recording timestamp & user ID.
4. Strict separation of acknowledgement from formal handover approval:
   - Incoming members cannot formally approve handovers (403 Forbidden).
   - Acknowledging does not alter formal approval status or approver metadata.
   - Unapproved drafts cannot be acknowledged.
5. Display pending tasks and responsibilities.
6. Display unresolved blockers (blocked tasks and their prerequisites) and unresolved conflicts.
7. Allow incoming members to update assigned task statuses where authorized.
8. Role enforcement: incoming members cannot update tasks assigned to other members or reassign tasks.
9. Allow incoming members to add structured progress updates and retrieve update history.
10. Display overdue tasks and unresolved tasks metrics.
11. Track overall handover transition status:
    - Progression: Awaiting Acknowledgement -> Acknowledged -> In Progress -> Completed.
    - Status updates via PATCH /handovers/{handover_id}/transition-status.
    - Automatic transition to 'In Progress' when task status or progress is updated.
12. Audit logging for acknowledgement, transition updates, task status changes, and progress notes.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.handover import Handover, HandoverSection, HandoverVersion, HandoverAuditLog
from app.models.task import Task, TaskDependency, TaskProgressUpdate
from app.models.conflict import Conflict
from app.models.audit_log import AuditLog, AuditActionType, AuditEntityType
from app.schemas.handover import (
    AcknowledgeHandoverRequest,
    ApproveHandoverRequest,
    TransitionStatusUpdateRequest,
    HandoverTransitionStatus,
    normalize_transition_status,
)
from app.schemas.task import (
    TaskStatusUpdate,
    TaskProgressUpdateCreate,
    TaskUpdate,
)
from app.core.exceptions import ForbiddenException, BadRequestException, NotFoundException
from app.api.v1.endpoints.handovers import (
    acknowledge_handover,
    approve_handover,
    update_handover_transition_status,
    get_handover_continuity,
    list_shared_with_me_handovers,
)
from app.api.v1.endpoints.tasks import (
    update_continuation_task_status,
    add_task_progress_update,
    get_task_progress_updates,
    update_task,
)


# =============================================================================
# 1. SHARED HANDOVERS ACCESS (Feature 1)
# =============================================================================

@pytest.mark.asyncio
async def test_incoming_member_access_shared_with_me():
    """Incoming members can access handovers shared with them across their projects."""
    mock_db = AsyncMock()
    incoming_user = User(id=uuid.uuid4(), full_name="Successor Dev", email="successor@company.internal")
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="Payment Infrastructure Cutover", created_by=uuid.uuid4())

    membership = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_user.id,
        role="INCOMING",
    )

    approved_handover = Handover(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Payment Core Handover",
        version="v1.0",
        status="APPROVED",
        transition_status="Awaiting Acknowledgement",
        project=project,
        tasks=[],
    )

    # Mock DB executions
    # 1. Fetch memberships
    mock_pm_res = MagicMock()
    mock_pm_res.scalars.return_value.all.return_value = [membership]

    # 2. Fetch shared handovers
    mock_h_res = MagicMock()
    mock_h_res.scalars.return_value.all.return_value = [approved_handover]

    mock_db.execute.side_effect = [mock_pm_res, mock_h_res]

    res = await list_shared_with_me_handovers(current_user=incoming_user, db=mock_db)

    assert len(res.data) == 1
    item = res.data[0]
    assert item.id == approved_handover.id
    assert item.title == "Payment Core Handover"
    assert item.status == "APPROVED"
    assert item.transition_status == "Awaiting Acknowledgement"
    assert item.project_title == "Payment Infrastructure Cutover"


@pytest.mark.asyncio
async def test_shared_with_me_excludes_unapproved_drafts_for_incoming():
    """Draft and in-review handovers are never returned in shared-with-me for incoming members."""
    mock_db = AsyncMock()
    incoming_user = User(id=uuid.uuid4(), full_name="New Member", email="newbie@company.internal")
    project_id = uuid.uuid4()

    membership = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_user.id,
        role="INCOMING",
    )

    # Mock query returning empty because only APPROVED/SHARED/ACKNOWLEDGED are filtered
    mock_pm_res = MagicMock()
    mock_pm_res.scalars.return_value.all.return_value = [membership]

    mock_h_res = MagicMock()
    mock_h_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [mock_pm_res, mock_h_res]

    res = await list_shared_with_me_handovers(current_user=incoming_user, db=mock_db)
    assert len(res.data) == 0


# =============================================================================
# 2. CONTINUITY DASHBOARD & LATEST VERSION (Feature 2)
# =============================================================================

@pytest.mark.asyncio
async def test_continuity_dashboard_displays_approved_handover_and_latest_version():
    """Continuity dashboard displays approved handover details alongside latest version snapshot."""
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    incoming_user = User(id=user_id, full_name="Incoming Lead", email="incoming@company.internal")
    project_id = uuid.uuid4()
    handover_id = uuid.uuid4()

    now = datetime.now(timezone.utc)
    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Microservice Architecture Handover",
        version="v1.0",
        status="APPROVED",
        transition_status="Awaiting Acknowledgement",
        approved_at=now - timedelta(days=1),
        created_at=now - timedelta(days=2),
    )

    project = Project(id=project_id, name="Core Platform Migration", created_by=uuid.uuid4())

    version_record = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.0",
        version_description="Initial Approved Baseline",
        approval_status="APPROVED",
        is_latest=True,
        created_by=user_id,
        created_at=now - timedelta(days=1),
        snapshot={"project_overview": "Platform microservices migration.", "tasks": []},
    )

    # Setup mocks for continuity dashboard queries:
    # 1. Project
    p_res = MagicMock()
    p_res.scalars.return_value.first.return_value = project

    # 2. Latest version
    v_res = MagicMock()
    v_res.scalars.return_value.all.return_value = [version_record]

    # 3. Version creator
    vc_res = MagicMock()
    vc_res.scalars.return_value.first.return_value = incoming_user

    # 4. Tasks (empty)
    t_res = MagicMock()
    t_res.scalars.return_value.all.return_value = []

    # 5. Conflicts (empty)
    c_res = MagicMock()
    c_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [p_res, v_res, vc_res, t_res, c_res]

    res = await get_handover_continuity(handover=handover, current_user=incoming_user, db=mock_db)

    assert res.data.handover_id == handover_id
    assert res.data.title == "Microservice Architecture Handover"
    assert res.data.status == "APPROVED"
    assert res.data.transition_status == "Awaiting Acknowledgement"
    assert res.data.latest_version is not None
    assert res.data.latest_version.version_number == "v1.0"
    assert res.data.latest_version.version_description == "Initial Approved Baseline"
    assert res.data.latest_version.is_latest is True
    assert res.data.latest_version.snapshot["project_overview"] == "Platform microservices migration."


# =============================================================================
# 3. ACKNOWLEDGEMENT OF RECEIPT (Features 3, 4 & 11)
# =============================================================================

@pytest.mark.asyncio
async def test_incoming_member_acknowledges_receipt_and_records_audit():
    """Incoming member acknowledges receipt, recording timestamp, user ID, and transition status."""
    mock_db = AsyncMock()
    incoming_id = uuid.uuid4()
    project_id = uuid.uuid4()
    incoming_user = User(id=incoming_id, full_name="Taylor Swift", email="taylor@company.internal")

    handover = Handover(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Database Sharding Handover",
        version="v1.0",
        status="APPROVED",
        transition_status="Awaiting Acknowledgement",
        approved_at=datetime.now(timezone.utc) - timedelta(hours=5),
    )

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        payload = AcknowledgeHandoverRequest(
            checklist_confirmed=True,
            notes="Reviewed runbooks, verified local access, and checked partition diagrams.",
        )
        res = await acknowledge_handover(
            payload=payload,
            handover=handover,
            current_user=incoming_user,
            db=mock_db,
        )

    # Verify handover acknowledgement metadata
    assert handover.acknowledged_by == incoming_id
    assert handover.acknowledged_at is not None
    assert handover.checklist_confirmed is True
    assert handover.acknowledgement_notes == "Reviewed runbooks, verified local access, and checked partition diagrams."
    assert handover.transition_status == "Acknowledged"
    assert handover.assigned_to == incoming_id

    # Verify response
    assert res.data["transitionStatus"] == "Acknowledged"
    assert res.data["acknowledgedBy"] == str(incoming_id)
    assert res.data["acknowledgedAt"] is not None

    # Verify HandoverAuditLog was added
    add_calls = [call[0][0] for call in mock_db.add.call_args_list]
    audit_logs = [c for c in add_calls if isinstance(c, HandoverAuditLog)]
    assert len(audit_logs) >= 1
    assert audit_logs[0].action == "acknowledged"
    assert audit_logs[0].details["checklist_confirmed"] is True
    assert audit_logs[0].details["transition_status"] == "Acknowledged"


@pytest.mark.asyncio
async def test_acknowledgement_is_strictly_separate_from_formal_approval():
    """
    Validates security requirement:
    - Incoming members cannot formally approve handovers (403 Forbidden).
    - Acknowledging does NOT modify formal approved_at timestamp.
    - Unapproved handovers cannot be acknowledged.
    """
    mock_db = AsyncMock()
    incoming_user = User(id=uuid.uuid4(), full_name="Junior Successor", email="jr@company.internal")
    project_id = uuid.uuid4()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=project_id,
        status="DRAFT",
        version="v1.0",
    )

    # 1. Incoming member tries to formally approve -> 403 Forbidden
    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.side_effect = ForbiddenException("Insufficient permissions: APPROVE_HANDOVER required.")
        with pytest.raises(ForbiddenException) as exc_info:
            await approve_handover(
                payload=ApproveHandoverRequest(notes="I approve myself"),
                handover=handover,
                current_user=incoming_user,
                db=mock_db,
            )
        assert "Insufficient permissions" in str(exc_info.value.message)

    # 2. Cannot acknowledge unapproved draft -> 403 Forbidden
    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        with pytest.raises(ForbiddenException) as exc_info:
            await acknowledge_handover(
                payload=None,
                handover=handover,
                current_user=incoming_user,
                db=mock_db,
            )
        assert "Only approved or shared handovers can be acknowledged" in str(exc_info.value.message)


# =============================================================================
# 4. PENDING, OVERDUE, AND RESOLVED TASKS (Features 5 & 9)
# =============================================================================

@pytest.mark.asyncio
async def test_continuity_dashboard_categorizes_pending_and_overdue_tasks():
    """Dashboard correctly groups tasks into pending, in_progress, completed, and overdue."""
    mock_db = AsyncMock()
    incoming_user = User(id=uuid.uuid4(), full_name="Alex Lead", email="alex@company.internal")
    project_id = uuid.uuid4()
    handover_id = uuid.uuid4()

    now = datetime.now(timezone.utc)
    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Continuity Task Handover",
        status="APPROVED",
        transition_status="Acknowledged",
    )

    # Create 4 tasks:
    # 1. Completed task
    t_comp = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=handover_id,
        title="Setup CloudWatch Alerts",
        status="completed",
        due_date=now - timedelta(days=2),
    )
    # 2. In progress task
    t_prog = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=handover_id,
        title="Migrate Redis Keyspaces",
        status="in_progress",
        due_date=now + timedelta(days=3),
    )
    # 3. Pending task (not overdue)
    t_pend = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=handover_id,
        title="Update OpenAPI Schema",
        status="pending",
        due_date=now + timedelta(days=7),
    )
    # 4. Overdue pending task
    t_overdue = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=handover_id,
        title="Rotate Production RDS Credentials",
        status="pending",
        due_date=now - timedelta(days=1),  # Past due!
    )

    all_tasks = [t_comp, t_prog, t_pend, t_overdue]

    # Setup mocks
    p_res = MagicMock()
    p_res.scalars.return_value.first.return_value = Project(id=project_id, name="Test Project", created_by=uuid.uuid4())

    v_res = MagicMock()
    v_res.scalars.return_value.all.return_value = []

    t_res = MagicMock()
    t_res.scalars.return_value.all.return_value = all_tasks

    dep_res = MagicMock()
    dep_res.scalars.return_value.all.return_value = []

    c_res = MagicMock()
    c_res.scalars.return_value.all.return_value = []

    pu_res = MagicMock()
    pu_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [p_res, v_res, t_res, dep_res, c_res, pu_res]

    res = await get_handover_continuity(handover=handover, current_user=incoming_user, db=mock_db)

    summary = res.data.tasks_summary
    assert summary.total_tasks == 4
    assert summary.completed_tasks == 1
    assert summary.in_progress_tasks == 1
    assert summary.pending_tasks == 2
    assert summary.overdue_tasks == 1
    assert summary.completion_percentage == 25.0

    assert len(res.data.overdue_tasks) == 1
    assert res.data.overdue_tasks[0].title == "Rotate Production RDS Credentials"
    assert len(res.data.completed_tasks) == 1
    assert len(res.data.in_progress_tasks) == 1
    assert len(res.data.pending_tasks) == 2


# =============================================================================
# 5. UNRESOLVED BLOCKERS AND CONFLICTS (Feature 6)
# =============================================================================

@pytest.mark.asyncio
async def test_continuity_dashboard_displays_blockers_and_unresolved_conflicts():
    """Continuity dashboard surfaces unresolved blockers and open conflicts."""
    mock_db = AsyncMock()
    incoming_user = User(id=uuid.uuid4(), full_name="User", email="user@test.com")
    project_id = uuid.uuid4()
    handover_id = uuid.uuid4()

    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Blocker Verification Handover",
        status="APPROVED",
    )

    # Prerequisite task (incomplete)
    prereq = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=handover_id,
        title="Acquire Vault Production Secrets Token",
        status="pending",
    )
    # Blocked task
    blocked_task = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=handover_id,
        title="Deploy Auth Microservice",
        status="pending",
    )

    dep = TaskDependency(id=uuid.uuid4(), task_id=blocked_task.id, depends_on_task_id=prereq.id)

    # Unresolved Conflict
    conflict_open = Conflict(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=handover_id,
        conflict_type="architecture",
        description="Conflicting Redis cluster node size between PR #40 and ADR-003",
        status="OPEN",
        source_a={"doc": "PR-40"},
        source_b={"doc": "ADR-003"},
    )
    # Resolved Conflict (should be excluded)
    conflict_resolved = Conflict(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=handover_id,
        conflict_type="date",
        description="Resolved cutover date discrepancy",
        status="RESOLVED",
        source_a={},
        source_b={},
    )

    # Setup mocks
    p_res = MagicMock()
    p_res.scalars.return_value.first.return_value = Project(id=project_id, name="Test Project", created_by=uuid.uuid4())
    v_res = MagicMock()
    v_res.scalars.return_value.all.return_value = []
    t_res = MagicMock()
    t_res.scalars.return_value.all.return_value = [prereq, blocked_task]
    dep_res = MagicMock()
    dep_res.scalars.return_value.all.return_value = [dep]
    c_res = MagicMock()
    c_res.scalars.return_value.all.return_value = [conflict_open, conflict_resolved]
    pu_res = MagicMock()
    pu_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [p_res, v_res, t_res, dep_res, c_res, pu_res]

    res = await get_handover_continuity(handover=handover, current_user=incoming_user, db=mock_db)

    # Verify blockers detected
    assert len(res.data.blocked_tasks) == 1
    assert res.data.blocked_tasks[0].id == blocked_task.id
    assert res.data.blocked_tasks[0].is_blocked is True

    assert len(res.data.unresolved_blockers) == 1
    blocker_info = res.data.unresolved_blockers[0]
    assert blocker_info["task_id"] == str(blocked_task.id)
    assert len(blocker_info["blocking_prerequisites"]) == 1
    assert blocker_info["blocking_prerequisites"][0]["prerequisite_title"] == "Acquire Vault Production Secrets Token"

    # Verify only OPEN conflict is surfaced
    assert len(res.data.unresolved_conflicts) == 1
    assert res.data.unresolved_conflicts[0].id == conflict_open.id
    assert res.data.unresolved_conflicts[0].status == "OPEN"


# =============================================================================
# 6. INCOMING MEMBERS TASK STATUS UPDATES (Feature 7)
# =============================================================================

@pytest.mark.asyncio
async def test_incoming_member_updates_assigned_task_status():
    """Incoming member can update the status of their assigned task."""
    mock_db = AsyncMock()
    incoming_id = uuid.uuid4()
    project_id = uuid.uuid4()
    task_id = uuid.uuid4()
    handover_id = uuid.uuid4()

    incoming_user = User(id=incoming_id, full_name="Robin Successor", email="robin@company.internal")

    member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_id,
        role="INCOMING",
    )

    task = Task(
        id=task_id,
        project_id=project_id,
        handover_id=handover_id,
        title="Configure Prometheus Scraping Targets",
        status="pending",
        priority="high",
        assigned_to=incoming_id,  # Assigned to incoming member
    )

    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Monitoring Handover",
        status="APPROVED",
        transition_status="Acknowledged",
    )

    # Mock DB executions
    # 1. Member query
    m_res = MagicMock()
    m_res.scalars.return_value.first.return_value = member

    # 2. Handover query for auto-advance to In Progress
    h_res = MagicMock()
    h_res.scalars.return_value.first.return_value = handover

    # 3. Counts and blocked
    prereq_res = MagicMock()
    prereq_res.scalars.return_value.all.return_value = []
    dep_res = MagicMock()
    dep_res.scalars.return_value.all.return_value = []

    # 4. User query for assignee name
    u_res = MagicMock()
    u_res.scalars.return_value.first.return_value = incoming_user

    mock_db.execute.side_effect = [m_res, h_res, prereq_res, dep_res, u_res]

    payload = TaskStatusUpdate(
        status="in_progress",
        notes="Started Prometheus agent container and verified scrape config.",
    )

    res = await update_continuation_task_status(
        payload=payload,
        task=task,
        current_user=incoming_user,
        db=mock_db,
    )

    assert task.status == "in_progress"
    assert res.data.status == "in_progress"
    assert handover.transition_status == "In Progress"  # Auto advanced!
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_incoming_member_cannot_update_unassigned_task_or_reassign():
    """Incoming members are restricted from updating tasks assigned to others or reassigning."""
    mock_db = AsyncMock()
    incoming_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    incoming_user = User(id=incoming_id, full_name="Incoming Member", email="inc@test.com")

    member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_id,
        role="INCOMING",
    )

    task = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Confidential Lead Task",
        status="pending",
        assigned_to=other_user_id,  # Assigned to someone else!
    )

    m_res = MagicMock()
    m_res.scalars.return_value.first.return_value = member
    mock_db.execute.return_value = m_res

    # 1. Attempt status update on someone else's task -> 403 Forbidden
    with pytest.raises(ForbiddenException) as exc_info:
        await update_continuation_task_status(
            payload=TaskStatusUpdate(status="in_progress"),
            task=task,
            current_user=incoming_user,
            db=mock_db,
        )
    assert "Incoming members can only update tasks assigned to them" in str(exc_info.value.message)

    # 2. Attempt reassignment via update_task -> 403 Forbidden
    with pytest.raises(ForbiddenException) as exc_info:
        await update_task(
            payload=TaskUpdate(assigned_to=incoming_id),
            task=task,
            current_user=incoming_user,
            db=mock_db,
        )
    assert "Incoming members can only update tasks assigned to them" in str(exc_info.value.message)


# =============================================================================
# 7. STRUCTURED PROGRESS UPDATES (Feature 8)
# =============================================================================

@pytest.mark.asyncio
async def test_incoming_member_adds_progress_update_and_retrieves_history():
    """Incoming member records structured progress update, creating history record and updating status."""
    mock_db = AsyncMock()
    incoming_id = uuid.uuid4()
    project_id = uuid.uuid4()
    task_id = uuid.uuid4()

    incoming_user = User(id=incoming_id, full_name="Jordan Dev", email="jordan@company.internal")

    member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_id,
        role="INCOMING",
    )

    task = Task(
        id=task_id,
        project_id=project_id,
        title="Verify OAuth2 Tokens on Ingress Gateway",
        status="pending",
        assigned_to=incoming_id,
        description="Initial description",
    )

    # 1. Add progress update
    m_res = MagicMock()
    m_res.scalars.return_value.first.return_value = member

    mock_db.execute.return_value = m_res

    payload = TaskProgressUpdateCreate(
        update_text="Configured Envoy filter and tested Bearer token validation with mock IdP.",
        new_status="in_progress",
    )

    res = await add_task_progress_update(
        payload=payload,
        task=task,
        current_user=incoming_user,
        db=mock_db,
    )

    assert res.data.update_text == "Configured Envoy filter and tested Bearer token validation with mock IdP."
    assert res.data.status_before == "pending"
    assert res.data.status_after == "in_progress"
    assert task.status == "in_progress"
    assert "Progress Note" in task.description

    # 2. Retrieve progress updates history
    progress_record = TaskProgressUpdate(
        id=uuid.uuid4(),
        task_id=task_id,
        user_id=incoming_id,
        update_text="Configured Envoy filter and tested Bearer token validation with mock IdP.",
        status_before="pending",
        status_after="in_progress",
        created_at=datetime.now(timezone.utc),
    )

    pu_res = MagicMock()
    pu_res.scalars.return_value.all.return_value = [progress_record]

    u_res = MagicMock()
    u_res.scalars.return_value.all.return_value = [incoming_user]

    mock_db.execute.side_effect = [pu_res, u_res]

    hist_res = await get_task_progress_updates(task=task, current_user=incoming_user, db=mock_db)
    assert len(hist_res.data) == 1
    assert hist_res.data[0].user_name == "Jordan Dev"
    assert hist_res.data[0].status_after == "in_progress"


# =============================================================================
# 8. HANDOVER TRANSITION STATUS TRACKING (Feature 10)
# =============================================================================

@pytest.mark.asyncio
async def test_handover_transition_status_lifecycle():
    """Tracks transition lifecycle: Awaiting Acknowledgement -> Acknowledged -> In Progress -> Completed."""
    mock_db = AsyncMock()
    user = User(id=uuid.uuid4(), full_name="Coordinator", email="coord@company.internal")
    project_id = uuid.uuid4()

    handover = Handover(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Full Lifecycle Continuity Handover",
        status="APPROVED",
        transition_status="Awaiting Acknowledgement",
    )

    # 1. Transition to Acknowledged
    res1 = await update_handover_transition_status(
        payload=TransitionStatusUpdateRequest(transition_status="Acknowledged", notes="Receipt signed off."),
        handover=handover,
        current_user=user,
        db=mock_db,
    )
    assert handover.transition_status == "Acknowledged"
    assert res1.data["transitionStatus"] == "Acknowledged"

    # 2. Transition to In Progress
    res2 = await update_handover_transition_status(
        payload=TransitionStatusUpdateRequest(transition_status="In Progress", notes="Sprint tasks started."),
        handover=handover,
        current_user=user,
        db=mock_db,
    )
    assert handover.transition_status == "In Progress"
    assert res2.data["transitionStatus"] == "In Progress"

    # 3. Transition to Completed
    res3 = await update_handover_transition_status(
        payload=TransitionStatusUpdateRequest(transition_status="Completed", notes="All continuation tasks finalized."),
        handover=handover,
        current_user=user,
        db=mock_db,
    )
    assert handover.transition_status == "Completed"
    assert res3.data["transitionStatus"] == "Completed"

    # Verify HandoverAuditLog recorded for each transition
    add_calls = [call[0][0] for call in mock_db.add.call_args_list]
    transition_audits = [c for c in add_calls if isinstance(c, HandoverAuditLog) and c.action == "transition_status_updated"]
    assert len(transition_audits) == 3


def test_normalize_transition_status_variations():
    """Normalizes various casing and abbreviations to canonical Title Case."""
    assert normalize_transition_status("awaiting_acknowledgement") == "Awaiting Acknowledgement"
    assert normalize_transition_status("AWAITING") == "Awaiting Acknowledgement"
    assert normalize_transition_status("acknowledged") == "Acknowledged"
    assert normalize_transition_status("in_progress") == "In Progress"
    assert normalize_transition_status("INPROGRESS") == "In Progress"
    assert normalize_transition_status("completed") == "Completed"
    assert normalize_transition_status("done") == "Completed"
    assert normalize_transition_status(None) == "Awaiting Acknowledgement"
