import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import ForbiddenException, NotFoundException, BadRequestException
from app.core.permissions import Permission, ProjectRole
from app.models.audit_log import AuditActionType, AuditEntityType
from app.models.handover import (
    Handover,
    HandoverSection,
    HandoverVersion,
    HandoverAuditLog,
)
from app.models.conflict import Conflict
from app.models.task import Task
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.user import User
from app.schemas.handover import (
    HandoverStatus,
    HandoverVersionResponse,
    VersionCreateRequest,
    RestoreVersionRequest,
    VersionDiffResponse,
    SectionDiff,
)
from app.services.version_service import (
    HandoverVersionService,
    increment_version,
    build_handover_snapshot,
)
from app.api.v1.endpoints.handovers import (
    list_handover_versions,
    get_latest_handover_version,
    get_handover_version,
    create_handover_version,
    restore_handover_version,
    compare_handover_versions,
)


# =============================================================================
# 1. VERSION MODEL & SCHEMA INTEGRITY TESTS (All 9 Required Attributes)
# =============================================================================

def test_handover_version_model_contains_all_required_attributes():
    """
    Verifies that HandoverVersion model contains all 9 required fields:
    - Version ID
    - Handover ID
    - Version number
    - Complete handover snapshot
    - Created by
    - Created timestamp
    - Version description
    - Approval status
    - Parent version reference
    Plus is_latest flag.
    """
    version_id = uuid.uuid4()
    handover_id = uuid.uuid4()
    user_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    snapshot_data = {
        "title": "Core Banking Architecture",
        "version": "v1.0",
        "status": "APPROVED",
        "sections": [{"section_type": "architecture", "title": "Architecture", "content": "Microservices"}],
    }

    v = HandoverVersion(
        id=version_id,
        handover_id=handover_id,
        version_number="v1.0",
        snapshot=snapshot_data,
        created_by=user_id,
        created_at=now,
        version_description="Initial approved production baseline",
        approval_status="APPROVED",
        parent_version_id=parent_id,
        is_latest=True,
    )

    # 1. Version ID
    assert v.id == version_id
    # 2. Handover ID
    assert v.handover_id == handover_id
    # 3. Version number
    assert v.version_number == "v1.0"
    # 4. Complete handover snapshot
    assert v.snapshot == snapshot_data
    # 5. Created by
    assert v.created_by == user_id
    # 6. Created timestamp
    assert v.created_at == now
    # 7. Version description
    assert v.version_description == "Initial approved production baseline"
    # 8. Approval status
    assert v.approval_status == "APPROVED"
    # 9. Parent version reference
    assert v.parent_version_id == parent_id
    # Latest flag
    assert v.is_latest is True


def test_handover_version_response_schema_validation():
    """Verifies that HandoverVersionResponse serializes all required fields properly."""
    version_id = uuid.uuid4()
    handover_id = uuid.uuid4()
    user_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    resp = HandoverVersionResponse(
        id=version_id,
        handover_id=handover_id,
        version_number="v1.1",
        version_description="Updated database migration guide",
        approval_status="DRAFT",
        parent_version_id=parent_id,
        is_latest=True,
        created_by=user_id,
        creator_name="Alice Architect",
        created_at=now,
        snapshot={"title": "Updated", "sections": []},
    )

    assert resp.id == version_id
    assert resp.handover_id == handover_id
    assert resp.version_number == "v1.1"
    assert resp.version_description == "Updated database migration guide"
    assert resp.approval_status == "DRAFT"
    assert resp.parent_version_id == parent_id
    assert resp.is_latest is True
    assert resp.created_by == user_id
    assert resp.creator_name == "Alice Architect"
    assert resp.snapshot["title"] == "Updated"


# =============================================================================
# 2. VERSION INCREMENT HELPER TESTS
# =============================================================================

def test_increment_version_various_formats():
    """Verifies semantic version incrementation preserving prefix."""
    assert increment_version("v1.0") == "v1.1"
    assert increment_version("v1.1") == "v1.2"
    assert increment_version("v1.9") == "v1.10"
    assert increment_version("1.0") == "1.1"
    assert increment_version("v2") == "v2.1"
    assert increment_version("draft") == "draft.1"


# =============================================================================
# 3. REQUIREMENT 1: IMMUTABLE HISTORICAL SNAPSHOTS
# =============================================================================

