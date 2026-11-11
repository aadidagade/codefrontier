"""
Comprehensive Unit and Integration Tests for Step 11:
Handover Review, Approval, and Sharing Workflow.

Covers:
1. Full Handover Lifecycle:
   DRAFT -> IN_REVIEW -> CHANGES_REQUESTED -> IN_REVIEW -> APPROVED -> SHARED -> ACKNOWLEDGED.
2. Versioning and Approved Snapshot Immutability:
   Editing sections of an approved handover creates a snapshot of the approved version,
   bumps the version (v1.0 -> v1.1), and resets status to DRAFT for re-review.
3. Role-Based Permissions & Guardrails:
   - Outgoing submits review, edits drafts.
   - Lead / Admin requests changes, approves, rejects.
   - Incoming member accesses ONLY approved/shared/acknowledged handovers.
   - Incoming member acknowledges handover.
   - Unauthorized role attempts raise 403 Forbidden.
4. Invalid State Transitions:
   - Cannot submit review if already approved/in review.
   - Cannot share unapproved drafts.
   - Cannot acknowledge unapproved drafts.
   - Cannot approve handovers with rejected sections.
5. Complete Audit Trail:
   Every action (generated, section_updated, submitted_for_review, changes_requested,
   approved, shared, acknowledged, version_bumped, rejected) is logged with user_id & timestamp.
"""

import json
import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from app.schemas.handover import (
    HandoverStatus,
    SubmitReviewRequest,
    RequestChangesRequest,
    ApproveHandoverRequest,
    ShareHandoverRequest,
    AcknowledgeHandoverRequest,
    RejectHandoverRequest,
    HandoverSectionUpdate,
    HandoverHistoryResponse,
)
from app.models.user import User
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.handover import Handover, HandoverSection, HandoverAuditLog, HandoverVersion
from app.models.evidence import EvidenceReference
from app.models.conflict import Conflict
from app.models.task import Task
from app.models.notification import Notification
from app.core.exceptions import ForbiddenException, BadRequestException, NotFoundException
from app.dependencies.authorization import require_handover_access
from app.api.v1.endpoints.handovers import (
    increment_version,
    build_handover_snapshot,
    submit_handover_review,
    request_changes,
    approve_handover,
    share_handover,
    acknowledge_handover,
    reject_handover,
    update_handover_section,
    get_handover_history,
)


# =============================================================================
# 1. UNIT TESTS: STATUS ENUM & VERSION INCREMENT
# =============================================================================

def test_handover_status_enum_values():
    """Validates that HandoverStatus defines all 7 required lifecycle states."""
    expected = {
        "DRAFT",
        "IN_REVIEW",
        "CHANGES_REQUESTED",
        "APPROVED",
        "SHARED",
        "ACKNOWLEDGED",
        "REJECTED",
    }
    actual = {s.value for s in HandoverStatus}
    assert actual == expected


def test_increment_version_helper():
    """Validates semantic minor version increments across various formatting styles."""
    assert increment_version("v1.0") == "v1.1"
    assert increment_version("v1.1") == "v1.2"
    assert increment_version("v1.9") == "v1.10"
    assert increment_version("1.0") == "1.1"
    assert increment_version("v2") == "v2.1"
    assert increment_version("custom") == "custom.1"


def test_build_handover_snapshot_structure():
    """Validates that build_handover_snapshot creates a complete, immutable dictionary."""
    handover_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    section_id = uuid.uuid4()

    sec = HandoverSection(
        id=section_id,
        handover_id=handover_id,
        section_type="project_overview",
        title="1. Project Overview",
        content={"summary": "Overview summary", "markdown": "# Overview"},
        confidence=0.95,
        review_status="approved",
        sort_order=0,
        evidence_references=[
            EvidenceReference(
                id=uuid.uuid4(),
                handover_section_id=section_id,
                document_id=uuid.uuid4(),
                quoted_text="System runs PostgreSQL 16.",
                page_number=1,
                relevance_score=0.98,
                verification_status="SUPPORTED",
            )
        ],
    )

    conflict = Conflict(
        id=uuid.uuid4(),
        project_id=project_id,
        conflict_type="architecture",
        description="Port discrepancy",
        status="RESOLVED",
        resolution={"chosen_value": "port 5432"},
    )

    task = Task(
        id=uuid.uuid4(),
        title="Verify DB",
        description="Check connection",
        priority="high",
        status="pending",
    )

    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Production Architecture Handover",
        status="APPROVED",
        version="v1.0",
        created_by=user_id,
    )
    handover.sections = [sec]
    handover.conflicts = [conflict]
    handover.tasks = [task]

    snapshot = build_handover_snapshot(handover, user_id=user_id)

    assert snapshot["id"] == str(handover_id)
    assert snapshot["title"] == "Production Architecture Handover"
    assert snapshot["version"] == "v1.0"
    assert snapshot["status"] == "APPROVED"
    assert snapshot["approved_by"] == str(user_id)
    assert "snapshot_created_at" in snapshot
    assert len(snapshot["sections"]) == 1
    assert snapshot["sections"][0]["title"] == "1. Project Overview"
    assert len(snapshot["sections"][0]["evidence_references"]) == 1
    assert snapshot["sections"][0]["evidence_references"][0]["verification_status"] == "SUPPORTED"
    assert len(snapshot["conflicts"]) == 1
    assert len(snapshot["tasks"]) == 1


