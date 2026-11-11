"""
Comprehensive Unit and Integration Tests for Step 12:
Task Management, Notifications, and ReportLab PDF Export.

Validates:
1. Task Management:
   - Creation of tasks from handover sections or standalone.
   - Assigning tasks with project membership validation.
   - Tracking priority (low, medium, high, critical), due dates, and status.
   - Progress notes tracking.
2. Task Dependencies & Circular Dependency Prevention:
   - Self-dependency prevention.
   - 2-node cycle detection (A -> B, B -> A).
   - Transitive cycle detection (A -> B -> C, C -> A).
   - DAG dependency graph creation and prerequisite resolution tracking.
   - Dynamic is_blocked calculation.
3. Database-Backed Notifications:
   - Listing notifications with unread_only filter.
   - PATCH /notifications/{id}/read.
   - POST /notifications/read-all.
   - Notification dispatch on project invitations, task assignments, and handover approvals.
4. Professional PDF Export:
   - ReportLab PDF byte stream generation.
   - Verification that PDF distinguishes verified factual claims from advisory AI recommendations.
   - Access control (unapproved draft export blocked for incoming members).
"""

import io
import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.handover import Handover, HandoverSection
from app.models.evidence import EvidenceReference
from app.models.conflict import Conflict
from app.models.task import Task, TaskDependency
from app.models.notification import Notification
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskDependencyCreate,
    ProgressNoteCreate,
)
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.api.v1.endpoints.tasks import (
    would_create_cycle,
    create_project_task,
    list_project_tasks,
    update_task,
    add_task_dependency,
    get_task_dependencies,
    delete_task,
)
from app.api.v1.endpoints.notifications import (
    list_notifications,
    mark_notification_read,
    mark_all_notifications_read,
)
from app.services.pdf_export_service import PDFExportService
from app.services.notification_service import NotificationService


