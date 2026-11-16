"""
Step 2.5 — Security and Authorization Test Suite
================================================

Comprehensive security verification exercising:
1. Every role against every sensitive operation (RBAC matrix).
2. Unauthorized API requests returning appropriate errors (401, 403, 404).
3. Cross-project tenant isolation and IDOR prevention (cannot access another project's documents/handovers).
4. Incoming member handover approval and draft restrictions.
5. Immediate access termination for revoked members.
6. Server-side audit event recording, secret scrubbing, and content protection.
7. Audit trail immutability and rejection of client mutation requests.
8. Backend enforcement of all frontend restrictions.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import (
    UnauthorizedException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.core.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    ProjectRole,
    get_member_permissions,
    has_permission,
    normalize_role,
)
from app.dependencies.authorization import (
    enforce_member_permission,
    require_document_access,
    require_handover_access,
    require_permission,
    require_project_membership,
    require_task_access,
)
from app.models.audit_log import AuditActionType, AuditEntityType, AuditLog
from app.models.document import Document
from app.models.handover import Handover
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.task import Task
from app.models.user import User
from app.schemas.project import MemberAdd, MemberUpdateRole
from app.services.audit_service import AuditService, sanitize_metadata
from app.services.project_service import ProjectService


# =============================================================================
# 1. TEST EVERY ROLE AGAINST EVERY SENSITIVE OPERATION
# =============================================================================

@pytest.mark.parametrize(
    "role,permission,expected_allowed",
    [
        # --- ADMIN: All operations allowed ---
        (ProjectRole.ADMIN, Permission.VIEW_PROJECT, True),
        (ProjectRole.ADMIN, Permission.EDIT_PROJECT, True),
        (ProjectRole.ADMIN, Permission.UPLOAD_DOCUMENTS, True),
        (ProjectRole.ADMIN, Permission.DELETE_DOCUMENTS, True),
        (ProjectRole.ADMIN, Permission.GENERATE_HANDOVER, True),
        (ProjectRole.ADMIN, Permission.VIEW_HANDOVER, True),
        (ProjectRole.ADMIN, Permission.EDIT_HANDOVER, True),
        (ProjectRole.ADMIN, Permission.SUBMIT_HANDOVER_FOR_REVIEW, True),
        (ProjectRole.ADMIN, Permission.APPROVE_HANDOVER, True),
        (ProjectRole.ADMIN, Permission.SHARE_HANDOVER, True),
        (ProjectRole.ADMIN, Permission.MANAGE_PROJECT_MEMBERS, True),
        (ProjectRole.ADMIN, Permission.VIEW_AUDIT_LOGS, True),
        (ProjectRole.ADMIN, Permission.EDIT_APPROVED_HANDOVER, True),

        # --- PROJECT OWNER: All operations allowed ---
        (ProjectRole.PROJECT_OWNER, Permission.VIEW_PROJECT, True),
        (ProjectRole.PROJECT_OWNER, Permission.EDIT_PROJECT, True),
        (ProjectRole.PROJECT_OWNER, Permission.UPLOAD_DOCUMENTS, True),
        (ProjectRole.PROJECT_OWNER, Permission.DELETE_DOCUMENTS, True),
        (ProjectRole.PROJECT_OWNER, Permission.GENERATE_HANDOVER, True),
        (ProjectRole.PROJECT_OWNER, Permission.VIEW_HANDOVER, True),
        (ProjectRole.PROJECT_OWNER, Permission.EDIT_HANDOVER, True),
        (ProjectRole.PROJECT_OWNER, Permission.SUBMIT_HANDOVER_FOR_REVIEW, True),
        (ProjectRole.PROJECT_OWNER, Permission.APPROVE_HANDOVER, True),
        (ProjectRole.PROJECT_OWNER, Permission.SHARE_HANDOVER, True),
        (ProjectRole.PROJECT_OWNER, Permission.MANAGE_PROJECT_MEMBERS, True),
        (ProjectRole.PROJECT_OWNER, Permission.VIEW_AUDIT_LOGS, True),
        (ProjectRole.PROJECT_OWNER, Permission.EDIT_APPROVED_HANDOVER, True),

        # --- OUTGOING MEMBER: Authoring, uploading, submitting, but NO approve, edit project, or manage members ---
        (ProjectRole.OUTGOING, Permission.VIEW_PROJECT, True),
        (ProjectRole.OUTGOING, Permission.EDIT_PROJECT, False),
        (ProjectRole.OUTGOING, Permission.UPLOAD_DOCUMENTS, True),
        (ProjectRole.OUTGOING, Permission.DELETE_DOCUMENTS, True),
        (ProjectRole.OUTGOING, Permission.GENERATE_HANDOVER, True),
        (ProjectRole.OUTGOING, Permission.VIEW_HANDOVER, True),
        (ProjectRole.OUTGOING, Permission.EDIT_HANDOVER, True),
        (ProjectRole.OUTGOING, Permission.SUBMIT_HANDOVER_FOR_REVIEW, True),
        (ProjectRole.OUTGOING, Permission.APPROVE_HANDOVER, False),
        (ProjectRole.OUTGOING, Permission.SHARE_HANDOVER, True),
        (ProjectRole.OUTGOING, Permission.MANAGE_PROJECT_MEMBERS, False),
        (ProjectRole.OUTGOING, Permission.VIEW_AUDIT_LOGS, True),
        (ProjectRole.OUTGOING, Permission.EDIT_APPROVED_HANDOVER, False),

        # --- INCOMING MEMBER: View only, NO edit, upload, approve, generate, or manage members ---
        (ProjectRole.INCOMING, Permission.VIEW_PROJECT, True),
        (ProjectRole.INCOMING, Permission.EDIT_PROJECT, False),
        (ProjectRole.INCOMING, Permission.UPLOAD_DOCUMENTS, False),
        (ProjectRole.INCOMING, Permission.DELETE_DOCUMENTS, False),
        (ProjectRole.INCOMING, Permission.GENERATE_HANDOVER, False),
        (ProjectRole.INCOMING, Permission.VIEW_HANDOVER, True),
        (ProjectRole.INCOMING, Permission.EDIT_HANDOVER, False),
        (ProjectRole.INCOMING, Permission.SUBMIT_HANDOVER_FOR_REVIEW, False),
        (ProjectRole.INCOMING, Permission.APPROVE_HANDOVER, False),
        (ProjectRole.INCOMING, Permission.SHARE_HANDOVER, False),
        (ProjectRole.INCOMING, Permission.MANAGE_PROJECT_MEMBERS, False),
        (ProjectRole.INCOMING, Permission.VIEW_AUDIT_LOGS, False),
        (ProjectRole.INCOMING, Permission.EDIT_APPROVED_HANDOVER, False),

        # --- REVIEWER: View, review, approve, share, audit; NO upload docs, delete docs, edit project, or manage members ---
        (ProjectRole.REVIEWER, Permission.VIEW_PROJECT, True),
        (ProjectRole.REVIEWER, Permission.EDIT_PROJECT, False),
        (ProjectRole.REVIEWER, Permission.UPLOAD_DOCUMENTS, False),
        (ProjectRole.REVIEWER, Permission.DELETE_DOCUMENTS, False),
        (ProjectRole.REVIEWER, Permission.GENERATE_HANDOVER, False),
        (ProjectRole.REVIEWER, Permission.VIEW_HANDOVER, True),
        (ProjectRole.REVIEWER, Permission.EDIT_HANDOVER, False),
        (ProjectRole.REVIEWER, Permission.SUBMIT_HANDOVER_FOR_REVIEW, True),
        (ProjectRole.REVIEWER, Permission.APPROVE_HANDOVER, True),
        (ProjectRole.REVIEWER, Permission.SHARE_HANDOVER, True),
        (ProjectRole.REVIEWER, Permission.MANAGE_PROJECT_MEMBERS, False),
        (ProjectRole.REVIEWER, Permission.VIEW_AUDIT_LOGS, True),
        (ProjectRole.REVIEWER, Permission.EDIT_APPROVED_HANDOVER, False),

        # --- LEAD: Upload, view, edit draft, review, approve, share, audit; NO manage members or edit project settings ---
        (ProjectRole.LEAD, Permission.VIEW_PROJECT, True),
        (ProjectRole.LEAD, Permission.EDIT_PROJECT, False),
        (ProjectRole.LEAD, Permission.UPLOAD_DOCUMENTS, True),
        (ProjectRole.LEAD, Permission.DELETE_DOCUMENTS, False),
        (ProjectRole.LEAD, Permission.GENERATE_HANDOVER, False),
        (ProjectRole.LEAD, Permission.VIEW_HANDOVER, True),
        (ProjectRole.LEAD, Permission.EDIT_HANDOVER, True),
        (ProjectRole.LEAD, Permission.SUBMIT_HANDOVER_FOR_REVIEW, True),
        (ProjectRole.LEAD, Permission.APPROVE_HANDOVER, True),
        (ProjectRole.LEAD, Permission.SHARE_HANDOVER, True),
        (ProjectRole.LEAD, Permission.MANAGE_PROJECT_MEMBERS, False),
        (ProjectRole.LEAD, Permission.VIEW_AUDIT_LOGS, True),
        (ProjectRole.LEAD, Permission.EDIT_APPROVED_HANDOVER, False),
    ],
)
def test_all_roles_against_all_sensitive_operations(role, permission, expected_allowed):
    """
    Exhaustively tests every role against every sensitive operation in the RBAC matrix.
    """
    actual_allowed = has_permission(role, permission)
    assert actual_allowed == expected_allowed, (
        f"Role '{role}' permission '{permission}' was expected to be {expected_allowed}, but got {actual_allowed}."
    )


# =============================================================================
# 2. UNAUTHORIZED API REQUESTS RETURN APPROPRIATE ERRORS (401, 403, 404)
# =============================================================================

@pytest.mark.asyncio
async def test_unauthenticated_request_raises_unauthorized():
    """Unauthenticated requests must raise UnauthorizedException (HTTP 401)."""
    from app.dependencies.auth import get_current_token_payload

    with pytest.raises(UnauthorizedException) as exc:
        await get_current_token_payload(token=None)
    assert "Authentication token is required" in str(exc.value.message)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_jwt_token_raises_unauthorized():
    """Invalid or corrupted JWT tokens must raise UnauthorizedException (HTTP 401)."""
    from app.dependencies.auth import get_current_token_payload

    with pytest.raises(UnauthorizedException) as exc:
        await get_current_token_payload(token="malformed.jwt.token.here")
    assert "Invalid, expired, or malformed" in str(exc.value.message)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_non_member_accessing_project_returns_forbidden_403():
    """A user who is not a member of the project receives HTTP 403 Forbidden."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    with patch("app.dependencies.authorization.get_project_member", return_value=None):
        with pytest.raises(ForbiddenException) as exc:
            await enforce_member_permission(project_id, user_id, Permission.VIEW_PROJECT, mock_db)
        assert "not an authorized member" in str(exc.value.message)


