"""
Improvement 2 Security & Functional Audit Test Suite
===================================================

This test suite performs an exhaustive security and functional audit of Improvement 2
(Role-Based Access Control and Audit Trail):

Accounts:
- Admin (User 1)
- Project Owner (User 2)
- Outgoing Member (User 3)
- Incoming Member (User 4)
- Reviewer (User 5)

Two Separate Projects:
- Project Alpha (Managed by Project Owner; Outgoing, Reviewer, and Incoming members)
- Project Beta (Isolated Project; Owned by Admin; Outgoing and Incoming have NO access)

Scenarios Tested:
1. Project owners can manage their project members (invite, update role, permissions, revoke).
2. Incoming members cannot access projects that were not shared with them (Project Beta access denied).
3. Outgoing members cannot perform unauthorized approval actions (approval/rejection blocked).
4. Reviewers can approve or reject handovers only when authorized (Project Alpha allowed, Project Beta blocked).
5. Unauthorized users cannot upload or delete documents (Incoming & Reviewer blocked, Outgoing allowed).
6. Revoked members lose access immediately upon revocation.
7. Direct API requests cannot bypass permissions (enforced by backend dependencies, not just UI).
8. Users cannot access another project's data by changing resource IDs (IDOR protection on Documents, Handovers, Tasks).
9. Permission changes are reflected immediately (custom permission grant/revoke evaluated dynamically).
10. Audit logs record all important actions with actor, action, project, timestamp, entity reference, and metadata.
11. Immutability verification: Ordinary users and clients cannot create, modify, or delete audit records.
"""

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.permissions import Permission, ProjectRole, has_permission, get_member_permissions
from app.core.security import create_access_token, get_password_hash
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import (
    enforce_member_permission,
    require_document_access,
    require_handover_access,
    require_permission,
    require_task_access,
)
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_log import AuditActionType, AuditEntityType, AuditLog
from app.models.base import Base
from app.models.document import Document
from app.models.handover import Handover, HandoverSection
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.task import Task
from app.models.user import User
from app.schemas.project import MemberAdd, MemberUpdateRole
from app.services.audit_service import AuditService
from app.services.project_service import ProjectService


# ==============================================================================
# DATABASE FIXTURE & ISOLATED ENVIRONMENT SETUP
# ==============================================================================