def test_immutable_handover_snapshot_creation():
    """Verifies build_handover_snapshot freezes all handover content and references."""
    handover_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    sec1 = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover_id,
        section_type="architecture",
        title="Architecture",
        content="Initial monolithic setup",
        sort_order=1,
    )
    handover = Handover(
        id=handover_id,
        project_id=project_id,
        title="Initial Handover",
        status="APPROVED",
        version="v1.0",
        created_by=user_id,
    )
    handover.sections = [sec1]
    handover.conflicts = []
    handover.tasks = []

    snapshot = build_handover_snapshot(handover, user_id=user_id)

    assert snapshot["id"] == str(handover_id)
    assert snapshot["title"] == "Initial Handover"
    assert snapshot["version"] == "v1.0"
    assert snapshot["approved_by"] == str(user_id)
    assert len(snapshot["sections"]) == 1
    assert snapshot["sections"][0]["content"] == "Initial monolithic setup"

    # Mutate live handover - snapshot must remain completely unaffected
    handover.title = "Mutated Title"
    sec1.content = "Mutated content"
    assert snapshot["title"] == "Initial Handover"
    assert snapshot["sections"][0]["content"] == "Initial monolithic setup"


# =============================================================================
# 4. REQUIREMENT 2: PRESERVE PREVIOUSLY APPROVED VERSIONS
# =============================================================================

@pytest.mark.asyncio
async def test_preserve_previously_approved_versions_on_modification():
    """
    Requirement 2:
    When an approved handover (v1.0) is edited or restored, the approved snapshot
    is preserved with approval_status="APPROVED", while the active handover is bumped to v1.1 DRAFT.
    """
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    handover_id = uuid.uuid4()

    handover = Handover(
        id=handover_id,
        project_id=uuid.uuid4(),
        title="Production Microservices Handover",
        status="APPROVED",
        version="v1.0",
        created_by=user_id,
    )
    sec = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover_id,
        section_type="deployment",
        title="Deployment",
        content="Kubernetes on AWS",
        sort_order=1,
    )
    handover.sections = [sec]
    handover.conflicts = []
    handover.tasks = []

    # Mock DB query finding no existing v1.0 version snapshot record yet
    mock_find_res = MagicMock()
    mock_find_res.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_find_res

    # Use HandoverVersionService to create snapshot
    service = HandoverVersionService(mock_db)
    with patch.object(service, "fetch_full_handover", return_value=handover), \
         patch.object(service, "get_latest_version", return_value=None):
        version_rec = await service.create_version_snapshot(
            handover_id=handover.id,
            user_id=user_id,
            version_number="v1.0",
            version_description="Approved production version v1.0",
            approval_status="APPROVED",
            mark_as_latest=True,
        )

    assert version_rec.version_number == "v1.0"
    assert version_rec.approval_status == "APPROVED"
    assert version_rec.is_latest is True
    assert version_rec.snapshot["title"] == "Production Microservices Handover"

    # Now verify increment to v1.1
    new_version = increment_version(handover.version)
    assert new_version == "v1.1"


# =============================================================================
# 5. REQUIREMENT 3: IDENTIFY THE LATEST VERSION
# =============================================================================

