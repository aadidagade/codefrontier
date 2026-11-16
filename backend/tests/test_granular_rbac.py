import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import ForbiddenException, BadRequestException
from app.core.permissions import (
    Permission,
    ProjectRole,
    ROLE_PERMISSIONS,
    get_member_permissions,
    has_permission,
    normalize_role,
)
from app.dependencies.authorization import (
    enforce_member_permission,
    require_permission,
    require_project_membership,
)
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.models.handover import Handover, HandoverSection
from app.schemas.project import MemberAdd, MemberUpdateRole


# =============================================================================
# 1. PERMISSION ENUM & MANDATED ROLES TESTS
# =============================================================================

def test_permission_enum_contains_all_12_mandated_permissions():
    """Confirms all 12 permissions required by specification exist with exact keys."""
    expected_permissions = {
        "view_project",
        "edit_project",
        "upload_documents",
        "delete_documents",
        "generate_handover",
        "view_handover",
        "edit_handover",
        "submit_handover_for_review",
        "approve_handover",
        "share_handover",
        "manage_project_members",
        "view_audit_logs",
    }
    actual_permissions = {p.value for p in Permission if p != Permission.EDIT_APPROVED_HANDOVER}
    assert expected_permissions.issubset(actual_permissions)


def test_all_5_mandated_roles_supported_and_normalized():
    """
    Validates that the 5 specified roles are supported and normalize properly
    from user-friendly display labels, enum members, and string values:
    1. Admin
    2. Project Owner
    3. Outgoing Member
    4. Incoming Member
    5. Reviewer
    """
    # 1. Admin
    assert normalize_role("Admin") == ProjectRole.ADMIN
    assert normalize_role("ADMIN") == ProjectRole.ADMIN
    assert normalize_role(ProjectMemberRole.ADMIN) == ProjectRole.ADMIN

    # 2. Project Owner
    assert normalize_role("Project Owner") == ProjectRole.PROJECT_OWNER
    assert normalize_role("PROJECT_OWNER") == ProjectRole.PROJECT_OWNER
    assert normalize_role("owner") == ProjectRole.PROJECT_OWNER
    assert normalize_role(ProjectMemberRole.PROJECT_OWNER) == ProjectRole.PROJECT_OWNER

    # 3. Outgoing Member
    assert normalize_role("Outgoing Member") == ProjectRole.OUTGOING
    assert normalize_role("OUTGOING") == ProjectRole.OUTGOING
    assert normalize_role("outgoing") == ProjectRole.OUTGOING
    assert normalize_role(ProjectMemberRole.OUTGOING) == ProjectRole.OUTGOING

    # 4. Incoming Member
    assert normalize_role("Incoming Member") == ProjectRole.INCOMING
    assert normalize_role("INCOMING") == ProjectRole.INCOMING
    assert normalize_role("incoming") == ProjectRole.INCOMING
    assert normalize_role(ProjectMemberRole.INCOMING) == ProjectRole.INCOMING

    # 5. Reviewer
    assert normalize_role("Reviewer") == ProjectRole.REVIEWER
    assert normalize_role("REVIEWER") == ProjectRole.REVIEWER
    assert normalize_role("reviewer") == ProjectRole.REVIEWER
    assert normalize_role(ProjectMemberRole.REVIEWER) == ProjectRole.REVIEWER


# =============================================================================
# 2. ROLE PERMISSION MATRIX SPECIFICATION TESTS
# =============================================================================

def test_admin_has_full_permissions():
    """Admin role must possess all 12 project permissions."""
    admin_perms = get_member_permissions(ProjectRole.ADMIN)
    for p in [
        Permission.VIEW_PROJECT,
        Permission.EDIT_PROJECT,
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.GENERATE_HANDOVER,
        Permission.VIEW_HANDOVER,
        Permission.EDIT_HANDOVER,
        Permission.SUBMIT_HANDOVER_FOR_REVIEW,
        Permission.APPROVE_HANDOVER,
        Permission.SHARE_HANDOVER,
        Permission.MANAGE_PROJECT_MEMBERS,
        Permission.VIEW_AUDIT_LOGS,
    ]:
        assert p in admin_perms


def test_project_owner_permissions_and_member_management():
    """
    Requirement 5: Project Owners must have permission to manage project membership,
    edit projects, manage handovers, and view audit logs.
    """
    owner_perms = get_member_permissions(ProjectRole.PROJECT_OWNER)
    assert Permission.MANAGE_PROJECT_MEMBERS in owner_perms
    assert Permission.EDIT_PROJECT in owner_perms
    assert Permission.UPLOAD_DOCUMENTS in owner_perms
    assert Permission.DELETE_DOCUMENTS in owner_perms
    assert Permission.GENERATE_HANDOVER in owner_perms
    assert Permission.VIEW_HANDOVER in owner_perms
    assert Permission.EDIT_HANDOVER in owner_perms
    assert Permission.SUBMIT_HANDOVER_FOR_REVIEW in owner_perms
    assert Permission.APPROVE_HANDOVER in owner_perms
    assert Permission.SHARE_HANDOVER in owner_perms
    assert Permission.VIEW_AUDIT_LOGS in owner_perms


