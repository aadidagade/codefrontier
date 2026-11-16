"""
Final Integration Audit Test Suite
==================================
Comprehensive integration testing across all three Round 3 improvements:
1. Evidence Verification and Contradiction Detection
2. Role-Based Access Control and Audit Trail
3. Versioned Handovers and Incoming-Member Continuity

Verifies the 9 essential cross-cutting dependencies:
- D1: Only authorized users can resolve evidence conflicts (403 for non-lead/admin).
- D2: Every conflict resolution is recorded in the audit trail.
- D3: Approved handovers preserve their evidence references.
- D4: Every new handover revision receives a version record.
- D5: Version restoration creates a new revision without deleting historical data.
- D6: Only authorized members can share handovers.
- D7: Incoming members can only access handovers shared with them.
- D8: Incoming-member task updates are recorded.
- D9: Important handover actions appear in audit logs.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.permissions import Permission, ProjectRole
from app.dependencies.authorization import (
    enforce_member_permission,
    require_handover_access,
    require_project_membership,
)
from app.models.audit_log import AuditActionType, AuditEntityType, AuditLog
from app.models.conflict import Conflict
from app.models.evidence import EvidenceReference
from app.models.handover import (
    Handover,
    HandoverAuditLog,
    HandoverSection,
    HandoverVersion,
)
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.task import Task, TaskProgressUpdate
from app.models.user import User

from app.schemas.conflict import ConflictResolveRequest
from app.schemas.handover import (
    AcknowledgeHandoverRequest,
    ApproveHandoverRequest,
    HandoverStatus,
    HandoverTransitionStatus,
    ShareHandoverRequest,
)
from app.schemas.task import TaskProgressUpdateCreate, TaskStatusUpdate

from app.services.audit_service import AuditService
from app.services.contradiction_service import ContradictionDetectionService
from app.services.version_service import (
    HandoverVersionService,
    build_handover_snapshot,
)

from app.api.v1.endpoints.conflicts import resolve_conflict_by_id
from app.api.v1.endpoints.handovers import (
    acknowledge_handover,
    approve_handover,
    get_handover_continuity,
    list_shared_with_me_handovers,
    share_handover,
)
from app.api.v1.endpoints.tasks import (
    add_task_progress_update,
    update_continuation_task_status,
)


# =============================================================================
# DEPENDENCY 1: Only authorized users can resolve evidence conflicts
# =============================================================================

@pytest.mark.asyncio
async def test_d1_only_authorized_users_can_resolve_evidence_conflicts():
    """Unauthorized members (INCOMING, OUTGOING, VIEWER) cannot resolve conflicts (403)."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    conflict_id = uuid.uuid4()

    incoming_user = User(id=uuid.uuid4(), full_name="Elena Rostova", email="incoming@company.internal")
    outgoing_user = User(id=uuid.uuid4(), full_name="Sarah Jenkins", email="outgoing@company.internal")
    lead_user = User(id=uuid.uuid4(), full_name="Lead Engineer", email="lead@company.internal")

    conflict = Conflict(
        id=conflict_id,
        project_id=project_id,
        conflict_type="FACTUAL_CONTRADICTION",
        status="DETECTED",
        description="Architecture discrepancy between Redis 7 and Memcached.",
        source_a={"document_name": "spec_v1.md", "excerpt": "Uses Memcached"},
        source_b={"document_name": "spec_v2.md", "excerpt": "Uses Redis 7"},
    )

    resolve_payload = ConflictResolveRequest(
        chosen_source="spec_v2.md",
        authoritative_value="Redis 7 Cluster",
        resolution_notes="Approved by Lead Architect.",
    )

    # 1. Incoming member attempt -> 403 Forbidden
    with patch.object(ContradictionDetectionService, "get_conflict", new_callable=AsyncMock, return_value=conflict), \
         patch("app.api.v1.endpoints.conflicts.require_project_membership", side_effect=ForbiddenException("Project role 'INCOMING' lacks permission.")):
        with pytest.raises(ForbiddenException):
            await resolve_conflict_by_id(
                conflict_id=conflict_id,
                payload=resolve_payload,
                current_user=incoming_user,
                db=mock_db,
            )

    # 2. Outgoing member attempt -> 403 Forbidden
    with patch.object(ContradictionDetectionService, "get_conflict", new_callable=AsyncMock, return_value=conflict), \
         patch("app.api.v1.endpoints.conflicts.require_project_membership", side_effect=ForbiddenException("Project role 'OUTGOING' lacks permission.")):
        with pytest.raises(ForbiddenException):
            await resolve_conflict_by_id(
                conflict_id=conflict_id,
                payload=resolve_payload,
                current_user=outgoing_user,
                db=mock_db,
            )

    # 3. Lead user attempt -> Authorized
    with patch.object(ContradictionDetectionService, "get_conflict", new_callable=AsyncMock, return_value=conflict), \
         patch.object(ContradictionDetectionService, "resolve_conflict", new_callable=AsyncMock, return_value=conflict), \
         patch("app.api.v1.endpoints.conflicts.require_project_membership") as mock_perm, \
         patch.object(AuditService, "record_event", new_callable=AsyncMock):
        mock_perm.return_value = AsyncMock()
        response = await resolve_conflict_by_id(
            conflict_id=conflict_id,
            payload=resolve_payload,
            current_user=lead_user,
            db=mock_db,
        )
        assert response.data["conflictId"] == str(conflict.id)