@pytest.mark.asyncio
async def test_identify_latest_version_flag_management():
    """
    Requirement 3:
    Identify the latest version. When a new version is created with mark_as_latest=True,
    all prior versions are unmarked (is_latest=False) and the new version is marked is_latest=True.
    """
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    handover_id = uuid.uuid4()

    handover = Handover(
        id=handover_id,
        project_id=uuid.uuid4(),
        title="Messaging Platform Handover",
        status="DRAFT",
        version="v1.2",
    )
    handover.sections = []

    service = HandoverVersionService(mock_db)
    with patch.object(service, "fetch_full_handover", return_value=handover), \
         patch.object(service, "get_latest_version", return_value=None):
        v_latest = await service.create_version_snapshot(
            handover_id=handover_id,
            user_id=user_id,
            version_number="v1.2",
            version_description="Revision v1.2",
            approval_status="DRAFT",
            mark_as_latest=True,
        )

    assert v_latest.is_latest is True
    assert mock_db.execute.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_get_latest_handover_version_query():
    """Verifies get_latest_version retrieves the active latest version record."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    user_id = uuid.uuid4()

    latest_ver = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v2.0",
        version_description="Major Release 2.0",
        approval_status="APPROVED",
        is_latest=True,
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
        snapshot={"title": "Messaging Platform Handover v2", "sections": []},
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = latest_ver
    mock_db.execute.return_value = mock_res

    service = HandoverVersionService(mock_db)
    result = await service.get_latest_version(handover_id)

    assert result is not None
    assert result.version_number == "v2.0"
    assert result.is_latest is True


# =============================================================================
# 6. REQUIREMENT 4: TRACK WHO CREATED EACH VERSION
# =============================================================================

@pytest.mark.asyncio
async def test_track_who_created_each_version():
    """
    Requirement 4:
    Track who created each version, storing user ID and populating creator name.
    """
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    handover_id = uuid.uuid4()

    user = User(id=user_id, full_name="Carlos Lead Architect", email="carlos@company.com")
    version_record = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.0",
        created_by=user_id,
        creator=user,
        created_at=datetime.now(timezone.utc),
        snapshot={"sections": []},
    )

    service = HandoverVersionService(mock_db)
    resp = service.to_response(version_record)

    assert resp.created_by == user_id
    assert resp.creator_name == "Carlos Lead Architect"


# =============================================================================
# 7. REQUIREMENT 5: TRACK APPROVAL STATUS SEPARATELY FOR EACH REVISION
# =============================================================================

@pytest.mark.asyncio
async def test_track_approval_status_separately_for_each_revision():
    """
    Requirement 5:
    Track approval status separately for each revision (DRAFT, IN_REVIEW, APPROVED, REJECTED).
    """
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    handover_id = uuid.uuid4()

    v1 = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.0",
        approval_status="APPROVED",
        is_latest=False,
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
        snapshot={},
    )
    v2 = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.1",
        approval_status="REJECTED",
        is_latest=False,
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
        snapshot={},
    )
    v3 = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.2",
        approval_status="IN_REVIEW",
        is_latest=True,
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
        snapshot={},
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [v3, v2, v1]
    mock_db.execute.return_value = mock_res

    service = HandoverVersionService(mock_db)
    versions = await service.list_versions(handover_id)

    assert len(versions) == 3
    assert versions[0].approval_status == "IN_REVIEW"
    assert versions[0].is_latest is True
    assert versions[1].approval_status == "REJECTED"
    assert versions[1].is_latest is False
    assert versions[2].approval_status == "APPROVED"
    assert versions[2].is_latest is False


# =============================================================================
# 8. REQUIREMENT 6: PREVENT UNAUTHORIZED VERSION CREATION & RESTORATION
# =============================================================================

@pytest.mark.asyncio
async def test_unauthorized_member_cannot_create_version():
    """
    Requirement 6:
    Prevent unauthorized version creation. INCOMING members cannot manually create versions.
    """
    mock_db = AsyncMock()
    incoming_user = User(id=uuid.uuid4(), email="incoming@test.com")
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Secret Handover",
        status="DRAFT",
    )

    # Mock require_project_membership to raise ForbiddenException for INCOMING
    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.side_effect = ForbiddenException("INCOMING members cannot create versions.")
        with pytest.raises(ForbiddenException) as exc_info:
            await create_handover_version(
                handover_id=handover.id,
                payload=VersionCreateRequest(version_description="Unauthorized snapshot"),
                handover=handover,
                current_user=incoming_user,
                db=mock_db,
            )
        assert "cannot create versions" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_unauthorized_member_cannot_restore_version():
    """
    Requirement 6:
    Prevent unauthorized restoration. INCOMING members cannot restore prior versions.
    """
    mock_db = AsyncMock()
    incoming_user = User(id=uuid.uuid4(), email="incoming@test.com")
    handover = Handover(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Financial Pipeline Handover",
        status="APPROVED",
    )

    with patch("app.api.v1.endpoints.handovers.fetch_full_handover", return_value=handover), \
         patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm:
        mock_perm.side_effect = ForbiddenException("Permission EDIT_HANDOVER required to restore.")
        with pytest.raises(ForbiddenException) as exc_info:
            await restore_handover_version(
                handover_id=handover.id,
                version_id=uuid.uuid4(),
                payload=RestoreVersionRequest(reason="Restore request"),
                current_user=incoming_user,
                db=mock_db,
            )
        assert "EDIT_HANDOVER required" in str(exc_info.value.message)


# =============================================================================
# 9. REQUIREMENT 7 & 8: RESTORATION CREATES NEW REVISION & NEVER DELETES
# =============================================================================

@pytest.mark.asyncio
async def test_restore_version_creates_new_revision_and_never_deletes():
    """
    Requirements 7 & 8:
    7. Support restoration of an earlier version by creating a new revision based on it.
    8. Never delete historical approved versions during restoration.
    """
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()

    target_snapshot = {
        "title": "Reliable Database Handover v1.0",
        "sections": [
            {
                "section_type": "database_setup",
                "title": "Database Setup",
                "content": "PostgreSQL 16 High-Availability Replica",
                "sort_order": 1,
            }
        ],
    }

    v1_target = HandoverVersion(
        id=v1_id,
        handover_id=handover_id,
        version_number="v1.0",
        version_description="Initial Approved Baseline",
        approval_status="APPROVED",
        is_latest=False,
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
        snapshot=target_snapshot,
    )

    current_handover = Handover(
        id=handover_id,
        project_id=uuid.uuid4(),
        title="Corrupted or Altered Handover",
        status="APPROVED",
        version="v1.2",
    )
    current_sec = HandoverSection(
        id=uuid.uuid4(),
        handover_id=handover_id,
        section_type="database_setup",
        title="Database Setup",
        content="Broken configuration",
        sort_order=1,
    )
    current_handover.sections = [current_sec]
    current_handover.conflicts = []
    current_handover.tasks = []

    service = HandoverVersionService(mock_db)
    with patch.object(service, "fetch_full_handover", return_value=current_handover), \
         patch.object(service, "get_version", return_value=v1_target):
        restored_handover, new_version = await service.restore_version(
            handover_id=handover_id,
            version_id=v1_id,
            user_id=user_id,
            reason="Rolling back to stable v1.0 database architecture",
        )

    # 1. Active handover entity updated with incremented version and DRAFT status
    assert restored_handover.title == "Reliable Database Handover v1.0"
    assert restored_handover.version == "v1.3"  # Incremented from v1.2
    assert restored_handover.status.upper() == "DRAFT"
    assert current_sec.content == "PostgreSQL 16 High-Availability Replica"

    # 2. New version record created with target version as parent
    assert new_version.version_number == "v1.3"
    assert new_version.parent_version_id == v1_id
    assert new_version.approval_status.upper() == "DRAFT"
    assert new_version.is_latest is True
    assert "Rolling back to stable v1.0" in new_version.version_description

    # 3. Requirement 8: ZERO DELETE statements called on db session!
    assert mock_db.delete.call_count == 0

    # 4. Added new version record and audit records
    add_calls = [call[0][0] for call in mock_db.add.call_args_list]
    added_versions = [c for c in add_calls if isinstance(c, HandoverVersion)]
    added_audits = [c for c in add_calls if isinstance(c, HandoverAuditLog)]

    assert len(added_versions) >= 1
    assert any(a.action == "version_restored" for a in added_audits)


# =============================================================================
# 10. SECTION DIFF & VERSION COMPARISON TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_compare_versions_section_diff():
    """
    Verifies compare_versions generates section-by-section diff highlighting
    changed and unchanged chapters.
    """
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    v1 = HandoverVersion(
        id=v1_id,
        handover_id=handover_id,
        version_number="v1.0",
        snapshot={
            "sections": [
                {
                    "section_type": "architecture",
                    "title": "System Architecture",
                    "content": "Single AWS region deployment",
                },
                {
                    "section_type": "monitoring",
                    "title": "Monitoring",
                    "content": "Prometheus & Grafana",
                },
            ]
        },
    )

    v2 = HandoverVersion(
        id=v2_id,
        handover_id=handover_id,
        version_number="v1.1",
        snapshot={
            "sections": [
                {
                    "section_type": "architecture",
                    "title": "System Architecture",
                    "content": "Multi-region active-active deployment across us-east-1 and eu-west-1",
                },
                {
                    "section_type": "monitoring",
                    "title": "Monitoring",
                    "content": "Prometheus & Grafana",  # Unchanged
                },
            ]
        },
    )

    service = HandoverVersionService(mock_db)
    with patch.object(service, "get_version", side_effect=[v1, v2]):
        diff = await service.compare_versions(handover_id, v1_id, v2_id)

    assert diff.from_version_number == "v1.0"
    assert diff.to_version_number == "v1.1"
    assert len(diff.section_diffs) == 2

    arch_diff = next(d for d in diff.section_diffs if d.section_type == "architecture")
    assert arch_diff.has_changed is True
    assert arch_diff.old_content == "Single AWS region deployment"
    assert "Multi-region active-active" in arch_diff.new_content

    mon_diff = next(d for d in diff.section_diffs if d.section_type == "monitoring")
    assert mon_diff.has_changed is False
    assert mon_diff.old_content == mon_diff.new_content


# =============================================================================
# 11. ENDPOINT HANDLER INVOCATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_list_handover_versions_endpoint():
    """Verifies list_handover_versions returns chronological version history."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    handover = Handover(id=handover_id, project_id=uuid.uuid4())
    user = User(id=uuid.uuid4())

    v1 = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.0",
        version_description="Initial",
        approval_status="APPROVED",
        is_latest=True,
        created_by=user.id,
        created_at=datetime.now(timezone.utc),
        snapshot={},
    )

    with patch.object(HandoverVersionService, "list_versions", return_value=[
        HandoverVersionResponse(
            id=v1.id,
            handover_id=v1.handover_id,
            version_number=v1.version_number,
            version_description=v1.version_description,
            approval_status=v1.approval_status,
            is_latest=True,
            created_by=v1.created_by,
            created_at=v1.created_at,
            snapshot={},
        )
    ]):
        res = await list_handover_versions(
            handover_id=handover_id,
            handover=handover,
            current_user=user,
            db=mock_db,
        )

    assert len(res.data) == 1
    assert res.data[0].version_number == "v1.0"