@pytest_asyncio.fixture
async def audit_test_db():
    """Sets up an isolated in-memory SQLite database populated with all required tables."""
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
async def audit_environment(audit_test_db: AsyncSession):
    """
    Sets up the mandatory 5 test accounts and 2 separate projects:
    - User: Admin
    - User: Project Owner
    - User: Outgoing Member
    - User: Incoming Member
    - User: Reviewer
    - Project Alpha (Owner's project)
    - Project Beta (Isolated project)
    """
    # 1. Accounts
    admin = User(
        id=uuid.uuid4(),
        email="admin@security.corp",
        full_name="Global Administrator",
        password_hash=get_password_hash("AdminPass123!"),
        is_active=True,
    )
    owner = User(
        id=uuid.uuid4(),
        email="owner@security.corp",
        full_name="Project Alpha Owner",
        password_hash=get_password_hash("OwnerPass123!"),
        is_active=True,
    )
    outgoing = User(
        id=uuid.uuid4(),
        email="outgoing@security.corp",
        full_name="Outgoing Lead Engineer",
        password_hash=get_password_hash("OutgoingPass123!"),
        is_active=True,
    )
    incoming = User(
        id=uuid.uuid4(),
        email="incoming@security.corp",
        full_name="Incoming Junior Engineer",
        password_hash=get_password_hash("IncomingPass123!"),
        is_active=True,
    )
    reviewer = User(
        id=uuid.uuid4(),
        email="reviewer@security.corp",
        full_name="Principal Reviewer",
        password_hash=get_password_hash("ReviewerPass123!"),
        is_active=True,
    )

    audit_test_db.add_all([admin, owner, outgoing, incoming, reviewer])
    await audit_test_db.commit()

    # 2. Project Alpha (Target workspace)
    project_alpha = Project(
        id=uuid.uuid4(),
        name="Project Alpha Workspace",
        description="Core financial settlement gateway",
        created_by=owner.id,
    )

    # 3. Project Beta (Isolated workspace to test cross-tenant boundary and IDOR)
    project_beta = Project(
        id=uuid.uuid4(),
        name="Project Beta Workspace",
        description="Confidential HR system",
        created_by=admin.id,
    )

    audit_test_db.add_all([project_alpha, project_beta])
    await audit_test_db.commit()

    # 4. Project Alpha Memberships
    member_owner_alpha = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_alpha.id,
        user_id=owner.id,
        role=ProjectRole.PROJECT_OWNER.value,
        status="active",
        invitation_status="accepted",
    )
    member_outgoing_alpha = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_alpha.id,
        user_id=outgoing.id,
        role=ProjectRole.OUTGOING.value,
        status="active",
        invitation_status="accepted",
    )
    member_reviewer_alpha = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_alpha.id,
        user_id=reviewer.id,
        role=ProjectRole.REVIEWER.value,
        status="active",
        invitation_status="accepted",
    )
    member_incoming_alpha = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_alpha.id,
        user_id=incoming.id,
        role=ProjectRole.INCOMING.value,
        status="active",
        invitation_status="accepted",
    )

    # 5. Project Beta Memberships (Only Admin is member; Incoming, Outgoing, Reviewer, Owner are NOT members)
    member_admin_beta = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_beta.id,
        user_id=admin.id,
        role=ProjectRole.ADMIN.value,
        status="active",
        invitation_status="accepted",
    )

    audit_test_db.add_all([
        member_owner_alpha,
        member_outgoing_alpha,
        member_reviewer_alpha,
        member_incoming_alpha,
        member_admin_beta,
    ])
    await audit_test_db.commit()

    # 6. Artifacts in Project Alpha & Beta for IDOR testing
    doc_alpha = Document(
        id=uuid.uuid4(),
        project_id=project_alpha.id,
        uploaded_by=owner.id,
        original_filename="alpha_architecture.md",
        stored_filename="alpha_stored.md",
        file_type="md",
        file_size=1024,
        storage_path="/tmp/alpha.md",
        processing_status="completed",
    )
    doc_beta = Document(
        id=uuid.uuid4(),
        project_id=project_beta.id,
        uploaded_by=admin.id,
        original_filename="beta_confidential_salaries.pdf",
        stored_filename="beta_stored.pdf",
        file_type="pdf",
        file_size=2048,
        storage_path="/tmp/beta.pdf",
        processing_status="completed",
    )

    handover_alpha = Handover(
        id=uuid.uuid4(),
        project_id=project_alpha.id,
        created_by=outgoing.id,
        title="Alpha Core Handover v1",
        status="DRAFT",
        version=1,
    )
    handover_beta = Handover(
        id=uuid.uuid4(),
        project_id=project_beta.id,
        created_by=admin.id,
        title="Beta Executive Handover v1",
        status="DRAFT",
        version=1,
    )

    task_alpha = Task(
        id=uuid.uuid4(),
        project_id=project_alpha.id,
        title="Verify Alpha Ingress",
        description="Check TLS 1.3 ports",
        status="NOT_STARTED",
    )
    task_beta = Task(
        id=uuid.uuid4(),
        project_id=project_beta.id,
        title="Audit Beta Payroll",
        description="HR restricted audit",
        status="NOT_STARTED",
    )

    audit_test_db.add_all([doc_alpha, doc_beta, handover_alpha, handover_beta, task_alpha, task_beta])
    await audit_test_db.commit()

    return {
        "admin": admin,
        "owner": owner,
        "outgoing": outgoing,
        "incoming": incoming,
        "reviewer": reviewer,
        "project_alpha": project_alpha,
        "project_beta": project_beta,
        "member_owner_alpha": member_owner_alpha,
        "member_outgoing_alpha": member_outgoing_alpha,
        "member_reviewer_alpha": member_reviewer_alpha,
        "member_incoming_alpha": member_incoming_alpha,
        "member_admin_beta": member_admin_beta,
        "doc_alpha": doc_alpha,
        "doc_beta": doc_beta,
        "handover_alpha": handover_alpha,
        "handover_beta": handover_beta,
        "task_alpha": task_alpha,
        "task_beta": task_beta,
    }