# =============================================================================
# 2. WORKFLOW STEP TESTS: SUBMIT REVIEW
# =============================================================================

@pytest.mark.asyncio
async def test_submit_handover_review_happy_path():
    """Outgoing member submits DRAFT handover for review -> status transitions to IN_REVIEW."""
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        created_by=user_id,
        title="API Handover",
        status="DRAFT",
        version="v1.0",
    )
    user = User(id=user_id, full_name="Alice Engineer", email="alice@test.com")

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        res = await submit_handover_review(
            payload=SubmitReviewRequest(notes="Ready for review by Lead."),
            handover=handover,
            current_user=user,
            db=mock_db,
        )

    assert res.data["status"] == "IN_REVIEW"
    assert handover.status == "IN_REVIEW"
    assert mock_db.commit.called
    assert mock_db.add.called
    added_audit = mock_db.add.call_args[0][0]
    assert isinstance(added_audit, HandoverAuditLog)
    assert added_audit.action == "submitted_for_review"
    assert added_audit.details["notes"] == "Ready for review by Lead."


@pytest.mark.asyncio
async def test_submit_handover_review_invalid_state():
    """Attempting to submit an already APPROVED or IN_REVIEW handover raises BadRequestException."""
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="APPROVED",
        version="v1.0",
    )
    user = User(id=user_id, full_name="Alice Engineer", email="alice@test.com")

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        with pytest.raises(BadRequestException) as exc_info:
            await submit_handover_review(
                payload=None,
                handover=handover,
                current_user=user,
                db=mock_db,
            )
        assert "Cannot submit handover for review" in str(exc_info.value.message)


# =============================================================================
# 3. WORKFLOW STEP TESTS: REQUEST CHANGES
# =============================================================================

@pytest.mark.asyncio
async def test_request_changes_happy_path():
    """Lead requests changes on IN_REVIEW handover -> status becomes CHANGES_REQUESTED."""
    mock_db = AsyncMock()
    lead_id = uuid.uuid4()
    section_id = uuid.uuid4()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="IN_REVIEW",
        version="v1.0",
    )
    lead_user = User(id=lead_id, full_name="Bob Lead", email="bob@test.com")

    mock_section = HandoverSection(id=section_id, handover_id=handover.id, review_status="pending")
    mock_sec_res = MagicMock()
    mock_sec_res.scalars.return_value.all.return_value = [mock_section]
    mock_db.execute.return_value = mock_sec_res

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        res = await request_changes(
            payload=RequestChangesRequest(
                feedback="Please update the database connection pool settings.",
                section_ids=[section_id],
            ),
            handover=handover,
            current_user=lead_user,
            db=mock_db,
        )

    assert res.data["status"] == "CHANGES_REQUESTED"
    assert handover.status == "CHANGES_REQUESTED"
    assert mock_section.review_status == "changes_requested"
    assert mock_db.commit.called
    added_audit = mock_db.add.call_args[0][0]
    assert isinstance(added_audit, HandoverAuditLog)
    assert added_audit.action == "changes_requested"
    assert "database connection pool" in added_audit.details["feedback"]


# =============================================================================
# 4. WORKFLOW STEP TESTS: APPROVE & IMMUTABLE SNAPSHOT
# =============================================================================