@pytest.mark.asyncio
async def test_unauthorized_role_operation_returns_forbidden_with_descriptive_error():
    """Attempting an operation without the required permission raises ForbiddenException (HTTP 403)."""
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
        invitation_status="accepted",
        custom_permissions=[],
    )

    with patch("app.dependencies.authorization.get_project_member", return_value=member):
        with pytest.raises(ForbiddenException) as exc:
            await enforce_member_permission(project_id, user_id, Permission.UPLOAD_DOCUMENTS, mock_db)
        assert "Missing required permission 'upload_documents'" in str(exc.value.message)


@pytest.mark.asyncio
async def test_nonexistent_project_entity_returns_not_found_404():
    """Accessing an ID that does not exist returns NotFoundException (HTTP 404)."""
    mock_db = AsyncMock()
    nonexistent_id = uuid.uuid4()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_res

    user = User(id=uuid.uuid4(), email="test@company.internal")
    with pytest.raises(NotFoundException) as exc:
        await require_document_access(document_id=nonexistent_id, current_user=user, db=mock_db)
    assert str(nonexistent_id) in str(exc.value)


# =============================================================================
# 3. TENANT ISOLATION: USERS CANNOT ACCESS ANOTHER PROJECT'S DOCUMENTS (IDOR)
# =============================================================================

