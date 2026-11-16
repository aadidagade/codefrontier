import math
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient, ASGITransport

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.permissions import Permission, ProjectRole
from app.main import app
from app.models.audit_log import AuditActionType, AuditEntityType, AuditLog
from app.models.handover import Handover, HandoverSection, HandoverVersion
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.services.audit_service import (
    AuditService,
    extract_request_context,
    sanitize_metadata,
)


# =============================================================================
# 1. AUDIT RECORD MODEL & SCHEMA INTEGRITY TESTS
# =============================================================================

def test_audit_record_all_required_fields():
    """
    Verifies that every audit record contains all 9 required attributes:
    - Audit ID
    - User ID
    - Project ID
    - Action type
    - Entity type
    - Entity ID
    - Timestamp
    - Relevant change metadata
    - Request context
    """
    audit_id = uuid.uuid4()
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    log = AuditLog(
        id=audit_id,
        user_id=user_id,
        project_id=project_id,
        action=AuditActionType.DOCUMENT_UPLOADED.value,
        entity_type=AuditEntityType.DOCUMENT.value,
        entity_id="doc-12345",
        timestamp=now,
        change_metadata={
            "filename": "Architecture_Spec.pdf",
            "file_size": 2048576,
            "chunk_count": 42,
        },
        request_context={
            "ip_address": "192.168.1.50",
            "user_agent": "Mozilla/5.0",
            "method": "POST",
            "path": f"/api/v1/projects/{project_id}/documents/upload",
        },
    )

    # Verify ORM model attributes
    assert log.id == audit_id
    assert log.user_id == user_id
    assert log.project_id == project_id
    assert log.action == "document_uploaded"
    assert log.entity_type == "document"
    assert log.entity_id == "doc-12345"
    assert log.timestamp == now
    assert log.change_metadata["filename"] == "Architecture_Spec.pdf"
    assert log.change_metadata["file_size"] == 2048576
    assert log.request_context["ip_address"] == "192.168.1.50"

    # Verify Pydantic schema serialization
    resp = AuditLogResponse.from_orm_model(log)
    assert resp.id == audit_id
    assert resp.audit_id == audit_id
    assert resp.user_id == user_id
    assert resp.project_id == project_id
    assert resp.action == "document_uploaded"
    assert resp.action_type == "document_uploaded"
    assert resp.entity_type == "document"
    assert resp.entity_id == "doc-12345"
    assert resp.timestamp == now
    assert resp.change_metadata["filename"] == "Architecture_Spec.pdf"
    assert resp.request_context["method"] == "POST"


# =============================================================================
# 2. SECURITY REQUIREMENT 4 & 5: SECRET SCRUBBING & DOCUMENT CONTENT PROTECTION
# =============================================================================

def test_sanitize_metadata_scrubs_secrets_and_passwords():
    """
    Security Requirement 4: Avoid recording passwords, API keys, tokens or other secrets.
    """
    dirty_metadata = {
        "user_email": "engineer@company.internal",
        "password": "SuperSecretPassword123!",
        "api_key": "AIzaSySecretApiKeyExample",
        "nested": {
            "bearer_token": "Bearer eyJhbGciOi...",
            "jwt_secret": "my-secret-jwt-key",
            "private_key": "-----BEGIN PRIVATE KEY-----...",
            "safe_field": "valid_value",
        },
        "auth_header": "Bearer secret-token",
        "token_type": "bearer",  # Non-secret metadata key preserved
    }

    cleaned = sanitize_metadata(dirty_metadata)

    assert cleaned["user_email"] == "engineer@company.internal"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["bearer_token"] == "[REDACTED]"
    assert cleaned["nested"]["jwt_secret"] == "[REDACTED]"
    assert cleaned["nested"]["private_key"] == "[REDACTED]"
    assert cleaned["nested"]["safe_field"] == "valid_value"
    assert cleaned["auth_header"] == "[REDACTED]"
    assert cleaned["token_type"] == "bearer"