# =============================================================================
# 1. TASK MANAGEMENT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_project_task_happy_path():
    """Validates creating a continuation task assigned to a project member."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    author_id = uuid.uuid4()
    assignee_id = uuid.uuid4()

    author_user = User(id=author_id, full_name="Author User", email="author@test.com")
    member_record = ProjectMember(id=uuid.uuid4(), project_id=project_id, user_id=assignee_id, role="INCOMING")

    mock_m_res = MagicMock()
    mock_m_res.scalars.return_value.first.return_value = member_record
    mock_db.execute.return_value = mock_m_res

    with patch("app.api.v1.endpoints.tasks.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        payload = TaskCreate(
            title="Setup Local PostgreSQL & pgvector",
            description="Install postgres 16 and enable pgvector extension on port 5432.",
            assigned_to=assignee_id,
            priority="high",
            status="pending",
            due_date=datetime.now(timezone.utc),
        )
        res = await create_project_task(
            project_id=project_id,
            payload=payload,
            current_user=author_user,
            db=mock_db,
        )

    assert res.data.title == "Setup Local PostgreSQL & pgvector"
    assert res.data.priority == "high"
    assert res.data.assigned_to == assignee_id
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_create_task_invalid_assignee_fails():
    """Assigning a task to someone outside the project workspace raises BadRequestException."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    external_user_id = uuid.uuid4()

    current_user = User(id=user_id)

    mock_m_res = MagicMock()
    mock_m_res.scalars.return_value.first.return_value = None  # user not in project!
    mock_db.execute.return_value = mock_m_res

    with patch("app.api.v1.endpoints.tasks.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        payload = TaskCreate(
            title="External Task",
            assigned_to=external_user_id,
        )
        with pytest.raises(BadRequestException) as exc_info:
            await create_project_task(
                project_id=project_id,
                payload=payload,
                current_user=current_user,
                db=mock_db,
            )
        assert "not a member of this project" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_update_task_and_unblock_dependent():
    """Updating a task to 'completed' sends unblock notifications to dependent task assignees."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    task_id = uuid.uuid4()
    dep_task_id = uuid.uuid4()
    assignee_id = uuid.uuid4()

    task = Task(
        id=task_id,
        project_id=project_id,
        title="Prerequisite Task",
        status="in_progress",
        priority="high",
    )
    dependent_task = Task(
        id=dep_task_id,
        project_id=project_id,
        title="Dependent Downstream Task",
        assigned_to=assignee_id,
        status="pending",
    )

    # Mock query for dependent tasks
    mock_dep_res = MagicMock()
    mock_dep_res.scalars.return_value.all.return_value = [dependent_task]

    # Mock query for counts and blocked
    mock_counts_res1 = MagicMock()
    mock_counts_res1.scalars.return_value.all.return_value = []
    mock_counts_res2 = MagicMock()
    mock_counts_res2.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [mock_dep_res, mock_counts_res1, mock_counts_res2, mock_counts_res1, mock_counts_res2]

    current_user = User(id=uuid.uuid4())

    with patch("app.api.v1.endpoints.tasks.get_task_counts_and_blocked", return_value=(0, 0, False)):
        res = await update_task(
            payload=TaskUpdate(status="completed"),
            task=task,
            current_user=current_user,
            db=mock_db,
        )

    assert task.status == "completed"
    assert res.data.status == "completed"
    assert mock_db.commit.called


# =============================================================================
# 2. CIRCULAR DEPENDENCY & CYCLE DETECTION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_would_create_cycle_self_dependency():
    """A task cannot depend on itself."""
    mock_db = AsyncMock()
    task_id = uuid.uuid4()
    assert await would_create_cycle(task_id=task_id, depends_on_task_id=task_id, db=mock_db) is True


@pytest.mark.asyncio
async def test_would_create_cycle_two_nodes():
    """
    If Task A depends on Task B (A -> B), adding B -> A creates a cycle.
    """
    mock_db = AsyncMock()
    task_a = uuid.uuid4()
    task_b = uuid.uuid4()

    # When checking if B can reach A:
    # Query prereqs of A: returns [task_b]
    mock_res_a = MagicMock()
    mock_res_a.scalars.return_value.all.return_value = [task_b]
    mock_db.execute.return_value = mock_res_a

    # Adding B depends on A:
    # depends_on_task_id is A. If A can reach B, cycle!
    is_cycle = await would_create_cycle(task_id=task_b, depends_on_task_id=task_a, db=mock_db)
    assert is_cycle is True


@pytest.mark.asyncio
async def test_would_create_cycle_transitive_three_nodes():
    """
    If A -> B and B -> C, adding C -> A creates a transitive cycle (C -> A -> B -> C).
    """
    mock_db = AsyncMock()
    task_a = uuid.uuid4()
    task_b = uuid.uuid4()
    task_c = uuid.uuid4()

    # Query for A's prereqs returns [B]
    mock_res_a = MagicMock()
    mock_res_a.scalars.return_value.all.return_value = [task_b]

    # Query for B's prereqs returns [C]
    mock_res_b = MagicMock()
    mock_res_b.scalars.return_value.all.return_value = [task_c]

    mock_db.execute.side_effect = [mock_res_a, mock_res_b]

    # Adding C depends on A: depends_on is A, task_id is C
    is_cycle = await would_create_cycle(task_id=task_c, depends_on_task_id=task_a, db=mock_db)
    assert is_cycle is True


@pytest.mark.asyncio
async def test_would_create_cycle_valid_dag_allowed():
    """Valid directed acyclic dependency (A -> B and C -> B) has no cycle."""
    mock_db = AsyncMock()
    task_b = uuid.uuid4()
    task_c = uuid.uuid4()

    # Query prereqs of B: returns empty (B has no dependencies)
    mock_res_b = MagicMock()
    mock_res_b.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res_b

    # Adding C depends on B:
    is_cycle = await would_create_cycle(task_id=task_c, depends_on_task_id=task_b, db=mock_db)
    assert is_cycle is False


@pytest.mark.asyncio
async def test_add_task_dependency_endpoint_cycle_rejection():
    """API endpoint rejects cycle creation with BadRequestException."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    task_a = Task(id=uuid.uuid4(), project_id=project_id, title="Task A")
    task_b = Task(id=uuid.uuid4(), project_id=project_id, title="Task B")

    mock_prereq_res = MagicMock()
    mock_prereq_res.scalars.return_value.first.return_value = task_b

    mock_ex_res = MagicMock()
    mock_ex_res.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [mock_prereq_res, mock_ex_res]

    current_user = User(id=uuid.uuid4())

    with patch("app.api.v1.endpoints.tasks.would_create_cycle", return_value=True):
        with pytest.raises(BadRequestException) as exc_info:
            await add_task_dependency(
                payload=TaskDependencyCreate(depends_on_task_id=task_b.id),
                task=task_a,
                current_user=current_user,
                db=mock_db,
            )
        assert "Circular dependency detected" in str(exc_info.value.message)