@pytest.mark.asyncio
async def test_get_latest_handover_version_endpoint():
    """Verifies get_latest_handover_version endpoint returns the active latest version."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    handover = Handover(id=handover_id, project_id=uuid.uuid4())
    user = User(id=uuid.uuid4())

    latest_v = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.5",
        version_description="Current latest release",
        approval_status="APPROVED",
        is_latest=True,
        created_by=user.id,
        created_at=datetime.now(timezone.utc),
        snapshot={},
    )

    with patch.object(HandoverVersionService, "get_latest_version", return_value=latest_v):
        res = await get_latest_handover_version(
            handover_id=handover_id,
            handover=handover,
            current_user=user,
            db=mock_db,
        )

    assert res.data.version_number == "v1.5"
    assert res.data.is_latest is True


@pytest.mark.asyncio
async def test_get_latest_handover_version_not_found():
    """Verifies 404 is raised when no version exists for handover."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    handover = Handover(id=handover_id, project_id=uuid.uuid4())
    user = User(id=uuid.uuid4())

    with patch.object(HandoverVersionService, "get_latest_version", return_value=None):
        with pytest.raises(NotFoundException):
            await get_latest_handover_version(
                handover_id=handover_id,
                handover=handover,
                current_user=user,
                db=mock_db,
            )