def test_outgoing_member_permissions():
    """
    Outgoing Member authors documentation and submits handovers, but cannot approve
    handovers, edit workspace settings, or manage members.
    """
    outgoing_perms = get_member_permissions(ProjectRole.OUTGOING)
    # Allowed
    assert Permission.VIEW_PROJECT in outgoing_perms
    assert Permission.UPLOAD_DOCUMENTS in outgoing_perms
    assert Permission.DELETE_DOCUMENTS in outgoing_perms
    assert Permission.GENERATE_HANDOVER in outgoing_perms
    assert Permission.VIEW_HANDOVER in outgoing_perms
    assert Permission.EDIT_HANDOVER in outgoing_perms
    assert Permission.SUBMIT_HANDOVER_FOR_REVIEW in outgoing_perms
    assert Permission.SHARE_HANDOVER in outgoing_perms
    assert Permission.VIEW_AUDIT_LOGS in outgoing_perms

    # Forbidden
    assert Permission.APPROVE_HANDOVER not in outgoing_perms
    assert Permission.MANAGE_PROJECT_MEMBERS not in outgoing_perms
    assert Permission.EDIT_PROJECT not in outgoing_perms


def test_incoming_member_permissions():
    """
    Incoming Member views project and approved handovers, but cannot edit, upload,
    generate, approve, or manage members by default.
    """
    incoming_perms = get_member_permissions(ProjectRole.INCOMING)
    # Allowed
    assert Permission.VIEW_PROJECT in incoming_perms
    assert Permission.VIEW_HANDOVER in incoming_perms

    # Forbidden
    assert Permission.EDIT_PROJECT not in incoming_perms
    assert Permission.UPLOAD_DOCUMENTS not in incoming_perms
    assert Permission.DELETE_DOCUMENTS not in incoming_perms
    assert Permission.GENERATE_HANDOVER not in incoming_perms
    assert Permission.EDIT_HANDOVER not in incoming_perms
    assert Permission.SUBMIT_HANDOVER_FOR_REVIEW not in incoming_perms
    assert Permission.APPROVE_HANDOVER not in incoming_perms
    assert Permission.SHARE_HANDOVER not in incoming_perms
    assert Permission.MANAGE_PROJECT_MEMBERS not in incoming_perms
    assert Permission.VIEW_AUDIT_LOGS not in incoming_perms


def test_reviewer_permissions():
    """
    Reviewer can view projects/handovers, request changes, approve handovers, and view audit logs,
    but cannot manage members, edit projects, or upload documents.
    """
    reviewer_perms = get_member_permissions(ProjectRole.REVIEWER)
    # Allowed
    assert Permission.VIEW_PROJECT in reviewer_perms
    assert Permission.VIEW_HANDOVER in reviewer_perms
    assert Permission.APPROVE_HANDOVER in reviewer_perms
    assert Permission.SHARE_HANDOVER in reviewer_perms
    assert Permission.VIEW_AUDIT_LOGS in reviewer_perms

    # Forbidden
    assert Permission.MANAGE_PROJECT_MEMBERS not in reviewer_perms
    assert Permission.EDIT_PROJECT not in reviewer_perms
    assert Permission.UPLOAD_DOCUMENTS not in reviewer_perms
    assert Permission.DELETE_DOCUMENTS not in reviewer_perms
    assert Permission.GENERATE_HANDOVER not in reviewer_perms
    assert Permission.EDIT_HANDOVER not in reviewer_perms


# =============================================================================
# 3. REQUIREMENT 4: INCOMING MEMBER APPROVED HANDOVER RESTRICTION
# =============================================================================

def test_incoming_member_cannot_edit_approved_handover_unless_explicitly_permitted():
    """
    Requirement 4: Prevent incoming members from editing approved handovers
    unless explicitly permitted.
    """
    # 1. Default incoming member has no edit permission
    assert has_permission(ProjectRole.INCOMING, Permission.EDIT_HANDOVER, handover_status="APPROVED") is False

    # 2. Incoming member with generic edit_handover custom permission STILL cannot edit APPROVED handover
    custom_edit_only = ["edit_handover"]
    assert has_permission(
        ProjectRole.INCOMING,
        Permission.EDIT_HANDOVER,
        custom_permissions=custom_edit_only,
        handover_status="APPROVED",
    ) is False
    assert has_permission(
        ProjectRole.INCOMING,
        Permission.EDIT_HANDOVER,
        custom_permissions=custom_edit_only,
        handover_status="SHARED",
    ) is False
    assert has_permission(
        ProjectRole.INCOMING,
        Permission.EDIT_HANDOVER,
        custom_permissions=custom_edit_only,
        handover_status="ACKNOWLEDGED",
    ) is False

    # 3. Incoming member with generic edit_handover CAN edit a DRAFT handover if custom granted
    assert has_permission(
        ProjectRole.INCOMING,
        Permission.EDIT_HANDOVER,
        custom_permissions=custom_edit_only,
        handover_status="DRAFT",
    ) is True

    # 4. Incoming member WITH explicit "edit_approved_handover" permission IS permitted to edit approved handover
    explicit_approved_override = ["edit_handover", "edit_approved_handover"]
    assert has_permission(
        ProjectRole.INCOMING,
        Permission.EDIT_HANDOVER,
        custom_permissions=explicit_approved_override,
        handover_status="APPROVED",
    ) is True
    assert has_permission(
        ProjectRole.INCOMING,
        Permission.EDIT_HANDOVER,
        custom_permissions=explicit_approved_override,
        handover_status="SHARED",
    ) is True