# ==============================================================================
# 1. PROJECT OWNERS CAN MANAGE THEIR PROJECT MEMBERS
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_1_project_owner_can_manage_members(audit_test_db: AsyncSession, audit_environment: dict):
    """Verifies project owners can invite, update roles, edit permissions, and revoke members."""
    owner = audit_environment["owner"]
    alpha = audit_environment["project_alpha"]
    proj_service = ProjectService(audit_test_db)

    # 1. Project Owner has MANAGE_PROJECT_MEMBERS permission
    allowed = has_permission(ProjectRole.PROJECT_OWNER, Permission.MANAGE_PROJECT_MEMBERS)
    assert allowed is True

    # 2. Invite a new member
    new_user = User(
        id=uuid.uuid4(),
        email="contractor@security.corp",
        full_name="Contractor User",
        password_hash="pwd",
    )
    audit_test_db.add(new_user)
    await audit_test_db.commit()

    add_payload = MemberAdd(
        email="contractor@security.corp",
        role=ProjectMemberRole.INCOMING,
        invitation_status="invited",
    )
    new_member = await proj_service.add_member(alpha.id, add_payload, inviter_id=owner.id)
    assert new_member.user_id == new_user.id
    assert new_member.role == ProjectRole.INCOMING.value

    # 3. Update member's role to REVIEWER
    update_payload = MemberUpdateRole(role=ProjectMemberRole.REVIEWER)
    updated = await proj_service.update_member_role(alpha.id, new_member.id, update_payload)
    assert updated.role == ProjectRole.REVIEWER.value

    # 4. Revoke member access
    revoked = await proj_service.revoke_member_access(alpha.id, new_member.id)
    assert revoked.status == "revoked"


# ==============================================================================
# 2. INCOMING MEMBERS CANNOT ACCESS UNSHARED PROJECTS
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_2_incoming_member_cannot_access_unshared_projects(audit_test_db: AsyncSession, audit_environment: dict):
    """Verifies incoming member can access Project Alpha (shared) but is denied access to Project Beta (unshared)."""
    incoming = audit_environment["incoming"]
    alpha = audit_environment["project_alpha"]
    beta = audit_environment["project_beta"]

    # Allowed in Alpha
    alpha_member = await enforce_member_permission(alpha.id, incoming.id, Permission.VIEW_PROJECT, audit_test_db)
    assert alpha_member.project_id == alpha.id

    # Strictly Denied in Beta (raises HTTP 403 Forbidden)
    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(beta.id, incoming.id, Permission.VIEW_PROJECT, audit_test_db)
    assert "not an authorized member" in str(exc_info.value.message)


# ==============================================================================
# 3. OUTGOING MEMBERS CANNOT PERFORM UNAUTHORIZED APPROVAL ACTIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_3_outgoing_member_cannot_approve_or_reject_handovers(audit_test_db: AsyncSession, audit_environment: dict):
    """Verifies outgoing members can submit handovers but cannot perform approval or rejection sign-offs."""
    outgoing = audit_environment["outgoing"]
    alpha = audit_environment["project_alpha"]

    # Can submit handover for review
    submit_allowed = has_permission(ProjectRole.OUTGOING, Permission.SUBMIT_HANDOVER_FOR_REVIEW)
    assert submit_allowed is True

    # CANNOT approve handover
    approve_allowed = has_permission(ProjectRole.OUTGOING, Permission.APPROVE_HANDOVER)
    assert approve_allowed is False

    # Enforce check raises ForbiddenException
    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(alpha.id, outgoing.id, Permission.APPROVE_HANDOVER, audit_test_db)
    assert "Missing required permission 'approve_handover'" in str(exc_info.value.message)