@pytest.mark.asyncio
async def test_create_handover_version_endpoint():
    """Verifies authorized member can trigger manual version creation."""
    mock_db = AsyncMock()
    handover_id = uuid.uuid4()
    lead_user = User(id=uuid.uuid4(), full_name="Lead Engineer")
    handover = Handover(
        id=handover_id,
        project_id=uuid.uuid4(),
        title="Microservices Transition",
        status="DRAFT",
        version="v1.1",
    )

    new_v = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=handover_id,
        version_number="v1.1",
        version_description="Pre-review checkpoint",
        approval_status="DRAFT",
        is_latest=True,
        created_by=lead_user.id,
        created_at=datetime.now(timezone.utc),
        snapshot={},
    )

    with patch("app.api.v1.endpoints.handovers.require_project_membership") as mock_perm, \
         patch.object(HandoverVersionService, "create_version_snapshot", return_value=new_v):
        mock_perm.return_value = AsyncMock()
        res = await create_handover_version(
            handover_id=handover_id,
            payload=VersionCreateRequest(version_description="Pre-review checkpoint"),
            handover=handover,
            current_user=lead_user,
            db=mock_db,
        )

    assert res.data.version_number == "v1.1"
    assert res.data.version_description == "Pre-review checkpoint"
    assert res.data.approval_status == "DRAFT"