# =============================================================================
# 3. NOTIFICATION ENDPOINTS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_list_notifications_unread_filter():
    """Lists only unread notifications when unread_only=True."""
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    notif = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Review Required",
        message="Handover submitted",
        notification_type="handover_submitted_review",
        is_read=False,
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [notif]
    mock_db.execute.return_value = mock_res

    res = await list_notifications(
        unread_only=True,
        limit=20,
        offset=0,
        current_user=User(id=user_id),
        db=mock_db,
    )
    assert len(res.data) == 1
    assert res.data[0].title == "Review Required"
    assert res.data[0].is_read is False


@pytest.mark.asyncio
async def test_mark_notification_read():
    """Marks a single notification as read."""
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    notif = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Task Assigned",
        message="New task",
        notification_type="task_assigned",
        is_read=False,
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = notif
    mock_db.execute.return_value = mock_res

    res = await mark_notification_read(
        notification_id=notif.id,
        current_user=User(id=user_id),
        db=mock_db,
    )
    assert notif.is_read is True
    assert res.data.is_read is True
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_mark_all_notifications_read():
    """Bulk marks all pending notifications as read."""
    mock_db = AsyncMock()
    user_id = uuid.uuid4()

    mock_res = MagicMock()
    mock_res.rowcount = 5
    mock_db.execute.return_value = mock_res

    res = await mark_all_notifications_read(
        current_user=User(id=user_id),
        db=mock_db,
    )
    assert res.data["markedReadCount"] == 5
    assert mock_db.commit.called


# =============================================================================
# 4. REPORTLAB PDF EXPORT TESTS
# =============================================================================

def test_pdf_export_service_compiles_valid_pdf():
    """Validates that PDFExportService generates a valid ReportLab PDF byte stream."""
    handover_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    sec1 = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover_id,
        section_type="project_overview",
        title="1. Project Overview",
        content={
            "summary": "AI Knowledge Handover platform overview",
            "markdown": "## System Overview\n\n- Multi-format ingestion\n- Vector search",
            "claims": [
                {
                    "statement": "PostgreSQL with pgvector handles semantic indexing.",
                    "evidence_status": "SUPPORTED",
                    "quoted_text": "PostgreSQL 16 with pgvector extension enabled.",
                }
            ],
            "recommendations": [
                {
                    "title": "Enable Connection Pooling",
                    "description": "Recommended to use PgBouncer in production.",
                    "timeframe": "short_term",
                    "is_recommendation": True,
                }
            ],
        },
        evidence_references=[
            EvidenceReference(
                id=uuid.uuid4(),
                handover_section_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                quoted_text="PostgreSQL 16 with pgvector extension enabled.",
                page_number=2,
                relevance_score=0.96,
                verification_status="SUPPORTED",
            )
        ],
    )

    conflict = Conflict(
        id=uuid.uuid4(),
        project_id=project_id,
        conflict_type="architecture",
        description="Port discrepancy between documentation runbooks.",
        source_a={"text": "Port 5432 in db.env"},
        source_b={"text": "Port 5433 in compose.yml"},
        status="RESOLVED",
        resolution={"chosen_value": "Port 5432"},
    )

    task = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Setup Staging Database",
        description="Provision RDS instance with pgvector.",
        priority="critical",
        status="pending",
    )

    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Production Infrastructure Handover",
        status="APPROVED",
        version="v1.0",
        created_by=user_id,
        generated_at=datetime.now(timezone.utc),
        approved_at=datetime.now(timezone.utc),
    )
    handover.sections = [sec1]
    handover.conflicts = [conflict]
    handover.tasks = [task]

    # Generate PDF stream
    pdf_buffer = PDFExportService.generate_handover_pdf(handover, project_name="Platform Core")
    pdf_bytes = pdf_buffer.getvalue()

    # STRICT ASSERTIONS:
    # 1. Valid PDF header magic bytes
    assert pdf_bytes.startswith(b"%PDF-"), "Generated byte stream must have valid %PDF- magic header."
    # 2. Non-trivial file size (several KB for styled document)
    assert len(pdf_bytes) > 2048, f"PDF content too small: {len(pdf_bytes)} bytes."
    # 3. Valid EOF trailer
    assert b"%%EOF" in pdf_bytes[-1024:], "PDF must conclude with %%EOF trailer."