@pytest.mark.asyncio
async def test_cross_project_document_access_is_strictly_forbidden():
    """
    Tenant Isolation & IDOR Prevention:
    User Alice (Member of Project A) CANNOT access Document D belonging to Project B.
    """
    mock_db = AsyncMock()
    project_a_id = uuid.uuid4()
    project_b_id = uuid.uuid4()
    alice_id = uuid.uuid4()

    alice_user = User(id=alice_id, email="alice@company.internal")

    # Document D belongs to Project B
    doc_b_id = uuid.uuid4()
    doc_b = Document(
        id=doc_b_id,
        project_id=project_b_id,
        uploaded_by=uuid.uuid4(),
        original_filename="Confidential_Payment_Keys.pdf",
        storage_path="/tmp/doc.pdf",
    )

    mock_db_res = MagicMock()
    mock_db_res.scalars.return_value.first.return_value = doc_b
    mock_db.execute.return_value = mock_db_res

    # Alice is NOT a member of Project B (get_project_member returns None for Project B)
    def mock_get_member(project_id, user_id, db):
        if project_id == project_a_id and user_id == alice_id:
            return ProjectMember(
                id=uuid.uuid4(),
                project_id=project_a_id,
                user_id=alice_id,
                role=ProjectMemberRole.ADMIN.value,
                status="active",
            )
        return None  # Alice is not in Project B

    with patch("app.dependencies.authorization.get_project_member", side_effect=mock_get_member):
        # 1. Direct document retrieval must fail with 403 Forbidden
        with pytest.raises(ForbiddenException) as exc:
            await require_document_access(document_id=doc_b_id, current_user=alice_user, db=mock_db)
        assert "not an authorized member of this project workspace" in str(exc.value.message)