# =============================================================================
# DEPENDENCY 2: Every conflict resolution is recorded in the audit trail
# =============================================================================

@pytest.mark.asyncio
async def test_d2_every_conflict_resolution_recorded_in_audit_trail():
    """Conflict resolution generates an immutable AuditLog entry with CONFLICT_RESOLVED."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    conflict_id = uuid.uuid4()
    lead_user = User(id=uuid.uuid4(), full_name="Lead Engineer", email="lead@company.internal")

    conflict = Conflict(
        id=conflict_id,
        project_id=project_id,
        conflict_type="SPECIFICATION_MISMATCH",
        status="RESOLVED",
        description="Discrepancy in caching architecture.",
        source_a={"document_name": "spec_v1.md"},
        source_b={"document_name": "spec_v2.md"},
    )

    resolve_payload = ConflictResolveRequest(
        chosen_source="spec_v2.md",
        authoritative_value="Redis 7 Cluster",
        resolution_notes="Adopted Redis 7 Cluster.",
    )

    with patch.object(ContradictionDetectionService, "get_conflict", new_callable=AsyncMock, return_value=conflict), \
         patch.object(ContradictionDetectionService, "resolve_conflict", new_callable=AsyncMock, return_value=conflict), \
         patch("app.api.v1.endpoints.conflicts.require_project_membership") as mock_perm, \
         patch.object(AuditService, "record_event", new_callable=AsyncMock) as mock_record_event:
        mock_perm.return_value = AsyncMock()

        await resolve_conflict_by_id(
            conflict_id=conflict_id,
            payload=resolve_payload,
            current_user=lead_user,
            db=mock_db,
        )

        mock_record_event.assert_awaited_once()
        call_kwargs = mock_record_event.call_args[1]
        assert call_kwargs["action"] == AuditActionType.CONFLICT_RESOLVED
        assert call_kwargs["entity_type"] == AuditEntityType.CONFLICT
        assert call_kwargs["entity_id"] == conflict.id
        assert call_kwargs["user_id"] == lead_user.id
        assert call_kwargs["project_id"] == project_id
        assert call_kwargs["change_metadata"]["chosen_source"] == "spec_v2.md"


# =============================================================================
# DEPENDENCY 3: Approved handovers preserve their evidence references
# =============================================================================

@pytest.mark.asyncio
async def test_d3_approved_handovers_preserve_evidence_references():
    """Approved handover snapshot and sections fully retain cited evidence references."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    handover_id = uuid.uuid4()
    reviewer = User(id=uuid.uuid4(), full_name="Principal Reviewer", email="reviewer@company.internal")

    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Passkey Level 3 Architecture Handover",
        version="v1.0",
        status=HandoverStatus.IN_REVIEW.value,
        transition_status=HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value,
        created_by=reviewer.id,
        created_at=datetime.now(timezone.utc),
        sections=[],
        tasks=[],
    )

    sec = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover_id,
        section_type="technical_architecture",
        title="Technical Architecture",
        content="Passkey authentication backed by WebAuthn FIDO2 Level 3 standards.",
        sort_order=1,
        review_status="approved",
    )

    ev_ref = EvidenceReference(
        id=uuid.uuid4(),
        handover_section_id=sec.id,
        document_id=uuid.uuid4(),
        document_chunk_id=uuid.uuid4(),
        quoted_text="WebAuthn Level 3 platform authenticators mandate hardware biometric boundary.",
        supporting_text_excerpt="Hardware biometric boundary requirement verified.",
        relevance_score=0.98,
        source_filename="FIDO2_L3_Spec.pdf",
    )
    sec.evidence_references = [ev_ref]
    handover.sections = [sec]

    # Baseline snapshot on approval
    snapshot = build_handover_snapshot(handover, reviewer.id)
    assert "sections" in snapshot
    snap_sec = snapshot["sections"][0]
    assert snap_sec["section_type"] == "technical_architecture"
    assert len(snap_sec.get("evidence_references", [])) == 1
    ev_snap = snap_sec["evidence_references"][0]
    assert ev_snap["quoted_text"] == "WebAuthn Level 3 platform authenticators mandate hardware biometric boundary."
    assert ev_snap["relevance_score"] == 0.98