def test_non_incoming_members_can_edit_approved_handovers_for_versioning():
    """
    Admin, Project Owner, and Outgoing members can edit approved handovers
    (which triggers version increment v1.0 -> v1.1 and draft status reset).
    """
    assert has_permission(ProjectRole.ADMIN, Permission.EDIT_HANDOVER, handover_status="APPROVED") is True
    assert has_permission(ProjectRole.PROJECT_OWNER, Permission.EDIT_HANDOVER, handover_status="APPROVED") is True
    assert has_permission(ProjectRole.OUTGOING, Permission.EDIT_HANDOVER, handover_status="APPROVED") is True


# =============================================================================
# 4. REQUIREMENT 3: MULTI-TENANT ISOLATION & NON-MEMBER ACCESS RESTRICTION
# =============================================================================

@pytest.mark.asyncio
async def test_prevent_non_members_from_accessing_projects_they_do_not_belong_to():
    """
    Requirement 3: Prevent users from accessing projects they do not belong to.
    Verifies that get_project_member returning None raises ForbiddenException(403).
    """
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None  # Not a member
    mock_db.execute.return_value = mock_res

    target_project_id = uuid.uuid4()
    stranger_user_id = uuid.uuid4()

    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(
            project_id=target_project_id,
            user_id=stranger_user_id,
            permission=Permission.VIEW_PROJECT,
            db=mock_db,
        )

    assert "not an authorized member" in exc_info.value.message


# =============================================================================
# 5. ASYNC DEPENDENCY ENFORCEMENT & API WORKFLOW TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_enforce_member_permission_allows_authorized_member():
    """Verifies enforce_member_permission succeeds and returns ProjectMember for valid permissions."""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.PROJECT_OWNER.value,
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = member
    mock_db.execute.return_value = mock_res

    res = await enforce_member_permission(
        project_id=project_id,
        user_id=user_id,
        permission=Permission.MANAGE_PROJECT_MEMBERS,
        db=mock_db,
    )
    assert res.role == ProjectMemberRole.PROJECT_OWNER.value
    assert res.project_id == project_id


@pytest.mark.asyncio
async def test_enforce_member_permission_denies_unauthorized_action():
    """Verifies that an Incoming member attempting to generate handover is rejected with 403."""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.INCOMING.value,
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = member
    mock_db.execute.return_value = mock_res

    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(
            project_id=project_id,
            user_id=user_id,
            permission=Permission.GENERATE_HANDOVER,
            db=mock_db,
        )

    assert "Missing required permission 'generate_handover'" in exc_info.value.message


@pytest.mark.asyncio
async def test_enforce_member_permission_blocks_incoming_on_approved_handover():
    """Verifies incoming member editing approved handover receives specific denial message."""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.INCOMING.value,
        custom_permissions=["edit_handover"],  # Generic edit only, not approved override
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = member
    mock_db.execute.return_value = mock_res

    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(
            project_id=project_id,
            user_id=user_id,
            permission=Permission.EDIT_HANDOVER,
            db=mock_db,
            handover_status="APPROVED",
        )

    assert "Incoming members cannot edit approved handovers unless explicitly permitted" in exc_info.value.message


# =============================================================================
# 6. MEMBER SCHEMA NORMALIZATION TESTS
# =============================================================================

def test_member_add_and_update_schemas_support_all_5_roles():
    """Verifies MemberAdd and MemberUpdateRole schemas accept user-friendly and enum role names."""
    # Test all 5 roles
    roles = [
        ("Admin", ProjectMemberRole.ADMIN),
        ("Project Owner", ProjectMemberRole.PROJECT_OWNER),
        ("Outgoing Member", ProjectMemberRole.OUTGOING),
        ("Incoming Member", ProjectMemberRole.INCOMING),
        ("Reviewer", ProjectMemberRole.REVIEWER),
    ]

    for label, expected_enum in roles:
        add_schema = MemberAdd(email="user@company.internal", role=label)
        assert add_schema.role == expected_enum

        update_schema = MemberUpdateRole(role=label)
        assert update_schema.role == expected_enum