@pytest.mark.asyncio
async def test_approve_handover_creates_snapshot():
    """Lead approves handover -> status becomes APPROVED, snapshot created in HandoverVersion."""
    mock_db = AsyncMock()
    lead_id = uuid.uuid4()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Service Transition Handover",
        status="IN_REVIEW",
        version="v1.0",
    )
    handover.sections = [
        HandoverSection(
            id=uuid.uuid4(),
            handover_id=handover.id,
            section_type="project_overview",
            title="Overview",
            content={"summary": "all good"},
            review_status="approved",
            evidence_references=[],
        )
    ]
    handover.conflicts = []
    handover.tasks = []

    lead_user = User(id=lead_id, full_name="Bob Lead", email="bob@test.com")

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm, \
         patch("app.api.v1.endpoints.handovers.fetch_full_handover", return_value=handover):
        mock_perm.return_value = AsyncMock()
        res = await approve_handover(
            payload=ApproveHandoverRequest(notes="Looks comprehensive, approved for incoming team."),
            handover=handover,
            current_user=lead_user,
            db=mock_db,
        )

    assert res.data["status"] == "APPROVED"
    assert handover.status == "APPROVED"
    assert handover.approved_at is not None

    # Verify both version snapshot and audit log were added
    add_calls = [call[0][0] for call in mock_db.add.call_args_list]
    versions = [c for c in add_calls if isinstance(c, HandoverVersion)]
    audits = [c for c in add_calls if isinstance(c, HandoverAuditLog)]

    assert len(versions) == 1
    assert versions[0].version_number == "v1.0"
    assert versions[0].snapshot["status"] == "APPROVED"
    assert len(audits) == 1
    assert audits[0].action == "approved"


@pytest.mark.asyncio
async def test_approve_handover_with_rejected_section_fails():
    """Cannot approve a handover if any section is marked as rejected."""
    mock_db = AsyncMock()
    lead_id = uuid.uuid4()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="IN_REVIEW",
        version="v1.0",
    )
    handover.sections = [
        HandoverSection(
            id=uuid.uuid4(),
            handover_id=handover.id,
            section_type="technical_architecture",
            title="Technical Architecture",
            content={},
            review_status="rejected",
            evidence_references=[],
        )
    ]
    handover.conflicts = []
    handover.tasks = []
    lead_user = User(id=lead_id)

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm, \
         patch("app.api.v1.endpoints.handovers.fetch_full_handover", return_value=handover):
        mock_perm.return_value = AsyncMock()
        with pytest.raises(BadRequestException) as exc_info:
            await approve_handover(payload=None, handover=handover, current_user=lead_user, db=mock_db)
        assert "marked as rejected" in str(exc_info.value.message)


# =============================================================================
# 5. WORKFLOW STEP TESTS: SHARE WITH INCOMING MEMBERS
# =============================================================================

@pytest.mark.asyncio
async def test_share_handover_happy_path():
    """Sharing an approved handover transitions status to SHARED and notifies incoming member."""
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    incoming_id = uuid.uuid4()

    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Microservice Handover",
        status="APPROVED",
        version="v1.0",
    )
    current_user = User(id=user_id, full_name="Lead User")

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        res = await share_handover(
            payload=ShareHandoverRequest(assigned_to=incoming_id, notes="Welcome to the repo!"),
            handover=handover,
            current_user=current_user,
            db=mock_db,
        )

    assert res.data["status"] == "SHARED"
    assert handover.status == "SHARED"
    assert handover.shared_at is not None
    assert handover.assigned_to == incoming_id

    add_calls = [call[0][0] for call in mock_db.add.call_args_list]
    notifs = [c for c in add_calls if isinstance(c, Notification)]
    audits = [c for c in add_calls if isinstance(c, HandoverAuditLog)]

    assert len(notifs) == 1
    assert notifs[0].user_id == incoming_id
    assert notifs[0].notification_type == "handover_shared"
    assert len(audits) == 1
    assert audits[0].action == "shared"


@pytest.mark.asyncio
async def test_share_unapproved_handover_fails():
    """Attempting to share a DRAFT or IN_REVIEW handover raises ForbiddenException."""
    mock_db = AsyncMock()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="DRAFT",
        version="v1.0",
    )

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        with pytest.raises(ForbiddenException) as exc_info:
            await share_handover(payload=None, handover=handover, current_user=User(id=uuid.uuid4()), db=mock_db)
        assert "Only approved handovers can be shared" in str(exc_info.value.message)


# =============================================================================
# 6. WORKFLOW STEP TESTS: ACKNOWLEDGE RECEIPT
# =============================================================================