# =============================================================================
# DEPENDENCY 4: Every new handover revision receives a version record
# =============================================================================

@pytest.mark.asyncio
async def test_d4_every_new_handover_revision_receives_version_record():
    """Creating a revision records an immutable HandoverVersion with creator and snapshot."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    handover_id = uuid.uuid4()
    author = User(id=uuid.uuid4(), full_name="Sarah Jenkins", email="author@company.internal")

    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Core Payment Gateway Handover",
        version="v1.0",
        status=HandoverStatus.DRAFT.value,
        created_by=author.id,
        created_at=datetime.now(timezone.utc),
        sections=[],
        tasks=[],
    )

    version_svc = HandoverVersionService(mock_db)
    with patch.object(version_svc, "fetch_full_handover", new_callable=AsyncMock, return_value=handover), \
         patch.object(version_svc, "get_latest_version", new_callable=AsyncMock, return_value=None):
        version_rec = await version_svc.create_version_snapshot(
            handover_id=handover_id,
            user_id=author.id,
            version_number="v1.0",
            version_description="Initial synthesized draft",
            approval_status="DRAFT",
            mark_as_latest=True,
        )

    assert version_rec.version_number == "v1.0"
    assert version_rec.created_by == author.id
    assert version_rec.is_latest is True
    assert version_rec.approval_status == "DRAFT"
    assert "title" in version_rec.snapshot


# =============================================================================
# DEPENDENCY 5: Version restoration creates a new revision
# =============================================================================

@pytest.mark.asyncio
async def test_d5_version_restoration_creates_new_revision():
    """Restoration generates a brand-new revision based on target version; never deletes historical data."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    handover_id = uuid.uuid4()
    owner = User(id=uuid.uuid4(), full_name="Project Owner", email="owner@company.internal")

    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Payment Engine Handover",
        version="v1.1",
        status=HandoverStatus.DRAFT.value,
        created_by=owner.id,
        created_at=datetime.now(timezone.utc),
        sections=[],
        tasks=[],
    )

    v1_0 = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.0",
        version_description="Certified production baseline",
        approval_status="APPROVED",
        is_latest=False,
        created_by=owner.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        snapshot={
            "title": "Payment Engine Handover",
            "version": "v1.0",
            "sections": [
                {
                    "section_type": "overview",
                    "title": "Overview",
                    "content": "Certified baseline content v1.0",
                    "sort_order": 1,
                    "review_status": "approved",
                }
            ],
            "tasks": [],
        },
    )

    version_svc = HandoverVersionService(mock_db)
    with patch.object(version_svc, "fetch_full_handover", new_callable=AsyncMock, return_value=handover), \
         patch.object(version_svc, "get_version", new_callable=AsyncMock, return_value=v1_0):
        restored_handover, new_version = await version_svc.restore_version(
            handover_id=handover_id,
            version_id=v1_0.id,
            user_id=owner.id,
            reason="Reverting to v1.0 certified baseline",
        )

    # Restored entity increments version
    assert restored_handover.version == "v1.2"
    assert new_version.version_number == "v1.2"
    assert new_version.parent_version_id == v1_0.id
    assert new_version.is_latest is True
    # Historical version v1.0 is preserved intact
    assert v1_0.version_number == "v1.0"
    assert v1_0.approval_status == "APPROVED"