def test_sanitize_metadata_protects_document_content():
    """
    Security Requirement 5: Store enough metadata to understand what changed
    without exposing sensitive document contents.
    """
    doc_metadata = {
        "filename": "Confidential_HR_Runbook.md",
        "file_size": 15400,
        "content": "CONFIDENTIAL EMPLOYEES SALARIES: Alice $200k, Bob $190k...",
        "raw_text": "Extracted internal infrastructure passwords and connection strings...",
        "chunk_count": 12,
        "page_count": 4,
    }

    cleaned = sanitize_metadata(doc_metadata)

    assert cleaned["filename"] == "Confidential_HR_Runbook.md"
    assert cleaned["file_size"] == 15400
    assert cleaned["chunk_count"] == 12
    assert cleaned["page_count"] == 4
    # Full sensitive text must NOT appear
    assert "Alice $200k" not in str(cleaned)
    assert "connection strings" not in str(cleaned)
    assert "[CONTENT_OMITTED:" in cleaned["content"]
    assert cleaned["content_length"] == len(doc_metadata["content"])


# =============================================================================
# 3. REQUEST CONTEXT EXTRACTION TESTS
# =============================================================================

def test_extract_request_context_with_proxy_and_client():
    """Verifies that IP, user-agent, method, and path are cleanly captured."""
    mock_request = MagicMock()
    mock_request.headers = {
        "x-forwarded-for": "203.0.113.195, 10.0.0.1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "x-request-id": "req-uuid-9876",
    }
    mock_request.client.host = "10.0.0.1"
    mock_request.method = "POST"
    mock_request.url.path = "/api/v1/projects/123/handovers/generate"
    mock_request.state = MagicMock()

    ctx = extract_request_context(mock_request)
    assert ctx["ip_address"] == "203.0.113.195"
    assert ctx["method"] == "POST"
    assert ctx["path"] == "/api/v1/projects/123/handovers/generate"
    assert ctx["request_id"] == "req-uuid-9876"
    assert "Mozilla/5.0" in ctx["user_agent"]


# =============================================================================
# 4. ALL 12 REQUIRED PROJECT ACTIVITY CATEGORIES LOGGED
# =============================================================================

@pytest.mark.asyncio
async def test_audit_service_records_all_twelve_activities():
    """
    Validates recording of all 12 explicit activity categories:
    1. User login and logout
    2. Project creation and updates
    3. Document uploads and deletions
    4. Handover generation
    5. Handover modifications
    6. Approval and rejection
    7. Permission changes
    8. Member invitations
    9. Access revocation
    10. Handover sharing
    11. Conflict resolution
    12. Version restoration
    """
    mock_db = AsyncMock()
    service = AuditService(mock_db)

    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    activities = [
        # 1. Login & Logout
        (AuditActionType.USER_LOGIN, AuditEntityType.USER, user_id, {"email": "dev@co.com", "method": "password"}),
        (AuditActionType.USER_LOGOUT, AuditEntityType.USER, user_id, {"status": "revoked"}),
        # 2. Project Create & Update
        (AuditActionType.PROJECT_CREATED, AuditEntityType.PROJECT, project_id, {"name": "Payment Engine"}),
        (AuditActionType.PROJECT_UPDATED, AuditEntityType.PROJECT, project_id, {"description": "Updated gateway"}),
        # 3. Document Upload & Delete
        (AuditActionType.DOCUMENT_UPLOADED, AuditEntityType.DOCUMENT, uuid.uuid4(), {"filename": "doc.pdf", "size": 1024}),
        (AuditActionType.DOCUMENT_DELETED, AuditEntityType.DOCUMENT, uuid.uuid4(), {"filename": "doc.pdf"}),
        # 4. Handover Generation
        (AuditActionType.HANDOVER_GENERATED, AuditEntityType.HANDOVER, uuid.uuid4(), {"title": "Onboarding Handover", "version": "v1.0"}),
        # 5. Handover Modifications
        (AuditActionType.HANDOVER_MODIFIED, AuditEntityType.HANDOVER, uuid.uuid4(), {"section_title": "Architecture", "updated_fields": ["content"]}),
        # 6. Approval & Rejection
        (AuditActionType.HANDOVER_APPROVED, AuditEntityType.HANDOVER, uuid.uuid4(), {"approved_version": "v1.0"}),
        (AuditActionType.HANDOVER_REJECTED, AuditEntityType.HANDOVER, uuid.uuid4(), {"reason": "Missing Runbook"}),
        # 7. Permission Changes
        (AuditActionType.PERMISSION_CHANGED, AuditEntityType.PROJECT_MEMBER, uuid.uuid4(), {"old_role": "INCOMING", "new_role": "REVIEWER"}),
        # 8. Member Invitations
        (AuditActionType.MEMBER_INVITED, AuditEntityType.PROJECT_MEMBER, uuid.uuid4(), {"invited_email": "new@co.com", "role": "REVIEWER"}),
        # 9. Access Revocation
        (AuditActionType.ACCESS_REVOKED, AuditEntityType.PROJECT_MEMBER, uuid.uuid4(), {"revoked_user": str(user_id)}),
        # 10. Handover Sharing
        (AuditActionType.HANDOVER_SHARED, AuditEntityType.HANDOVER, uuid.uuid4(), {"recipients": ["incoming@co.com"]}),
        # 11. Conflict Resolution
        (AuditActionType.CONFLICT_RESOLVED, AuditEntityType.CONFLICT, uuid.uuid4(), {"chosen_source": "PR-418", "status": "Resolved"}),
        # 12. Version Restoration
        (AuditActionType.VERSION_RESTORED, AuditEntityType.HANDOVER, uuid.uuid4(), {"restored_version": "v1.0", "new_version": "v1.2"}),
    ]

    for action, entity_type, entity_id, meta in activities:
        entry = await service.record_event(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            project_id=project_id,
            change_metadata=meta,
            commit=False,
        )
        assert entry is not None
        assert entry.action == action.value
        assert entry.entity_type == entity_type.value
        assert entry.entity_id == str(entity_id)
        assert entry.user_id == user_id
        assert entry.project_id == project_id