# ==============================================================================
# 4. REVIEWERS CAN APPROVE/REJECT HANDOVERS ONLY WHEN AUTHORIZED
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_4_reviewer_authorization_scope(audit_test_db: AsyncSession, audit_environment: dict):
    """Verifies Reviewer can approve in Alpha where authorized, but is blocked in Beta where not a member."""
    reviewer = audit_environment["reviewer"]
    alpha = audit_environment["project_alpha"]
    beta = audit_environment["project_beta"]

    # Reviewer can approve in Project Alpha
    alpha_member = await enforce_member_permission(alpha.id, reviewer.id, Permission.APPROVE_HANDOVER, audit_test_db)
    assert alpha_member.role == ProjectRole.REVIEWER.value

    # Reviewer CANNOT approve in Project Beta (Tenant boundary)
    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(beta.id, reviewer.id, Permission.APPROVE_HANDOVER, audit_test_db)
    assert "not an authorized member" in str(exc_info.value.message)


# ==============================================================================
# 5. UNAUTHORIZED USERS CANNOT UPLOAD OR DELETE DOCUMENTS
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_5_document_upload_and_delete_permissions(audit_test_db: AsyncSession, audit_environment: dict):
    """Verifies Incoming Member and Reviewer cannot upload/delete documents, whereas Outgoing Member can."""
    alpha = audit_environment["project_alpha"]
    incoming = audit_environment["incoming"]
    reviewer = audit_environment["reviewer"]
    outgoing = audit_environment["outgoing"]

    # Incoming member upload -> BLOCKED
    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(alpha.id, incoming.id, Permission.UPLOAD_DOCUMENTS, audit_test_db)
    assert "Missing required permission 'upload_documents'" in str(exc_info.value.message)

    # Incoming member delete -> BLOCKED
    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(alpha.id, incoming.id, Permission.DELETE_DOCUMENTS, audit_test_db)
    assert "Missing required permission 'delete_documents'" in str(exc_info.value.message)

    # Reviewer upload -> BLOCKED
    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(alpha.id, reviewer.id, Permission.UPLOAD_DOCUMENTS, audit_test_db)
    assert "Missing required permission 'upload_documents'" in str(exc_info.value.message)

    # Outgoing member upload & delete -> ALLOWED
    out_upload = await enforce_member_permission(alpha.id, outgoing.id, Permission.UPLOAD_DOCUMENTS, audit_test_db)
    assert out_upload.role == ProjectRole.OUTGOING.value
    out_del = await enforce_member_permission(alpha.id, outgoing.id, Permission.DELETE_DOCUMENTS, audit_test_db)
    assert out_del.role == ProjectRole.OUTGOING.value


# ==============================================================================
# 6. REVOKED MEMBERS LOSE ACCESS IMMEDIATELY
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_6_revoked_members_lose_access_immediately(audit_test_db: AsyncSession, audit_environment: dict):
    """Verifies that revoking a member immediately cuts off access to all project resources."""
    alpha = audit_environment["project_alpha"]
    outgoing = audit_environment["outgoing"]
    member_record = audit_environment["member_outgoing_alpha"]

    # Initially active -> Access granted
    active_check = await enforce_member_permission(alpha.id, outgoing.id, Permission.VIEW_PROJECT, audit_test_db)
    assert active_check is not None

    # Revoke member status
    member_record.status = "revoked"
    await audit_test_db.commit()

    # Immediate access attempt -> BLOCKED with explicit revoked error
    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(alpha.id, outgoing.id, Permission.VIEW_PROJECT, audit_test_db)
    assert "membership has been revoked" in str(exc_info.value.message)