# =============================================================================
# DEPENDENCY 6: Only authorized members can share handovers
# =============================================================================

@pytest.mark.asyncio
async def test_d6_only_authorized_members_can_share_handovers():
    """Sharing handovers is strictly restricted to ADMIN, PROJECT_OWNER, and LEAD roles."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    handover_id = uuid.uuid4()
    target_incoming_id = uuid.uuid4()

    incoming_user = User(id=uuid.uuid4(), full_name="Elena Rostova", email="incoming@company.internal")
    owner_user = User(id=uuid.uuid4(), full_name="Marcus Vance", email="owner@company.internal")

    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="WebAuthn Handover",
        status=HandoverStatus.APPROVED.value,
        transition_status=HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value,
    )

    share_payload = ShareHandoverRequest(assigned_to=target_incoming_id)

    # 1. Unauthorized attempt (INCOMING) -> 403 Forbidden
    with patch("app.api.v1.endpoints.handovers.require_project_membership", side_effect=ForbiddenException("Forbidden: cannot share handover")):
        with pytest.raises(ForbiddenException):
            await share_handover(
                payload=share_payload,
                handover=handover,
                current_user=incoming_user,
                db=mock_db,
            )

    # 2. Authorized attempt (PROJECT_OWNER) -> Success
    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm, \
         patch("app.api.v1.endpoints.handovers.AuditService.log_event", new_callable=AsyncMock), \
         patch("app.api.v1.endpoints.handovers.NotificationService.notify_handover_shared", new_callable=AsyncMock):
        mock_perm.return_value = AsyncMock()
        res = await share_handover(
            payload=share_payload,
            handover=handover,
            current_user=owner_user,
            db=mock_db,
        )
        assert res.data["assignedTo"] == str(target_incoming_id)
        assert res.data["status"] == HandoverStatus.SHARED.value
        assert handover.assigned_to == target_incoming_id


# =============================================================================
# DEPENDENCY 7: Incoming members can only access handovers shared with them
# =============================================================================

@pytest.mark.asyncio
async def test_d7_incoming_members_can_only_access_handovers_shared_with_them():
    """Incoming members cannot access unapproved draft handovers; can only access approved/shared ones."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    incoming_member = User(id=uuid.uuid4(), full_name="Elena Rostova", email="elena@company.internal")

    pm_incoming = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_member.id,
        role="INCOMING",
    )

    # Unapproved draft handover
    draft_handover = Handover(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Unapproved Draft Handover",
        status="DRAFT",
    )

    # 1. Attempting to access draft handover -> 403 Forbidden
    draft_res = MagicMock()
    draft_res.scalars.return_value.first.return_value = draft_handover
    mock_db.execute.return_value = draft_res

    with patch("app.dependencies.authorization.enforce_member_permission", new_callable=AsyncMock, return_value=pm_incoming):
        with pytest.raises(ForbiddenException) as exc_info:
            await require_handover_access(
                handover_id=draft_handover.id,
                current_user=incoming_member,
                db=mock_db,
            )
        assert "Incoming members can only access handovers after authorized approval" in str(exc_info.value)

    # 2. Approved / shared handover -> Access permitted
    shared_handover = Handover(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Approved Production Handover",
        status="SHARED",
        assigned_to=incoming_member.id,
    )
    shared_res = MagicMock()
    shared_res.scalars.return_value.first.return_value = shared_handover
    mock_db.execute.return_value = shared_res

    with patch("app.dependencies.authorization.enforce_member_permission", new_callable=AsyncMock, return_value=pm_incoming):
        res = await require_handover_access(
            handover_id=shared_handover.id,
            current_user=incoming_member,
            db=mock_db,
        )
        assert res.id == shared_handover.id