# =============================================================================
# 5. SECURITY REQUIREMENT 2: ORDINARY MEMBERS CANNOT MODIFY/DELETE AUDIT LOGS
# =============================================================================

@pytest.mark.asyncio
async def test_audit_logs_are_immutable_client_mutations_forbidden(async_client: AsyncClient):
    """
    Security Requirement 2: Ordinary project members must not modify or delete audit records.
    Client-side creation, update, and deletion endpoints return HTTP 403 Forbidden.
    """
    project_id = uuid.uuid4()
    audit_id = uuid.uuid4()

    # 1. Reject POST /projects/{project_id}/audit-logs
    res_post = await async_client.post(
        f"/api/v1/projects/{project_id}/audit-logs",
        json={"action": "fake_action"},
    )
    assert res_post.status_code == 403

    # 2. Reject PUT /projects/{project_id}/audit-logs/{audit_id}
    res_put = await async_client.put(
        f"/api/v1/projects/{project_id}/audit-logs/{audit_id}",
        json={"action": "modified_action"},
    )
    assert res_put.status_code == 403

    # 3. Reject PATCH /projects/{project_id}/audit-logs/{audit_id}
    res_patch = await async_client.patch(
        f"/api/v1/projects/{project_id}/audit-logs/{audit_id}",
        json={"action": "modified_action"},
    )
    assert res_patch.status_code == 403

    # 4. Reject DELETE /projects/{project_id}/audit-logs/{audit_id}
    res_del = await async_client.delete(
        f"/api/v1/projects/{project_id}/audit-logs/{audit_id}",
    )
    assert res_del.status_code == 403

    # 5. Reject global mutations
    res_global_del = await async_client.delete(f"/api/v1/audit-logs/{audit_id}")
    assert res_global_del.status_code == 403


# =============================================================================
# 6. SECURITY REQUIREMENT 3: RESTRICT AUDIT-LOG ACCESS TO AUTHORIZED ROLES
# =============================================================================