# ==============================================================================
# 7. DIRECT API REQUESTS CANNOT BYPASS PERMISSIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_7_direct_api_requests_cannot_bypass_permissions(audit_test_db: AsyncSession, audit_environment: dict):
    """
    Simulates direct HTTP requests via FastAPI client with valid JWT tokens
    verifying backend dependencies return HTTP 403 Forbidden regardless of client UI.
    """
    alpha = audit_environment["project_alpha"]
    outgoing = audit_environment["outgoing"]
    incoming = audit_environment["incoming"]
    handover = audit_environment["handover_alpha"]

    # Generate valid JWT tokens
    token_outgoing = create_access_token(outgoing.id, email=outgoing.email)
    token_incoming = create_access_token(incoming.id, email=incoming.email)

    # Override database dependency with our live test DB session
    async def override_get_db():
        yield audit_test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Outgoing engineer directly POSTs to approval endpoint -> 403 Forbidden
            approve_url = f"/api/v1/handovers/{handover.id}/approve"
            res = await client.post(
                approve_url,
                headers={"Authorization": f"Bearer {token_outgoing}"},
                json={"comments": "Direct bypass attempt"},
            )
            assert res.status_code == 403
            assert "approve_handover" in res.text

            # 2. Incoming engineer directly POSTs to member management endpoint -> 403 Forbidden
            invite_url = f"/api/v1/projects/{alpha.id}/members"
            res_invite = await client.post(
                invite_url,
                headers={"Authorization": f"Bearer {token_incoming}"},
                json={"email": "attacker@corp.io", "role": "ADMIN"},
            )
            assert res_invite.status_code == 403
            assert "manage_project_members" in res_invite.text

    finally:
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# 8. IDOR PROTECTION: CANNOT ACCESS ANOTHER PROJECT'S RESOURCES
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_8_idor_protection_cross_project_isolation(audit_test_db: AsyncSession, audit_environment: dict):
    """
    Tests Insecure Direct Object Reference (IDOR) prevention:
    A user who is a member of Project Alpha attempts to access Document, Handover, and Task
    belonging to Project Beta by manipulating UUIDs in requests.
    """
    outgoing = audit_environment["outgoing"]  # Member of Alpha, NOT Beta
    doc_beta = audit_environment["doc_beta"]
    handover_beta = audit_environment["handover_beta"]
    task_beta = audit_environment["task_beta"]

    # 1. Document IDOR: Attempting to resolve Beta's document raises ForbiddenException
    with pytest.raises(ForbiddenException) as exc_doc:
        await require_document_access(document_id=doc_beta.id, current_user=outgoing, db=audit_test_db)
    assert "not an authorized member" in str(exc_doc.value.message)

    # 2. Handover IDOR: Attempting to resolve Beta's handover raises ForbiddenException
    with pytest.raises(ForbiddenException) as exc_h:
        await require_handover_access(handover_id=handover_beta.id, current_user=outgoing, db=audit_test_db)
    assert "not an authorized member" in str(exc_h.value.message)

    # 3. Task IDOR: Attempting to resolve Beta's task raises ForbiddenException
    with pytest.raises(ForbiddenException) as exc_t:
        await require_task_access(task_id=task_beta.id, current_user=outgoing, db=audit_test_db)
    assert "not an authorized member" in str(exc_t.value.message)


# ==============================================================================
# 9. PERMISSION CHANGES ARE REFLECTED IMMEDIATELY
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_9_permission_changes_reflected_immediately(audit_test_db: AsyncSession, audit_environment: dict):
    """Verifies that granting/revoking custom permissions takes effect on the very next request without re-login."""
    alpha = audit_environment["project_alpha"]
    incoming = audit_environment["incoming"]
    member_record = audit_environment["member_incoming_alpha"]

    # 1. Incoming member initially has NO upload_documents permission
    allowed_initial = has_permission(member_record.role, Permission.UPLOAD_DOCUMENTS, member_record.custom_permissions)
    assert allowed_initial is False

    with pytest.raises(ForbiddenException):
        await enforce_member_permission(alpha.id, incoming.id, Permission.UPLOAD_DOCUMENTS, audit_test_db)

    # 2. Project Owner grants custom permission: upload_documents
    member_record.custom_permissions = [Permission.UPLOAD_DOCUMENTS.value]
    await audit_test_db.commit()

    # 3. Incoming member immediately allowed to upload
    member_granted = await enforce_member_permission(alpha.id, incoming.id, Permission.UPLOAD_DOCUMENTS, audit_test_db)
    assert Permission.UPLOAD_DOCUMENTS in get_member_permissions(member_granted.role, member_granted.custom_permissions)

    # 4. Project Owner revokes custom permission
    member_record.custom_permissions = []
    await audit_test_db.commit()

    # 5. Immediate block on next request
    with pytest.raises(ForbiddenException):
        await enforce_member_permission(alpha.id, incoming.id, Permission.UPLOAD_DOCUMENTS, audit_test_db)