@pytest.mark.asyncio
async def test_cross_project_handover_access_is_strictly_forbidden():
    """
    Tenant Isolation:
    User Alice (Member of Project A) CANNOT access Handover H belonging to Project B.
    """
    mock_db = AsyncMock()
    project_b_id = uuid.uuid4()
    alice_user = User(id=uuid.uuid4(), email="alice@company.internal")

    handover_b_id = uuid.uuid4()
    handover_b = Handover(
        id=handover_b_id,
        project_id=project_b_id,
        created_by=uuid.uuid4(),
        status="APPROVED",
    )

    mock_db_res = MagicMock()
    mock_db_res.scalars.return_value.first.return_value = handover_b
    mock_db.execute.return_value = mock_db_res

    with patch("app.dependencies.authorization.get_project_member", return_value=None):
        with pytest.raises(ForbiddenException) as exc:
            await require_handover_access(handover_id=handover_b_id, current_user=alice_user, db=mock_db)
        assert "not an authorized member of this project workspace" in str(exc.value.message)


@pytest.mark.asyncio
async def test_cross_project_task_access_is_strictly_forbidden():
    """
    Tenant Isolation:
    User Alice CANNOT access Task T belonging to another project.
    """
    mock_db = AsyncMock()
    project_b_id = uuid.uuid4()
    alice_user = User(id=uuid.uuid4(), email="alice@company.internal")

    task_b_id = uuid.uuid4()
    task_b = Task(
        id=task_b_id,
        project_id=project_b_id,
        title="Rotate Bastion SSH Keys",
    )

    mock_db_res = MagicMock()
    mock_db_res.scalars.return_value.first.return_value = task_b
    mock_db.execute.return_value = mock_db_res

    with patch("app.dependencies.authorization.get_project_member", return_value=None):
        with pytest.raises(ForbiddenException) as exc:
            await require_task_access(task_id=task_b_id, current_user=alice_user, db=mock_db)
        assert "not an authorized member of this project workspace" in str(exc.value.message)