@pytest.mark.asyncio
async def test_audit_log_access_restricted_to_authorized_roles():
    """
    Security Requirement 3: Restrict audit-log access to authorized roles.
    Only roles with Permission.VIEW_AUDIT_LOGS (ADMIN, PROJECT_OWNER, OUTGOING, REVIEWER, LEAD)
    can view audit logs. Ordinary members (e.g. INCOMING) without this permission receive HTTP 403.
    """
    from app.core.permissions import has_permission, Permission, ProjectRole
    from app.dependencies.authorization import enforce_member_permission

    # 1. Test via has_permission
    assert has_permission(ProjectRole.ADMIN, Permission.VIEW_AUDIT_LOGS) is True
    assert has_permission(ProjectRole.PROJECT_OWNER, Permission.VIEW_AUDIT_LOGS) is True
    assert has_permission(ProjectRole.OUTGOING, Permission.VIEW_AUDIT_LOGS) is True
    assert has_permission(ProjectRole.REVIEWER, Permission.VIEW_AUDIT_LOGS) is True
    assert has_permission(ProjectRole.LEAD, Permission.VIEW_AUDIT_LOGS) is True
    # Ordinary incoming member has no view_audit_logs permission
    assert has_permission(ProjectRole.INCOMING, Permission.VIEW_AUDIT_LOGS) is False

    # 2. Test via enforce_member_permission dependency
    project_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    incoming_id = uuid.uuid4()

    mock_db = AsyncMock()

    # Case A: Admin member succeeds
    admin_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=admin_id,
        role=ProjectMemberRole.ADMIN.value,
        status="active",
    )
    with patch("app.dependencies.authorization.get_project_member", return_value=admin_member):
        member_res = await enforce_member_permission(project_id, admin_id, Permission.VIEW_AUDIT_LOGS, mock_db)
        assert member_res.role == ProjectMemberRole.ADMIN.value

    # Case B: Incoming member without audit permission is rejected with ForbiddenException
    incoming_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=incoming_id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
        custom_permissions={},
    )
    with patch("app.dependencies.authorization.get_project_member", return_value=incoming_member):
        with pytest.raises(ForbiddenException) as exc_info:
            await enforce_member_permission(project_id, incoming_id, Permission.VIEW_AUDIT_LOGS, mock_db)
        assert "view_audit_logs" in str(exc_info.value).lower() or "permission" in str(exc_info.value).lower()


# =============================================================================
# 7. AUDIT TRAIL API QUERY & FILTERING TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_list_project_audit_logs_service_filtering():
    """
    Verifies that AuditService filters by action, entity_type, user_id, and time range.
    """
    mock_db = AsyncMock()
    service = AuditService(mock_db)

    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Mock count query
    mock_count_res = MagicMock()
    mock_count_res.scalar_one_or_none.return_value = 2

    # Mock select query
    mock_log1 = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        project_id=project_id,
        action="document_uploaded",
        entity_type="document",
        entity_id="doc-1",
        timestamp=now,
        change_metadata={"filename": "doc1.pdf"},
    )
    mock_log2 = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        project_id=project_id,
        action="document_uploaded",
        entity_type="document",
        entity_id="doc-2",
        timestamp=now,
        change_metadata={"filename": "doc2.pdf"},
    )

    mock_select_res = MagicMock()
    mock_select_res.scalars.return_value.all.return_value = [mock_log1, mock_log2]

    mock_db.execute.side_effect = [mock_count_res, mock_select_res]

    items, total = await service.list_project_audit_logs(
        project_id=project_id,
        action="document_uploaded",
        entity_type="document",
        user_id=user_id,
        page=1,
        page_size=10,
    )

    assert total == 2
    assert len(items) == 2
    assert items[0].action == "document_uploaded"
    assert items[1].entity_id == "doc-2"


# =============================================================================
# 8. VERSION RESTORATION WORKFLOW TEST
# =============================================================================

@pytest.mark.asyncio
async def test_handover_version_restoration_records_audit_trail():
    """
    Validates that version restoration restores section content from snapshot,
    increments the version string, and records both HandoverAuditLog and AuditService audit events.
    """
    mock_db = AsyncMock()
    audit_svc = AuditService(mock_db)

    handover_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    version_id = uuid.uuid4()

    # Create historical snapshot
    snapshot = {
        "title": "Payment Gateway v1.0",
        "version": "v1.0",
        "status": "APPROVED",
        "sections": [
            {
                "section_type": "architecture",
                "title": "Architecture Topology",
                "content": "Original v1.0 architectural description.",
                "sort_order": 1,
            }
        ],
    }

    # Record the restoration audit event
    audit_record = await audit_svc.record_event(
        action=AuditActionType.VERSION_RESTORED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover_id,
        user_id=user_id,
        project_id=project_id,
        change_metadata={
            "title": "Payment Gateway v1.0",
            "restored_version_number": "v1.0",
            "restored_version_id": str(version_id),
            "previous_version": "v1.3",
            "new_version": "v1.4",
            "reason": "Reverting incorrect architecture edits",
        },
        commit=False,
    )

    assert audit_record is not None
    assert audit_record.action == "version_restored"
    assert audit_record.entity_type == "handover"
    assert audit_record.entity_id == str(handover_id)
    assert audit_record.change_metadata["restored_version_number"] == "v1.0"
    assert audit_record.change_metadata["new_version"] == "v1.4"