# ==============================================================================
# 10. AUDIT LOGS RECORD ALL IMPORTANT ACTIONS WITH MANDATORY FIELDS
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_10_audit_log_completeness_and_metadata(audit_test_db: AsyncSession, audit_environment: dict):
    """
    Verifies that audit logs record all required fields:
    - Actor (user_id)
    - Action (action)
    - Related project (project_id)
    - Timestamp (timestamp)
    - Entity reference (entity_type, entity_id)
    - Relevant change metadata (change_metadata)
    """
    alpha = audit_environment["project_alpha"]
    owner = audit_environment["owner"]
    audit_svc = AuditService(audit_test_db)

    # Record sensitive actions
    actions_to_record = [
        (AuditActionType.MEMBER_INVITED, AuditEntityType.PROJECT_MEMBER, str(uuid.uuid4()), {"role": "INCOMING", "email": "dev@corp.io"}),
        (AuditActionType.PERMISSION_CHANGED, AuditEntityType.PROJECT_MEMBER, str(uuid.uuid4()), {"added_permissions": ["upload_documents"]}),
        (AuditActionType.ACCESS_REVOKED, AuditEntityType.PROJECT_MEMBER, str(uuid.uuid4()), {"revocation_reason": "Contract ended"}),
        (AuditActionType.HANDOVER_APPROVED, AuditEntityType.HANDOVER, str(uuid.uuid4()), {"version": 1, "approved_by": "Principal Reviewer"}),
        (AuditActionType.DOCUMENT_DELETED, AuditEntityType.DOCUMENT, str(uuid.uuid4()), {"filename": "deprecated_spec.md"}),
    ]

    for action, entity_type, entity_id, meta in actions_to_record:
        await audit_svc.record_event(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=owner.id,
            project_id=alpha.id,
            change_metadata=meta,
        )

    # Query recorded audit logs for Project Alpha
    items, total = await audit_svc.list_project_audit_logs(alpha.id, page=1, page_size=20)
    assert total >= 5

    for item in items:
        # Mandatory audit fields verification
        assert item.user_id == owner.id, "Audit record must capture the Actor (user_id)"
        assert item.action is not None, "Audit record must capture Action"
        assert item.project_id == alpha.id, "Audit record must link to Related Project"
        assert item.timestamp is not None, "Audit record must include valid Timestamp"
        assert item.entity_type is not None, "Audit record must specify Entity Type"
        assert item.entity_id is not None, "Audit record must specify Entity Reference ID"
        assert isinstance(item.change_metadata, dict), "Audit record must contain change metadata"