# =============================================================================
# 4. INCOMING MEMBERS CANNOT APPROVE HANDOVERS WITHOUT PERMISSION
# =============================================================================

@pytest.mark.asyncio
async def test_incoming_member_cannot_approve_handover():
    """
    Incoming members do NOT possess APPROVE_HANDOVER permission.
    Attempting to approve a handover raises ForbiddenException.
    """
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    incoming_id = uuid.uuid4()

    incoming_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
        invitation_status="accepted",
        custom_permissions=[],
    )

    with patch("app.dependencies.authorization.get_project_member", return_value=incoming_member):
        with pytest.raises(ForbiddenException) as exc:
            await enforce_member_permission(
                project_id=project_id,
                user_id=incoming_id,
                permission=Permission.APPROVE_HANDOVER,
                db=mock_db,
            )
        assert "Missing required permission 'approve_handover'" in str(exc.value.message)


@pytest.mark.asyncio
async def test_incoming_member_cannot_view_draft_handover_until_approved():
    """
    Information Leakage Prevention:
    Incoming members are restricted from viewing draft or in-review handovers.
    They can only view handovers once formally APPROVED, SHARED, or ACKNOWLEDGED.
    """
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    incoming_user = User(id=uuid.uuid4(), email="successor@company.internal")

    incoming_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_user.id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
        invitation_status="accepted",
    )

    # 1. Draft handover
    draft_handover = Handover(
        id=uuid.uuid4(),
        project_id=project_id,
        status="DRAFT",
    )
    mock_res_draft = MagicMock()
    mock_res_draft.scalars.return_value.first.return_value = draft_handover
    mock_db.execute.return_value = mock_res_draft

    with patch("app.dependencies.authorization.get_project_member", return_value=incoming_member):
        with pytest.raises(ForbiddenException) as exc:
            await require_handover_access(handover_id=draft_handover.id, current_user=incoming_user, db=mock_db)
        assert "Incoming members can only access handovers after authorized approval" in str(exc.value.message)

    # 2. Approved handover succeeds
    approved_handover = Handover(
        id=uuid.uuid4(),
        project_id=project_id,
        status="APPROVED",
    )
    mock_res_appr = MagicMock()
    mock_res_appr.scalars.return_value.first.return_value = approved_handover
    mock_db.execute.return_value = mock_res_appr

    with patch("app.dependencies.authorization.get_project_member", return_value=incoming_member):
        returned = await require_handover_access(handover_id=approved_handover.id, current_user=incoming_user, db=mock_db)
        assert returned.id == approved_handover.id


@pytest.mark.asyncio
async def test_incoming_member_cannot_edit_approved_handover_without_explicit_override():
    """
    Incoming member cannot modify an already approved handover unless
    explicitly granted 'edit_approved_handover' override.
    """
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    incoming_id = uuid.uuid4()

    # Incoming member with general edit_handover permission
    incoming_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
        custom_permissions=["edit_handover"],
    )

    with patch("app.dependencies.authorization.get_project_member", return_value=incoming_member):
        with pytest.raises(ForbiddenException) as exc:
            await enforce_member_permission(
                project_id=project_id,
                user_id=incoming_id,
                permission=Permission.EDIT_HANDOVER,
                db=mock_db,
                handover_status="APPROVED",
            )
        assert "Incoming members cannot edit approved handovers unless explicitly permitted" in str(exc.value.message)

    # With explicit override permission
    incoming_member.custom_permissions = ["edit_handover", "edit_approved_handover"]
    with patch("app.dependencies.authorization.get_project_member", return_value=incoming_member):
        res = await enforce_member_permission(
            project_id=project_id,
            user_id=incoming_id,
            permission=Permission.EDIT_HANDOVER,
            db=mock_db,
            handover_status="APPROVED",
        )
        assert res.id == incoming_member.id


# =============================================================================
# 5. REVOKED MEMBERS IMMEDIATELY LOSE PROJECT ACCESS
# =============================================================================