@pytest.mark.asyncio
async def test_acknowledge_handover_happy_path():
    """Incoming member acknowledges SHARED handover -> status becomes ACKNOWLEDGED."""
    mock_db = AsyncMock()
    incoming_id = uuid.uuid4()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="SHARED",
        version="v1.0",
    )
    incoming_user = User(id=incoming_id, full_name="Charlie Incoming")

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        res = await acknowledge_handover(
            payload=AcknowledgeHandoverRequest(
                checklist_confirmed=True,
                notes="Reviewed runbooks and verified local database setup.",
            ),
            handover=handover,
            current_user=incoming_user,
            db=mock_db,
        )

    assert res.data["status"] == "ACKNOWLEDGED"
    assert handover.status == "ACKNOWLEDGED"
    assert handover.assigned_to == incoming_id

    add_calls = [call[0][0] for call in mock_db.add.call_args_list]
    audits = [c for c in add_calls if isinstance(c, HandoverAuditLog)]
    assert len(audits) == 1
    assert audits[0].action == "acknowledged"
    assert audits[0].details["checklist_confirmed"] is True


@pytest.mark.asyncio
async def test_acknowledge_unapproved_handover_fails():
    """Incoming member cannot acknowledge a draft or in-review handover."""
    mock_db = AsyncMock()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="IN_REVIEW",
        version="v1.0",
    )

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        with pytest.raises(ForbiddenException) as exc_info:
            await acknowledge_handover(payload=None, handover=handover, current_user=User(id=uuid.uuid4()), db=mock_db)
        assert "Only approved or shared handovers can be acknowledged" in str(exc_info.value.message)


# =============================================================================
# 7. APPROVED IMMUTABILITY & VERSION BUMPING
# =============================================================================

@pytest.mark.asyncio
async def test_section_edit_on_approved_bumps_version_and_resets_to_draft():
    """
    Editing an APPROVED handover preserves the approved version in HandoverVersion,
    bumps version to v1.1, and resets status to DRAFT for human re-review.
    """
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    section_id = uuid.uuid4()

    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Stable Handover",
        status="APPROVED",
        version="v1.0",
        approved_at=datetime.now(timezone.utc),
    )
    section = HandoverSection(
        id=section_id,
        handover_id=handover.id,
        section_type="pending_tasks",
        title="Pending Tasks",
        content={"summary": "old tasks"},
        review_status="approved",
        evidence_references=[],
    )

    # Mock DB query for section and existing version
    mock_sec_res = MagicMock()
    mock_sec_res.scalars.return_value.first.return_value = section

    mock_version_res = MagicMock()
    mock_version_res.scalars.return_value.first.return_value = None  # snapshot doesn't exist yet, should create

    mock_db.execute.side_effect = [mock_sec_res, mock_version_res]

    current_user = User(id=user_id, full_name="Alice Engineer")

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm, \
         patch("app.api.v1.endpoints.handovers.fetch_full_handover", return_value=handover):
        mock_perm.return_value = AsyncMock()
        res = await update_handover_section(
            section_id=section_id,
            payload=HandoverSectionUpdate(
                title="Pending Tasks (Updated)",
                content={"summary": "New critical pending tasks"},
            ),
            handover=handover,
            current_user=current_user,
            db=mock_db,
        )

    # Immutability & Version Bump Assertions:
    assert handover.version == "v1.1"
    assert handover.status == "DRAFT"  # Reset to DRAFT for re-review!
    assert handover.approved_at is None
    assert section.title == "Pending Tasks (Updated)"

    add_calls = [call[0][0] for call in mock_db.add.call_args_list]
    versions = [c for c in add_calls if isinstance(c, HandoverVersion)]
    bump_audits = [c for c in add_calls if isinstance(c, HandoverAuditLog) and c.action == "version_bumped"]

    assert len(versions) == 1
    assert versions[0].version_number == "v1.0"  # Saved snapshot of the approved v1.0 state!
    assert len(bump_audits) == 1
    assert bump_audits[0].details["from_version"] == "v1.0"
    assert bump_audits[0].details["to_version"] == "v1.1"


# =============================================================================
# 8. INCOMING MEMBER DRAFT ISOLATION (IDOR & LEAKAGE PREVENTION)
# =============================================================================