# ==============================================================================
# 11. IMMUTABILITY VERIFICATION: ORDINARY USERS CANNOT MUTATE AUDIT RECORDS
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_11_audit_logs_are_immutable(audit_test_db: AsyncSession, audit_environment: dict):
    """
    Verifies that client requests attempting to POST, PUT, PATCH, or DELETE audit log records
    are explicitly rejected with HTTP 403 Forbidden.
    """
    alpha = audit_environment["project_alpha"]
    owner = audit_environment["owner"]
    token_owner = create_access_token(owner.id, email=owner.email)
    audit_id = uuid.uuid4()

    async def override_get_db():
        yield audit_test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {token_owner}"}

            # 1. Attempt POST to create client-side audit record -> 403 Forbidden
            res_post = await client.post(f"/api/v1/projects/{alpha.id}/audit-logs", headers=headers, json={"action": "fake"})
            assert res_post.status_code == 403
            assert "immutable" in res_post.text

            # 2. Attempt PUT to modify audit record -> 403 Forbidden
            res_put = await client.put(f"/api/v1/projects/{alpha.id}/audit-logs/{audit_id}", headers=headers, json={"action": "fake"})
            assert res_put.status_code == 403
            assert "immutable" in res_put.text

            # 3. Attempt PATCH to alter metadata -> 403 Forbidden
            res_patch = await client.patch(f"/api/v1/projects/{alpha.id}/audit-logs/{audit_id}", headers=headers, json={"change_metadata": {}})
            assert res_patch.status_code == 403
            assert "immutable" in res_patch.text

            # 4. Attempt DELETE to destroy audit evidence -> 403 Forbidden
            res_delete = await client.delete(f"/api/v1/projects/{alpha.id}/audit-logs/{audit_id}", headers=headers)
            assert res_delete.status_code == 403
            assert "immutable" in res_delete.text

    finally:
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# 12. COMPREHENSIVE ROLE-VERSUS-PERMISSION MATRIX AUDIT
# ==============================================================================

def test_scenario_12_comprehensive_role_permission_matrix_audit():
    """
    Exhaustively verifies all 5 roles against every defined permission (70 matrix checks):
    - Admin: Full authority across all 14 permissions
    - Project Owner: Full project authority across all 14 permissions
    - Outgoing Member: Document management, handover drafting, review submission, audit view
    - Incoming Member: Read-only project/handover inspection (strictly blocked on edit/approve/delete)
    - Reviewer: Handover review, approval, rejection, conflict resolution, audit view
    """
    all_permissions = list(Permission)
    assert len(all_permissions) >= 12

    # Expected permission sets per role
    matrix = {
        ProjectRole.ADMIN: {
            Permission.VIEW_PROJECT: True,
            Permission.EDIT_PROJECT: True,
            Permission.UPLOAD_DOCUMENTS: True,
            Permission.DELETE_DOCUMENTS: True,
            Permission.GENERATE_HANDOVER: True,
            Permission.VIEW_HANDOVER: True,
            Permission.EDIT_HANDOVER: True,
            Permission.SUBMIT_HANDOVER_FOR_REVIEW: True,
            Permission.APPROVE_HANDOVER: True,
            Permission.SHARE_HANDOVER: True,
            Permission.MANAGE_PROJECT_MEMBERS: True,
            Permission.VIEW_AUDIT_LOGS: True,
            Permission.RESOLVE_CONFLICT: True,
            Permission.EDIT_APPROVED_HANDOVER: True,
        },
        ProjectRole.PROJECT_OWNER: {
            Permission.VIEW_PROJECT: True,
            Permission.EDIT_PROJECT: True,
            Permission.UPLOAD_DOCUMENTS: True,
            Permission.DELETE_DOCUMENTS: True,
            Permission.GENERATE_HANDOVER: True,
            Permission.VIEW_HANDOVER: True,
            Permission.EDIT_HANDOVER: True,
            Permission.SUBMIT_HANDOVER_FOR_REVIEW: True,
            Permission.APPROVE_HANDOVER: True,
            Permission.SHARE_HANDOVER: True,
            Permission.MANAGE_PROJECT_MEMBERS: True,
            Permission.VIEW_AUDIT_LOGS: True,
            Permission.RESOLVE_CONFLICT: True,
            Permission.EDIT_APPROVED_HANDOVER: True,
        },
        ProjectRole.OUTGOING: {
            Permission.VIEW_PROJECT: True,
            Permission.EDIT_PROJECT: False,
            Permission.UPLOAD_DOCUMENTS: True,
            Permission.DELETE_DOCUMENTS: True,
            Permission.GENERATE_HANDOVER: True,
            Permission.VIEW_HANDOVER: True,
            Permission.EDIT_HANDOVER: True,
            Permission.SUBMIT_HANDOVER_FOR_REVIEW: True,
            Permission.APPROVE_HANDOVER: False,
            Permission.SHARE_HANDOVER: True,
            Permission.MANAGE_PROJECT_MEMBERS: False,
            Permission.VIEW_AUDIT_LOGS: True,
            Permission.RESOLVE_CONFLICT: False,
            Permission.EDIT_APPROVED_HANDOVER: False,
        },
        ProjectRole.INCOMING: {
            Permission.VIEW_PROJECT: True,
            Permission.EDIT_PROJECT: False,
            Permission.UPLOAD_DOCUMENTS: False,
            Permission.DELETE_DOCUMENTS: False,
            Permission.GENERATE_HANDOVER: False,
            Permission.VIEW_HANDOVER: True,
            Permission.EDIT_HANDOVER: False,
            Permission.SUBMIT_HANDOVER_FOR_REVIEW: False,
            Permission.APPROVE_HANDOVER: False,
            Permission.SHARE_HANDOVER: False,
            Permission.MANAGE_PROJECT_MEMBERS: False,
            Permission.VIEW_AUDIT_LOGS: False,
            Permission.RESOLVE_CONFLICT: False,
            Permission.EDIT_APPROVED_HANDOVER: False,
        },
        ProjectRole.REVIEWER: {
            Permission.VIEW_PROJECT: True,
            Permission.EDIT_PROJECT: False,
            Permission.UPLOAD_DOCUMENTS: False,
            Permission.DELETE_DOCUMENTS: False,
            Permission.GENERATE_HANDOVER: False,
            Permission.VIEW_HANDOVER: True,
            Permission.EDIT_HANDOVER: False,
            Permission.SUBMIT_HANDOVER_FOR_REVIEW: True,
            Permission.APPROVE_HANDOVER: True,
            Permission.SHARE_HANDOVER: True,
            Permission.MANAGE_PROJECT_MEMBERS: False,
            Permission.VIEW_AUDIT_LOGS: True,
            Permission.RESOLVE_CONFLICT: False,  # Only when granted custom permission
            Permission.EDIT_APPROVED_HANDOVER: False,
        },
    }

    total_matrix_checks = 0
    for role, perm_expectations in matrix.items():
        for perm, expected_allowed in perm_expectations.items():
            actual = has_permission(role, perm)
            assert actual == expected_allowed, (
                f"Role {role.value} permission check for '{perm.value}' failed: "
                f"expected {expected_allowed}, got {actual}"
            )
            total_matrix_checks += 1

    assert total_matrix_checks == 70, f"Expected 70 matrix checks, got {total_matrix_checks}"