@pytest.mark.asyncio
async def test_revoked_member_immediately_blocked_on_subsequent_requests():
    """
    Immediate Access Termination:
    When an admin revokes a member's access, the member's status is set to 'revoked'.
    Subsequent API calls by that member MUST immediately fail with HTTP 403 Forbidden.
    """
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    revoked_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.OUTGOING.value,
        status="revoked",
        invitation_status="revoked",
    )

    with patch("app.dependencies.authorization.get_project_member", return_value=revoked_member):
        # 1. enforce_member_permission check
        with pytest.raises(ForbiddenException) as exc:
            await enforce_member_permission(project_id, user_id, Permission.VIEW_PROJECT, mock_db)
        assert "Your project membership has been revoked" in str(exc.value.message)

        # 2. require_project_membership check
        dep = require_project_membership()
        with pytest.raises(ForbiddenException) as exc:
            await dep(project_id=project_id, current_user=User(id=user_id), db=mock_db)
        assert "Your project membership has been revoked" in str(exc.value.message)


# =============================================================================
# 6. AUDIT EVENTS ARE RECORDED FOR SENSITIVE ACTIONS
# =============================================================================

@pytest.mark.asyncio
async def test_all_12_required_sensitive_actions_record_audit_events():
    """
    Verifies that AuditService correctly records server-side audit events for:
    - user_login
    - user_logout
    - project_created
    - project_updated
    - document_uploaded
    - document_deleted
    - handover_generated
    - handover_modified
    - handover_approved
    - handover_rejected
    - handover_shared
    - version_restored
    - permission_changed
    - member_invited
    - access_revoked
    - conflict_resolved
    """
    mock_db = AsyncMock()
    service = AuditService(mock_db)

    actions = [
        (AuditActionType.USER_LOGIN, AuditEntityType.USER),
        (AuditActionType.USER_LOGOUT, AuditEntityType.USER),
        (AuditActionType.PROJECT_CREATED, AuditEntityType.PROJECT),
        (AuditActionType.PROJECT_UPDATED, AuditEntityType.PROJECT),
        (AuditActionType.DOCUMENT_UPLOADED, AuditEntityType.DOCUMENT),
        (AuditActionType.DOCUMENT_DELETED, AuditEntityType.DOCUMENT),
        (AuditActionType.HANDOVER_GENERATED, AuditEntityType.HANDOVER),
        (AuditActionType.HANDOVER_MODIFIED, AuditEntityType.HANDOVER),
        (AuditActionType.HANDOVER_APPROVED, AuditEntityType.HANDOVER),
        (AuditActionType.HANDOVER_REJECTED, AuditEntityType.HANDOVER),
        (AuditActionType.HANDOVER_SHARED, AuditEntityType.HANDOVER),
        (AuditActionType.VERSION_RESTORED, AuditEntityType.HANDOVER),
        (AuditActionType.PERMISSION_CHANGED, AuditEntityType.PROJECT_MEMBER),
        (AuditActionType.MEMBER_INVITED, AuditEntityType.PROJECT_MEMBER),
        (AuditActionType.ACCESS_REVOKED, AuditEntityType.PROJECT_MEMBER),
        (AuditActionType.CONFLICT_RESOLVED, AuditEntityType.CONFLICT),
    ]

    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    for action, entity_type in actions:
        entity_id = uuid.uuid4()
        record = await service.record_event(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            project_id=project_id,
            change_metadata={"test_field": f"value_for_{action.value}"},
            commit=False,
        )
        assert record is not None
        assert record.action == action.value
        assert record.entity_type == entity_type.value
        assert record.entity_id == str(entity_id)
        assert record.user_id == user_id
        assert record.project_id == project_id
        assert record.timestamp is not None
        assert record.change_metadata["test_field"] == f"value_for_{action.value}"