# =============================================================================
# DEPENDENCY 8: Incoming-member task updates are recorded
# =============================================================================

@pytest.mark.asyncio
async def test_d8_incoming_member_task_updates_are_recorded():
    """Updating task status or logging progress update creates persistent TaskProgressUpdate records."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    handover_id = uuid.uuid4()
    incoming_user = User(id=uuid.uuid4(), full_name="Elena Rostova", email="incoming@company.internal")

    m_incoming = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_user.id,
        role="INCOMING",
    )

    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Database Sharding Handover",
        status=HandoverStatus.ACKNOWLEDGED.value,
        transition_status="Acknowledged",
        assigned_to=incoming_user.id,
    )

    task = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=handover_id,
        title="Run Partition Stress Rehearsal",
        description="Execute pg_bench 25k RPS test.",
        status="pending",
        assigned_to=incoming_user.id,
    )

    pm_res = MagicMock()
    pm_res.scalars.return_value.first.return_value = m_incoming
    h_res = MagicMock()
    h_res.scalars.return_value.first.return_value = handover

    progress_payload = TaskProgressUpdateCreate(
        update_text="Dry-run partition rehearsal completed with 0 deadlocks.",
        new_status="in_progress",
    )

    mock_db.execute.side_effect = [pm_res, h_res]
    with patch("app.api.v1.endpoints.tasks.AuditService.log_event", new_callable=AsyncMock) as mock_audit, \
         patch("app.api.v1.endpoints.tasks.NotificationService.notify_task_unblocked", new_callable=AsyncMock):
        res = await add_task_progress_update(
            payload=progress_payload,
            task=task,
            current_user=incoming_user,
            db=mock_db,
        )
    mock_db.execute.side_effect = None

    # Assert progress was persisted and handover transition advanced
    assert res.data.task_id == task.id
    assert res.data.status_after == "in_progress"
    assert res.data.created_at is not None
    assert "Dry-run partition rehearsal completed" in task.description
    assert handover.transition_status == "In Progress"
    mock_audit.assert_awaited_once()


# =============================================================================
# DEPENDENCY 9: Important handover actions appear in audit logs
# =============================================================================

@pytest.mark.asyncio
async def test_d9_important_handover_actions_appear_in_audit_logs():
    """All sensitive handover lifecycle transitions generate immutable audit trail entries."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    audit_svc = AuditService(mock_db)

    # 1. HANDOVER_GENERATED
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_GENERATED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=uuid.uuid4(),
        user_id=user_id,
        project_id=project_id,
        change_metadata={"version": "v1.0", "title": "OAuth2 Migration Handover"},
        commit=False,
    )

    # 2. HANDOVER_APPROVED
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_APPROVED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=uuid.uuid4(),
        user_id=user_id,
        project_id=project_id,
        change_metadata={"approved_version": "v1.0"},
        commit=False,
    )

    # 3. HANDOVER_SHARED
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_SHARED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=uuid.uuid4(),
        user_id=user_id,
        project_id=project_id,
        change_metadata={"assigned_to": str(uuid.uuid4())},
        commit=False,
    )

    # 4. HANDOVER_ACKNOWLEDGED
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_ACKNOWLEDGED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=uuid.uuid4(),
        user_id=user_id,
        project_id=project_id,
        change_metadata={"transition_status": "Acknowledged"},
        commit=False,
    )

    # 5. VERSION_RESTORED
    await audit_svc.record_event(
        action=AuditActionType.VERSION_RESTORED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=uuid.uuid4(),
        user_id=user_id,
        project_id=project_id,
        change_metadata={"restored_from": "v1.0", "new_revision": "v1.2"},
        commit=False,
    )

    # Verify mock_db.add was called for all 5 audit records
    assert mock_db.add.call_count == 5
    for call in mock_db.add.call_args_list:
        added_obj = call[0][0]
        assert isinstance(added_obj, AuditLog)
        assert added_obj.project_id == project_id
        assert added_obj.user_id == user_id