# ==============================================================================
# 13. AUDIT LOG SECURITY SANITIZATION & REDACTION
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_13_audit_log_security_redaction_and_tamper_evidence(audit_test_db: AsyncSession, audit_environment: dict):
    """
    Verifies that the Audit subsystem automatically scrubs sensitive secrets, passwords,
    and tokens from change metadata before database storage.
    """
    alpha = audit_environment["project_alpha"]
    owner = audit_environment["owner"]
    audit_svc = AuditService(audit_test_db)

    sensitive_payload = {
        "password": "SuperSecretPassword123!",
        "new_password": "NewSecretPassword456!",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "api_key": "AIzaSyDummyKey...",
        "safe_field": "public_description_update",
    }

    event = await audit_svc.record_event(
        action=AuditActionType.PROJECT_UPDATED,
        entity_type=AuditEntityType.PROJECT,
        entity_id=str(alpha.id),
        user_id=owner.id,
        project_id=alpha.id,
        change_metadata=sensitive_payload,
    )

    # Verify secrets were sanitized
    stored_meta = event.change_metadata
    assert stored_meta["password"] == "[REDACTED]"
    assert stored_meta["new_password"] == "[REDACTED]"
    assert stored_meta["access_token"] == "[REDACTED]"
    assert stored_meta["api_key"] == "[REDACTED]"
    assert stored_meta["safe_field"] == "public_description_update"