def test_audit_scrubbing_prevents_secret_leakage_and_protects_document_contents():
    """
    Security Requirements 4 & 5:
    - Passwords, API keys, tokens are replaced with [REDACTED].
    - Sensitive full document contents and bodies are scrubbed from metadata.
    """
    dirty_metadata = {
        "password": "super_secret_password_123",
        "api_key": "sk-proj-999988887777",
        "access_token": "bearer.eyJhbGciOi...",
        "content": "This is a full confidential 50-page document body that must not leak into logs",
        "body": "Private financial statements...",
        "original_filename": "Quarterly_Financials.pdf",
        "file_size": 45000,
    }

    sanitized = sanitize_metadata(dirty_metadata)

    # Secrets scrubbed
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"

    # Document contents protected
    assert "[CONTENT_OMITTED:" in sanitized["content"]
    assert "[CONTENT_OMITTED:" in sanitized["body"]
    assert sanitized["content_length"] == len("This is a full confidential 50-page document body that must not leak into logs")

    # Non-sensitive metadata retained
    assert sanitized["original_filename"] == "Quarterly_Financials.pdf"
    assert sanitized["file_size"] == 45000


# =============================================================================
# 7. ORDINARY USERS CANNOT MODIFY AUDIT HISTORY (IMMUTABILITY)
# =============================================================================

@pytest.mark.asyncio
async def test_audit_mutation_endpoints_raise_forbidden_403():
    """
    Security Guarantee: Audit records are immutable.
    Client-side creation, modification, or deletion is strictly blocked with HTTP 403 Forbidden.
    """
    from app.api.v1.endpoints.audit import reject_audit_mutation

    with pytest.raises(ForbiddenException) as exc:
        await reject_audit_mutation()
    assert "Audit trail records are immutable and cannot be created, modified, or deleted" in str(exc.value.message)


# =============================================================================
# 8. FRONTEND RESTRICTIONS ARE ALSO ENFORCED BY BACKEND AUTHORIZATION
# =============================================================================

@pytest.mark.asyncio
async def test_backend_enforces_cannot_remove_or_demote_last_project_admin():
    """
    Governance Integrity:
    A user cannot bypass the frontend to remove or demote the sole remaining Admin/Owner.
    """
    mock_db = AsyncMock()
    service = ProjectService(mock_db)

    project_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    admin_member = ProjectMember(
        id=admin_id,
        project_id=project_id,
        user_id=uuid.uuid4(),
        role=ProjectMemberRole.ADMIN.value,
        status="active",
    )

    with patch.object(service.project_repo, "get_member_by_id", return_value=admin_member):
        with patch.object(service.project_repo, "count_admins", return_value=1):
            # 1. Attempting to demote to INCOMING raises ConflictException
            update_payload = MemberUpdateRole(role=ProjectMemberRole.INCOMING)
            with pytest.raises(ConflictException) as exc:
                await service.update_member_role(project_id, admin_id, update_payload)
            assert "must retain at least one active ADMIN or Project Owner" in str(exc.value.message)

            # 2. Attempting to remove member raises ConflictException
            with pytest.raises(ConflictException) as exc2:
                await service.remove_member(project_id, admin_id)
            assert "must retain at least one active ADMIN or Project Owner" in str(exc2.value.message)


@pytest.mark.asyncio
async def test_non_owner_inviting_member_rejected_by_backend():
    """
    Frontend Gating Backend Enforcement:
    Even if an unauthorized member sends a direct POST /projects/{id}/members request,
    the require_permission(MANAGE_PROJECT_MEMBERS) dependency blocks it.
    """
    mock_db = AsyncMock()
    project_id = uuid.uuid4()
    outgoing_id = uuid.uuid4()

    outgoing_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=outgoing_id,
        role=ProjectMemberRole.OUTGOING.value,
        status="active",
        custom_permissions=[],
    )

    with patch("app.dependencies.authorization.get_project_member", return_value=outgoing_member):
        with pytest.raises(ForbiddenException) as exc:
            await enforce_member_permission(
                project_id=project_id,
                user_id=outgoing_id,
                permission=Permission.MANAGE_PROJECT_MEMBERS,
                db=mock_db,
            )
        assert "Missing required permission 'manage_project_members'" in str(exc.value.message)