@pytest.mark.asyncio
async def test_incoming_member_draft_isolation_guard():
    """Incoming members cannot view unapproved drafts (DRAFT, IN_REVIEW, CHANGES_REQUESTED)."""
    mock_db = AsyncMock()
    incoming_user = User(id=uuid.uuid4())
    draft_handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="DRAFT",
    )
    incoming_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=draft_handover.project_id,
        user_id=incoming_user.id,
        role=ProjectMemberRole.INCOMING.value,
    )

    # Mock DB queries: 1. find handover, 2. find member
    mock_h_res = MagicMock()
    mock_h_res.scalars.return_value.first.return_value = draft_handover

    mock_m_res = MagicMock()
    mock_m_res.scalars.return_value.first.return_value = incoming_member

    mock_db.execute.side_effect = [mock_h_res, mock_m_res]

    with pytest.raises(ForbiddenException) as exc_info:
        await require_handover_access(
            handover_id=draft_handover.id,
            current_user=incoming_user,
            db=mock_db,
        )
    assert "Incoming members can only access handovers after authorized approval" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_incoming_member_can_access_approved_and_shared():
    """Incoming members CAN access handovers with status APPROVED or SHARED."""
    mock_db = AsyncMock()
    incoming_user = User(id=uuid.uuid4())
    shared_handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="SHARED",
    )
    incoming_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=shared_handover.project_id,
        user_id=incoming_user.id,
        role=ProjectMemberRole.INCOMING.value,
    )

    mock_h_res = MagicMock()
    mock_h_res.scalars.return_value.first.return_value = shared_handover

    mock_m_res = MagicMock()
    mock_m_res.scalars.return_value.first.return_value = incoming_member

    mock_db.execute.side_effect = [mock_h_res, mock_m_res]

    accessible_handover = await require_handover_access(
        handover_id=shared_handover.id,
        current_user=incoming_user,
        db=mock_db,
    )
    assert accessible_handover.id == shared_handover.id
    assert accessible_handover.status == "SHARED"


# =============================================================================
# 9. REJECT & AUDIT TRAIL HISTORY RETRIEVAL
# =============================================================================

@pytest.mark.asyncio
async def test_reject_handover_happy_path():
    """Lead formally rejects an IN_REVIEW handover -> status becomes REJECTED."""
    mock_db = AsyncMock()
    lead_id = uuid.uuid4()
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="IN_REVIEW",
        version="v1.0",
    )
    lead_user = User(id=lead_id)

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.return_value = AsyncMock()
        res = await reject_handover(
            payload=RejectHandoverRequest(reason="Scope insufficient for production service transfer."),
            handover=handover,
            current_user=lead_user,
            db=mock_db,
        )

    assert res.data["status"] == "REJECTED"
    assert handover.status == "REJECTED"
    assert mock_db.commit.called
    added_audit = mock_db.add.call_args[0][0]
    assert isinstance(added_audit, HandoverAuditLog)
    assert added_audit.action == "rejected"
    assert "insufficient" in added_audit.details["reason"]


@pytest.mark.asyncio
async def test_get_handover_history_audit_trail():
    """Verifies chronological history retrieval with both audit logs and immutable version snapshots."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    user_id = uuid.uuid4()

    author = User(id=user_id, full_name="Alice Engineer", email="alice@test.com")
    handover = Handover(
        id=handover_id,
        project_id=uuid.uuid4(),
        title="History Test Handover",
        status="ACKNOWLEDGED",
        version="v1.1",
    )

    audit_entry = HandoverAuditLog(
        id=uuid.uuid4(),
        handover_id=handover_id,
        user_id=user_id,
        action="approved",
        details={"notes": "Signed off"},
        created_at=datetime.now(timezone.utc),
    )
    audit_entry.user = author

    version_entry = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.0",
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
        snapshot={"title": "History Test Handover", "version": "v1.0"},
    )
    version_entry.creator = author

    mock_audit_res = MagicMock()
    mock_audit_res.scalars.return_value.all.return_value = [audit_entry]

    mock_version_res = MagicMock()
    mock_version_res.scalars.return_value.all.return_value = [version_entry]

    mock_db.execute.side_effect = [mock_audit_res, mock_version_res]

    res = await get_handover_history(handover=handover, db=mock_db)

    assert res.data.handover_id == handover_id
    assert res.data.current_version == "v1.1"
    assert len(res.data.audit_logs) == 1
    assert res.data.audit_logs[0].action == "approved"
    assert res.data.audit_logs[0].user_name == "Alice Engineer"
    assert len(res.data.versions) == 1
    assert res.data.versions[0].version_number == "v1.0"
    assert res.data.versions[0].creator_name == "Alice Engineer"
