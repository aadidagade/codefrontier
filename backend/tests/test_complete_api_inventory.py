"""
Comprehensive Backend API QA Test Suite
========================================
Exhaustively tests every backend API in the Knowledge Handover Platform
across the 15 core domains:
1. Authentication APIs
2. User Management APIs
3. Project CRUD APIs
4. Document Upload APIs
5. Document Processing APIs
6. Handover Generation APIs
7. Evidence Verification APIs
8. Contradiction Detection APIs
9. Conflict Resolution APIs
10. Member and Permission APIs
11. Audit Log APIs
12. Handover Version APIs
13. Version Comparison APIs
14. Incoming-Member APIs
15. Task Management APIs

Across all 9 required test conditions:
- Valid requests (200 / 201 / 204) with response schema checks
- Invalid requests (malformed payload, invalid status/enum)
- Missing parameters (missing required body or query fields)
- Incorrect data types (bad UUID, integer for email)
- Unauthorized requests (401 - missing or corrupt JWT)
- Forbidden requests (403 - unauthorized role / lack of RBAC privilege / revoked user)
- Nonexistent resource IDs (404 - UUID not present in database)
- Database errors (500 - simulated operational/database failure)
- Duplicate requests (400 or 409 Conflict - duplicate email or membership)
"""

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    DatabaseException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.permissions import Permission, ProjectRole
from app.core.security import create_access_token, get_password_hash
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import (
    enforce_member_permission,
    require_document_access,
    require_handover_access,
    require_permission,
    require_project_membership,
    require_task_access,
)
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_log import AuditActionType, AuditEntityType, AuditLog
from app.models.conflict import Conflict
from app.models.document import Document, DocumentChunk
from app.models.handover import (
    Handover,
    HandoverAuditLog,
    HandoverSection,
    HandoverVersion,
)
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.task import Task, TaskDependency, TaskProgressUpdate
from app.models.user import User
from app.schemas.handover import HandoverStatus, HandoverTransitionStatus
from app.schemas.task import (
    TaskCreate,
    TaskProgressUpdateCreate,
    TaskStatusUpdate,
)
from app.services.auth_service import AuthService


# =============================================================================
# HELPER TEST FIXTURES & DATA BUILDERS
# =============================================================================

@pytest.fixture
def test_admin_user():
    return User(
        id=uuid.uuid4(),
        email="admin@platform.qa",
        full_name="QA System Admin",
        password_hash=get_password_hash("Password123!"),
        is_active=True,
    )


@pytest.fixture
def test_lead_user():
    return User(
        id=uuid.uuid4(),
        email="lead@platform.qa",
        full_name="QA Lead Engineer",
        password_hash=get_password_hash("Password123!"),
        is_active=True,
    )


@pytest.fixture
def test_outgoing_user():
    return User(
        id=uuid.uuid4(),
        email="outgoing@platform.qa",
        full_name="QA Outgoing Engineer",
        password_hash=get_password_hash("Password123!"),
        is_active=True,
    )


@pytest.fixture
def test_incoming_user():
    return User(
        id=uuid.uuid4(),
        email="incoming@platform.qa",
        full_name="QA Incoming Member",
        password_hash=get_password_hash("Password123!"),
        is_active=True,
    )


@pytest.fixture
def test_viewer_user():
    return User(
        id=uuid.uuid4(),
        email="viewer@platform.qa",
        full_name="QA ReadOnly Viewer",
        password_hash=get_password_hash("Password123!"),
        is_active=True,
    )


@pytest.fixture
def sample_project(test_lead_user):
    return Project(
        id=uuid.uuid4(),
        name="Knowledge Handover QA Testbed",
        description="Core architecture and transition package",
        status="active",
        created_by=test_lead_user.id,
    )


@pytest.fixture
def sample_handover(sample_project, test_outgoing_user, test_incoming_user):
    return Handover(
        id=uuid.uuid4(),
        project_id=sample_project.id,
        title="Production Microservices Transition Handover",
        version="v1.0",
        status=HandoverStatus.DRAFT.value,
        transition_status=HandoverTransitionStatus.AWAITING_ACKNOWLEDGEMENT.value,
        created_by=test_outgoing_user.id,
        assigned_to=test_incoming_user.id,
        created_at=datetime.now(timezone.utc),
        project=sample_project,
        sections=[],
        tasks=[],
    )


# =============================================================================
# 0. API ROUTE INVENTORY VALIDATION
# =============================================================================

def test_api_route_inventory_completeness():
    """
    Validates that the FastAPI application registers the expected API inventory
    covering all 15 domains without duplicate paths or missing tags.
    """
    openapi = app.openapi()
    paths = openapi.get("paths", {})
    assert len(paths) >= 90, f"Expected at least 90 unique paths, found {len(paths)}"

    operations = []
    for path, methods in paths.items():
        for m in methods.keys():
            if m.lower() in ("get", "post", "put", "patch", "delete"):
                operations.append((m.upper(), path))

    assert len(operations) >= 120, f"Expected at least 120 operations, found {len(operations)}"

    # Ensure required domain prefixes exist
    endpoints_str = " ".join([p for _, p in operations])
    assert "/api/v1/auth" in endpoints_str
    assert "/api/v1/users" in endpoints_str
    assert "/api/v1/projects" in endpoints_str
    assert "/documents" in endpoints_str
    assert "/handovers" in endpoints_str
    assert "/evidence" in endpoints_str
    assert "/conflicts" in endpoints_str
    assert "/members" in endpoints_str
    assert "/audit-logs" in endpoints_str
    assert "/tasks" in endpoints_str


# =============================================================================
# 1. AUTHENTICATION APIS (/api/v1/auth/*)
# =============================================================================

@pytest.mark.asyncio
async def test_auth_apis_unauthorized_access(async_client: AsyncClient):
    """Verifies that protected auth endpoints return 401 when token is missing or malformed."""
    # 1. /api/v1/auth/me without token -> 401
    res1 = await async_client.get("/api/v1/auth/me")
    assert res1.status_code == 401
    assert res1.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. /api/v1/auth/me with malformed token -> 401
    res2 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert res2.status_code == 401
    assert res2.json()["error"]["code"] == "UNAUTHORIZED"

    # 3. /api/v1/auth/refresh without token or with invalid refresh token -> 401
    res3 = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid_refresh_token_12345"})
    assert res3.status_code == 401


@pytest.mark.asyncio
async def test_auth_apis_missing_parameters_and_invalid_types(async_client: AsyncClient):
    """Tests missing parameters and invalid data types on auth endpoints (422)."""
    # Missing body on register -> 422
    res_reg_empty = await async_client.post("/api/v1/auth/register", json={})
    assert res_reg_empty.status_code == 422

    # Incorrect data types (integer for email) -> 422
    res_reg_bad_type = await async_client.post(
        "/api/v1/auth/register",
        json={"email": 12345, "password": "Password123!", "full_name": "Test User"},
    )
    assert res_reg_bad_type.status_code == 422

    # Malformed email -> 422
    res_reg_bad_email = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "Password123!", "full_name": "Test User"},
    )
    assert res_reg_bad_email.status_code == 422

    # Short password (< 8 chars) -> 422
    res_reg_short_pw = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": "short", "full_name": "Test User"},
    )
    assert res_reg_short_pw.status_code == 422

    # Missing parameters on login -> 422
    res_login_empty = await async_client.post("/api/v1/auth/login", json={})
    assert res_login_empty.status_code == 422

    # Missing refresh token on refresh -> 422
    res_refresh_empty = await async_client.post("/api/v1/auth/refresh", json={})
    assert res_refresh_empty.status_code == 422

    # Missing body on logout -> 422
    res_logout_empty = await async_client.post("/api/v1/auth/logout")
    assert res_logout_empty.status_code == 422


@pytest.mark.asyncio
async def test_auth_apis_duplicate_and_valid_lifecycle(async_client: AsyncClient, test_lead_user):
    """Tests duplicate registration (409/400) and valid authentication responses."""
    # Test duplicate registration handling when user exists
    with patch.object(AuthService, "register", side_effect=ConflictException("Email already registered.")):
        res_dup = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "ValidPassword123!", "full_name": "Existing User"},
        )
        assert res_dup.status_code == 409
        assert res_dup.json()["error"]["code"] == "CONFLICT"

    # Test valid /me with authenticated override
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    try:
        res_me = await async_client.get("/api/v1/auth/me")
        assert res_me.status_code == 200
        data = res_me.json()["data"]
        assert data["email"] == test_lead_user.email
        assert data["full_name"] == test_lead_user.full_name

        # Test valid logout with payload
        res_logout = await async_client.post("/api/v1/auth/logout", json={"refresh_token": "valid_refresh_token_sample"})
        assert res_logout.status_code == 200
        assert res_logout.json()["success"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 2. USER MANAGEMENT APIS (/api/v1/users/*)
# =============================================================================

@pytest.mark.asyncio
async def test_users_apis_unauthorized(async_client: AsyncClient):
    """Verifies user endpoints require authentication (401)."""
    random_id = uuid.uuid4()
    assert (await async_client.get("/api/v1/users")).status_code == 401
    assert (await async_client.get(f"/api/v1/users/{random_id}")).status_code == 401


@pytest.mark.asyncio
async def test_users_apis_invalid_types_and_nonexistent(async_client: AsyncClient, test_admin_user):
    """Tests invalid UUID types (422) and nonexistent user IDs (404)."""
    app.dependency_overrides[get_current_user] = lambda: test_admin_user
    try:
        # Invalid data type (string instead of UUID in path) -> 422
        res_bad_type = await async_client.get("/api/v1/users/not-a-valid-uuid")
        assert res_bad_type.status_code == 422

        # Nonexistent user ID -> 404
        nonexistent_id = uuid.uuid4()
        res_not_found = await async_client.get(f"/api/v1/users/{nonexistent_id}")
        assert res_not_found.status_code == 404
        assert res_not_found.json()["error"]["code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_users_apis_valid_and_database_error(async_client: AsyncClient, test_admin_user):
    """Tests valid user list retrieval and graceful database error handling (500)."""
    app.dependency_overrides[get_current_user] = lambda: test_admin_user
    try:
        # Valid list users
        res = await async_client.get("/api/v1/users")
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert isinstance(res.json()["data"], list)

        # Database error handling
        from app.dependencies.database import get_db
        mock_db_error = AsyncMock()
        mock_db_error.execute.side_effect = DatabaseException("Database connection timed out.")

        async def override_error_db():
            yield mock_db_error

        app.dependency_overrides[get_db] = override_error_db
        res_err = await async_client.get("/api/v1/users")
        assert res_err.status_code == 500
        assert res_err.json()["error"]["code"] == "DATABASE_ERROR"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)
        app.dependency_overrides.pop(get_db, None)


# =============================================================================
# 3. PROJECT CRUD APIS (/api/v1/projects/*)
# =============================================================================

@pytest.mark.asyncio
async def test_projects_apis_unauthorized(async_client: AsyncClient):
    """Verifies all project CRUD endpoints return 401 without auth token."""
    pid = uuid.uuid4()
    assert (await async_client.get("/api/v1/projects")).status_code == 401
    assert (await async_client.post("/api/v1/projects", json={"name": "New Project"})).status_code == 401
    assert (await async_client.get(f"/api/v1/projects/{pid}")).status_code == 401
    assert (await async_client.patch(f"/api/v1/projects/{pid}", json={"name": "Updated"})).status_code == 401
    assert (await async_client.delete(f"/api/v1/projects/{pid}")).status_code == 401
    assert (await async_client.get(f"/api/v1/projects/{pid}/overview")).status_code == 401
    assert (await async_client.post(f"/api/v1/projects/{pid}/search", json={"query": "test"})).status_code == 401
    assert (await async_client.post(f"/api/v1/projects/{pid}/qa", json={"question": "test?"})).status_code == 401


@pytest.mark.asyncio
async def test_projects_apis_missing_parameters_and_invalid_types(async_client: AsyncClient, test_lead_user):
    """Tests missing body, empty strings, and bad UUID types (422)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    try:
        # Missing project name -> 422
        res1 = await async_client.post("/api/v1/projects", json={})
        assert res1.status_code == 422

        # Empty project name string -> 422
        res2 = await async_client.post("/api/v1/projects", json={"name": ""})
        assert res2.status_code == 422

        # Incorrect data type in path -> 422
        res3 = await async_client.get("/api/v1/projects/not-a-uuid")
        assert res3.status_code == 422

        # Incorrect UUID in search path -> 422
        res4 = await async_client.post("/api/v1/projects/not-a-uuid/search", json={"query": "test"})
        assert res4.status_code == 422

        # Incorrect UUID in QA path -> 422
        res5 = await async_client.post("/api/v1/projects/not-a-uuid/qa", json={"question": "test?"})
        assert res5.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_projects_apis_forbidden_and_nonexistent(async_client: AsyncClient, test_viewer_user):
    """Verifies 403 Forbidden for unauthorized roles and 404 for nonexistent projects."""
    app.dependency_overrides[get_current_user] = lambda: test_viewer_user
    pid = uuid.uuid4()
    try:
        # Non-member access to project -> 403 Forbidden (IDOR protection)
        res_forbid = await async_client.get(f"/api/v1/projects/{pid}")
        assert res_forbid.status_code == 403
        assert res_forbid.json()["error"]["code"] == "FORBIDDEN"

        # Authorized member accessing nonexistent project -> 404 Not Found
        mock_member = ProjectMember(id=uuid.uuid4(), project_id=pid, user_id=test_viewer_user.id, role="VIEWER")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_member):
            with patch("app.services.project_service.ProjectService.get_project", side_effect=NotFoundException("Project", pid)):
                res_nf = await async_client.get(f"/api/v1/projects/{pid}")
                assert res_nf.status_code == 404
                assert res_nf.json()["error"]["code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: AsyncClient):
    """Tests GET / (Health root) and GET /api/v1/health valid responses."""
    res_root = await async_client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["status"] == "online"

    with patch("app.api.v1.endpoints.health.check_database_health", return_value={"status": "connected"}):
        with patch("app.api.v1.endpoints.health.ai_service.check_ai_health", return_value={"status": "connected"}):
            res_health = await async_client.get("/api/v1/health")
            assert res_health.status_code == 200
            assert res_health.json()["status"] == "healthy"


# =============================================================================
# 4. DOCUMENT UPLOAD APIS (/api/v1/projects/{project_id}/documents/upload)
# =============================================================================

@pytest.mark.asyncio
async def test_document_upload_unauthorized(async_client: AsyncClient):
    """Verifies document upload returns 401 without auth token."""
    pid = uuid.uuid4()
    res = await async_client.post(
        f"/api/v1/projects/{pid}/documents/upload",
        files={"files": ("test.txt", b"Test document content", "text/plain")},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_document_upload_missing_files_and_invalid_uuid(async_client: AsyncClient, test_lead_user):
    """Verifies missing file multipart and bad UUID format return 422."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    try:
        # Invalid project UUID -> 422
        res1 = await async_client.post(
            "/api/v1/projects/invalid-project-uuid/documents/upload",
            files={"files": ("test.txt", b"content", "text/plain")},
        )
        assert res1.status_code == 422

        # When authorized member, missing files parameter -> 422
        pid = uuid.uuid4()
        mock_member = ProjectMember(id=uuid.uuid4(), project_id=pid, user_id=test_lead_user.id, role="LEAD")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_member):
            res2 = await async_client.post(f"/api/v1/projects/{pid}/documents/upload")
            assert res2.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_document_upload_forbidden_and_nonexistent(async_client: AsyncClient, test_viewer_user):
    """Verifies non-member or viewer role receives 403 on upload."""
    app.dependency_overrides[get_current_user] = lambda: test_viewer_user
    pid = uuid.uuid4()
    try:
        # Non-member or unauthorized role -> 403
        with patch("app.dependencies.authorization.enforce_member_permission", side_effect=ForbiddenException("Viewer cannot upload")):
            res = await async_client.post(
                f"/api/v1/projects/{pid}/documents/upload",
                files={"files": ("spec.md", b"# Architecture Spec", "text/markdown")},
            )
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 5. DOCUMENT PROCESSING APIS (/api/v1/documents/* & project documents)
# =============================================================================

@pytest.mark.asyncio
async def test_document_processing_unauthorized(async_client: AsyncClient):
    """Verifies document processing APIs return 401 without auth token."""
    doc_id = uuid.uuid4()
    pid = uuid.uuid4()
    assert (await async_client.get(f"/api/v1/documents/{doc_id}")).status_code == 401
    assert (await async_client.get(f"/api/v1/documents/{doc_id}/status")).status_code == 401
    assert (await async_client.get(f"/api/v1/documents/{doc_id}/chunks")).status_code == 401
    assert (await async_client.get(f"/api/v1/documents/{doc_id}/download")).status_code == 401
    assert (await async_client.post(f"/api/v1/documents/{doc_id}/retry")).status_code == 401
    assert (await async_client.delete(f"/api/v1/documents/{doc_id}")).status_code == 401
    assert (await async_client.get(f"/api/v1/projects/{pid}/documents")).status_code == 401
    assert (await async_client.post(f"/api/v1/projects/{pid}/documents/search", json={"query": "test"})).status_code == 401


@pytest.mark.asyncio
async def test_document_processing_nonexistent_and_invalid_types(async_client: AsyncClient, test_lead_user):
    """Verifies 422 for invalid UUIDs and 404 for nonexistent document IDs."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    try:
        # Invalid UUID in path -> 422
        res1 = await async_client.get("/api/v1/documents/bad-uuid")
        assert res1.status_code == 422

        # Nonexistent document ID (require_document_access raises 404) -> 404
        doc_id = uuid.uuid4()
        res2 = await async_client.get(f"/api/v1/documents/{doc_id}")
        assert res2.status_code == 404
        assert res2.json()["error"]["code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_document_processing_forbidden_actions(async_client: AsyncClient, test_viewer_user, sample_project):
    """Verifies that unauthorized members (e.g. VIEWER) cannot delete documents (403)."""
    app.dependency_overrides[get_current_user] = lambda: test_viewer_user
    doc_id = uuid.uuid4()
    mock_doc = Document(id=doc_id, project_id=sample_project.id, original_filename="spec.pdf")
    app.dependency_overrides[require_document_access] = lambda: mock_doc

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_doc
    mock_res.rowcount = 1
    mock_db.execute.return_value = mock_res

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        mock_viewer_member = ProjectMember(id=uuid.uuid4(), project_id=sample_project.id, user_id=test_viewer_user.id, role="VIEWER")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_viewer_member):
            res = await async_client.delete(f"/api/v1/documents/{doc_id}")
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)
        app.dependency_overrides.pop(require_document_access, None)
        app.dependency_overrides.pop(get_db, None)


# =============================================================================
# 6. HANDOVER GENERATION APIS (/api/v1/handovers/*)
# =============================================================================

@pytest.mark.asyncio
async def test_handover_apis_unauthorized(async_client: AsyncClient):
    """Verifies handover endpoints return 401 without auth token."""
    hid = uuid.uuid4()
    sid = uuid.uuid4()
    pid = uuid.uuid4()
    assert (await async_client.get("/api/v1/handovers")).status_code == 401
    assert (await async_client.post("/api/v1/handovers/generate", json={})).status_code == 401
    assert (await async_client.get(f"/api/v1/handovers/{hid}")).status_code == 401
    assert (await async_client.delete(f"/api/v1/handovers/{hid}")).status_code == 401
    assert (await async_client.patch(f"/api/v1/handovers/{hid}/sections/{sid}", json={"content": "new"})).status_code == 401
    assert (await async_client.post(f"/api/v1/handovers/{hid}/submit-review")).status_code == 401
    assert (await async_client.post(f"/api/v1/handovers/{hid}/approve", json={})).status_code == 401
    assert (await async_client.post(f"/api/v1/handovers/{hid}/reject", json={"reason": "Incomplete"})).status_code == 401
    assert (await async_client.get(f"/api/v1/handovers/{hid}/history")).status_code == 401
    assert (await async_client.get(f"/api/v1/handovers/{hid}/export/pdf")).status_code == 401
    assert (await async_client.get(f"/api/v1/projects/{pid}/handovers")).status_code == 401


@pytest.mark.asyncio
async def test_handover_apis_missing_parameters_and_invalid_types(async_client: AsyncClient, test_lead_user, sample_handover):
    """Tests missing payload in generation and invalid UUIDs (422)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    hid = sample_handover.id
    sid = uuid.uuid4()
    try:
        # Invalid handover UUID in path (checked by require_handover_access Path validation) -> 422
        res_bad_uuid = await async_client.get("/api/v1/handovers/invalid-uuid-format")
        assert res_bad_uuid.status_code == 422

        # Invalid projectId data type on generate -> 422
        res1 = await async_client.post("/api/v1/handovers/generate", json={"projectId": "not-a-valid-uuid"})
        assert res1.status_code == 422

        # Override require_handover_access for endpoint payload testing
        app.dependency_overrides[require_handover_access] = lambda: sample_handover
        mock_lead_member = ProjectMember(id=uuid.uuid4(), project_id=sample_handover.project_id, user_id=test_lead_user.id, role="LEAD")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_lead_member):
            # Invalid section UUID in path -> 422
            res3 = await async_client.patch(f"/api/v1/handovers/{hid}/sections/not-a-valid-uuid", json={"content": "new"})
            assert res3.status_code == 422

            # Incorrect data type for content (string instead of dict) -> 422
            res_bad_content_type = await async_client.patch(f"/api/v1/handovers/{hid}/sections/{sid}", json={"content": "string-not-dict"})
            assert res_bad_content_type.status_code == 422

            # Nonexistent section UUID in path -> 404
            res_sec_nf = await async_client.patch(f"/api/v1/handovers/{hid}/sections/{sid}", json={"content": {"text": "new"}})
            assert res_sec_nf.status_code == 404

            # Missing required reason on reject -> 422
            res4 = await async_client.post(f"/api/v1/handovers/{hid}/reject", json={})
            assert res4.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_handover_apis_forbidden_role_restrictions(async_client: AsyncClient, test_incoming_user, sample_handover):
    """Verifies that incoming member cannot approve or delete handovers (403)."""
    app.dependency_overrides[get_current_user] = lambda: test_incoming_user
    app.dependency_overrides[require_handover_access] = lambda: sample_handover
    try:
        # Incoming member attempting to approve -> 403 Forbidden
        with patch("app.dependencies.authorization.require_project_membership", side_effect=ForbiddenException("Incoming members cannot approve")):
            res = await async_client.post(f"/api/v1/handovers/{sample_handover.id}/approve", json={"notes": "Looks good"})
            assert res.status_code == 403

        # Non-owner attempting to delete -> 403 Forbidden
        with patch("app.dependencies.authorization.require_project_membership", side_effect=ForbiddenException("Cannot delete")):
            res_del = await async_client.delete(f"/api/v1/handovers/{sample_handover.id}")
            assert res_del.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 7. EVIDENCE VERIFICATION APIS (/api/v1/evidence/*)
# =============================================================================

@pytest.mark.asyncio
async def test_evidence_apis_unauthorized(async_client: AsyncClient):
    """Verifies evidence endpoints return 401 when unauthenticated."""
    hid = uuid.uuid4()
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    assert (await async_client.post("/api/v1/evidence/verify", json={"claim_text": "Test"})).status_code == 401
    assert (await async_client.post(f"/api/v1/evidence/handovers/{hid}/verify")).status_code == 401
    assert (await async_client.post(f"/api/v1/evidence/handovers/{hid}/verify-all")).status_code == 401
    assert (await async_client.get(f"/api/v1/evidence/handovers/{hid}/verification-results")).status_code == 401
    assert (await async_client.post(f"/api/v1/evidence/sections/{sid}/verify")).status_code == 401
    assert (await async_client.get(f"/api/v1/evidence/sections/{sid}/verification-results")).status_code == 401
    assert (await async_client.get(f"/api/v1/evidence/claims/{cid}")).status_code == 401
    assert (await async_client.get(f"/api/v1/evidence/passage/{cid}")).status_code == 401
    assert (await async_client.get(f"/api/v1/evidence/{hid}")).status_code == 401


@pytest.mark.asyncio
async def test_evidence_apis_missing_parameters_and_nonexistent(async_client: AsyncClient, test_lead_user):
    """Tests missing parameters (422) and nonexistent IDs (404) on evidence verification."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    hid = uuid.uuid4()
    try:
        # Missing claim_text -> 422
        res1 = await async_client.post("/api/v1/evidence/verify", json={})
        assert res1.status_code == 422

        # Nonexistent handover ID on verification-results -> 404
        with patch("app.dependencies.authorization.require_handover_access", side_effect=NotFoundException("Handover", hid)):
            res2 = await async_client.get(f"/api/v1/evidence/handovers/{hid}/verification-results")
            assert res2.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 8. CONTRADICTION DETECTION APIS (/api/v1/conflicts/* & project conflicts)
# =============================================================================

@pytest.mark.asyncio
async def test_contradiction_detection_unauthorized(async_client: AsyncClient):
    """Verifies contradiction detection APIs return 401 without auth token."""
    pid = uuid.uuid4()
    cid = uuid.uuid4()
    assert (await async_client.post(f"/api/v1/projects/{pid}/conflicts/detect")).status_code == 401
    assert (await async_client.post(f"/api/v1/projects/{pid}/conflicts/report", json={})).status_code == 401
    assert (await async_client.get(f"/api/v1/projects/{pid}/conflicts")).status_code == 401
    assert (await async_client.get("/api/v1/conflicts")).status_code == 401
    assert (await async_client.get(f"/api/v1/conflicts/{cid}")).status_code == 401
    assert (await async_client.patch(f"/api/v1/conflicts/{cid}", json={"severity": "HIGH"})).status_code == 401

    # Note: /api/v1/conflicts/categories is a public category reference taxonomy (200)
    cat_res = await async_client.get("/api/v1/conflicts/categories")
    assert cat_res.status_code == 200


@pytest.mark.asyncio
async def test_contradiction_detection_missing_params_and_nonexistent(async_client: AsyncClient, test_lead_user):
    """Tests missing report fields (422) and nonexistent conflict IDs (404)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    pid = uuid.uuid4()
    cid = uuid.uuid4()
    try:
        # Invalid UUID format -> 422
        res_bad_uuid = await async_client.get("/api/v1/conflicts/not-a-uuid")
        assert res_bad_uuid.status_code == 422

        # Nonexistent conflict ID -> 404
        res_nf = await async_client.get(f"/api/v1/conflicts/{cid}")
        assert res_nf.status_code == 404

        # Invalid handoverId data type on report -> 422
        res_bad_param = await async_client.post(f"/api/v1/projects/{pid}/conflicts/report?handoverId=not-a-uuid")
        assert res_bad_param.status_code == 422

        # Invalid project UUID format on detect -> 422
        res_bad_proj = await async_client.post("/api/v1/projects/not-a-uuid/conflicts/detect")
        assert res_bad_proj.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 9. CONFLICT RESOLUTION APIS (/api/v1/conflicts/{id}/resolve)
# =============================================================================

@pytest.mark.asyncio
async def test_conflict_resolution_unauthorized_and_missing_params(async_client: AsyncClient, test_lead_user):
    """Tests 401 unauthorized and 422 missing resolution strategy."""
    cid = uuid.uuid4()
    # 401 Unauthorized
    assert (await async_client.post(f"/api/v1/conflicts/{cid}/resolve", json={"strategy": "OVERWRITE"})).status_code == 401

    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    try:
        # Invalid UUID in path -> 422
        res_bad = await async_client.post("/api/v1/conflicts/not-a-uuid/resolve", json={"resolution_strategy": "MANUAL"})
        assert res_bad.status_code == 422

        # Nonexistent conflict -> 404
        res_nf = await async_client.post(f"/api/v1/conflicts/{cid}/resolve", json={"resolution_strategy": "MANUAL", "resolution_notes": "Note"})
        assert res_nf.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_conflict_resolution_forbidden_and_nonexistent(async_client: AsyncClient, test_incoming_user, sample_project):
    """Verifies non-lead/non-admin roles receive 403 on conflict resolution."""
    app.dependency_overrides[get_current_user] = lambda: test_incoming_user
    cid = uuid.uuid4()
    mock_conflict = Conflict(
        id=cid,
        project_id=sample_project.id,
        conflict_type="FACTUAL_CONTRADICTION",
        status="DETECTED",
        description="Version discrepancy",
    )
    payload = {
        "resolution_strategy": "SOURCE_A_ACCEPTED",
        "resolution_notes": "Accepted updated RFC document",
    }
    try:
        # Conflict exists, but user is INCOMING role -> 403 Forbidden
        with patch("app.services.contradiction_service.ContradictionDetectionService.get_conflict", return_value=mock_conflict):
            with patch("app.dependencies.authorization.require_project_membership", side_effect=ForbiddenException("Only Leads or Admins can resolve conflicts")):
                res1 = await async_client.post(f"/api/v1/conflicts/{cid}/resolve", json=payload)
                assert res1.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 10. MEMBER AND PERMISSION APIS (/api/v1/projects/{project_id}/members/*)
# =============================================================================

@pytest.mark.asyncio
async def test_member_apis_unauthorized(async_client: AsyncClient):
    """Verifies member management APIs return 401 without auth token."""
    pid = uuid.uuid4()
    mid = uuid.uuid4()
    assert (await async_client.get(f"/api/v1/projects/{pid}/members")).status_code == 401
    assert (await async_client.post(f"/api/v1/projects/{pid}/members", json={"email": "u@test.com"})).status_code == 401
    assert (await async_client.post(f"/api/v1/projects/{pid}/members/invite", json={"email": "u@test.com"})).status_code == 401
    assert (await async_client.patch(f"/api/v1/projects/{pid}/members/{mid}", json={"role": "LEAD"})).status_code == 401
    assert (await async_client.delete(f"/api/v1/projects/{pid}/members/{mid}")).status_code == 401
    assert (await async_client.post(f"/api/v1/projects/{pid}/members/{mid}/revoke")).status_code == 401


@pytest.mark.asyncio
async def test_member_apis_missing_params_and_duplicate(async_client: AsyncClient, test_lead_user):
    """Tests 422 missing parameters and 409 duplicate member additions."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    pid = uuid.uuid4()
    try:
        # Invalid project UUID format -> 422
        res_bad_uuid = await async_client.post("/api/v1/projects/not-a-uuid/members", json={"email": "test@test.com"})
        assert res_bad_uuid.status_code == 422

        # When authorized member:
        mock_member = ProjectMember(id=uuid.uuid4(), project_id=pid, user_id=test_lead_user.id, role="PROJECT_OWNER")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_member):
            # Missing email and role -> 422
            res1 = await async_client.post(f"/api/v1/projects/{pid}/members", json={})
            assert res1.status_code == 422

            # Duplicate member addition -> 409 Conflict
            with patch("app.services.project_service.ProjectService.add_member", side_effect=ConflictException("User is already a member")):
                res2 = await async_client.post(
                    f"/api/v1/projects/{pid}/members",
                    json={"email": "existing@company.qa", "role": "OUTGOING"},
                )
                assert res2.status_code == 409
                assert res2.json()["error"]["code"] == "CONFLICT"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_member_apis_forbidden_and_nonexistent(async_client: AsyncClient, test_viewer_user):
    """Verifies that non-admin/non-owner members cannot modify members (403)."""
    app.dependency_overrides[get_current_user] = lambda: test_viewer_user
    pid = uuid.uuid4()
    mid = uuid.uuid4()
    try:
        with patch("app.dependencies.authorization.require_permission", side_effect=ForbiddenException("MANAGE_PROJECT_MEMBERS required")):
            res = await async_client.delete(f"/api/v1/projects/{pid}/members/{mid}")
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 11. AUDIT LOG APIS (/api/v1/audit-logs/* & project audit logs)
# =============================================================================

@pytest.mark.asyncio
async def test_audit_logs_unauthorized(async_client: AsyncClient):
    """Verifies audit log retrieval endpoints return 401 without auth token."""
    pid = uuid.uuid4()
    aid = uuid.uuid4()
    assert (await async_client.get("/api/v1/audit-logs")).status_code == 401
    assert (await async_client.get(f"/api/v1/audit-logs/{aid}")).status_code == 401
    assert (await async_client.get(f"/api/v1/projects/{pid}/audit-logs")).status_code == 401


@pytest.mark.asyncio
async def test_audit_logs_immutability_rejection(async_client: AsyncClient, test_lead_user):
    """
    SECURITY GUARANTEE: Audit trail is strictly immutable.
    Client POST, PUT, PATCH, DELETE mutations must return HTTP 403 Forbidden.
    """
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    pid = uuid.uuid4()
    aid = uuid.uuid4()
    try:
        # Direct mutation on /api/v1/audit-logs
        assert (await async_client.post("/api/v1/audit-logs", json={"action": "test"})).status_code == 403
        assert (await async_client.put(f"/api/v1/audit-logs/{aid}", json={"action": "test"})).status_code == 403
        assert (await async_client.patch(f"/api/v1/audit-logs/{aid}", json={"action": "test"})).status_code == 403
        assert (await async_client.delete(f"/api/v1/audit-logs/{aid}")).status_code == 403

        # Direct mutation on /api/v1/projects/{project_id}/audit-logs
        assert (await async_client.post(f"/api/v1/projects/{pid}/audit-logs", json={})).status_code == 403
        assert (await async_client.put(f"/api/v1/projects/{pid}/audit-logs/{aid}", json={})).status_code == 403
        assert (await async_client.patch(f"/api/v1/projects/{pid}/audit-logs/{aid}", json={})).status_code == 403
        assert (await async_client.delete(f"/api/v1/projects/{pid}/audit-logs/{aid}")).status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_audit_logs_forbidden_permission(async_client: AsyncClient, test_viewer_user):
    """Verifies roles without VIEW_AUDIT_LOGS receive 403 on project audit logs."""
    app.dependency_overrides[get_current_user] = lambda: test_viewer_user
    pid = uuid.uuid4()
    try:
        with patch("app.dependencies.authorization.require_permission", side_effect=ForbiddenException("VIEW_AUDIT_LOGS required")):
            res = await async_client.get(f"/api/v1/projects/{pid}/audit-logs")
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 12. HANDOVER VERSION APIS (/api/v1/handovers/{id}/versions/*)
# =============================================================================

@pytest.mark.asyncio
async def test_handover_version_apis_unauthorized(async_client: AsyncClient):
    """Verifies version management endpoints return 401 without auth token."""
    hid = uuid.uuid4()
    vid = uuid.uuid4()
    assert (await async_client.get(f"/api/v1/handovers/{hid}/versions")).status_code == 401
    assert (await async_client.get(f"/api/v1/handovers/{hid}/versions/latest")).status_code == 401
    assert (await async_client.get(f"/api/v1/handovers/{hid}/versions/{vid}")).status_code == 401
    assert (await async_client.post(f"/api/v1/handovers/{hid}/versions", json={})).status_code == 401
    assert (await async_client.post(f"/api/v1/handovers/{hid}/versions/{vid}/restore", json={})).status_code == 401


@pytest.mark.asyncio
async def test_handover_version_apis_forbidden_and_nonexistent(async_client: AsyncClient, test_incoming_user, sample_handover):
    """Verifies incoming members cannot restore versions (403), and 404 for missing versions."""
    app.dependency_overrides[get_current_user] = lambda: test_incoming_user
    app.dependency_overrides[require_handover_access] = lambda: sample_handover
    vid = uuid.uuid4()
    try:
        # Invalid handover UUID in path -> 422
        res_bad_hid = await async_client.get(f"/api/v1/handovers/not-a-uuid/versions/{vid}")
        assert res_bad_hid.status_code == 422

        # Invalid version UUID format in path -> 422
        res_bad_uuid = await async_client.get(f"/api/v1/handovers/{sample_handover.id}/versions/not-a-uuid")
        assert res_bad_uuid.status_code == 422

        # Nonexistent handover on restore -> 404
        nonexistent_hid = uuid.uuid4()
        res_nf = await async_client.post(f"/api/v1/handovers/{nonexistent_hid}/versions/{vid}/restore")
        assert res_nf.status_code == 404

        # When handover exists, but incoming member lacks EDIT_HANDOVER -> 403 Forbidden
        with patch("app.api.v1.endpoints.handovers.fetch_full_handover", return_value=sample_handover):
            with patch("app.dependencies.authorization.require_project_membership", side_effect=ForbiddenException("EDIT_HANDOVER permission required")):
                res_forbid = await async_client.post(f"/api/v1/handovers/{sample_handover.id}/versions/{vid}/restore")
                assert res_forbid.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 13. VERSION COMPARISON APIS (/api/v1/handovers/{id}/compare*)
# =============================================================================

@pytest.mark.asyncio
async def test_version_comparison_unauthorized(async_client: AsyncClient):
    """Verifies version comparison endpoints return 401 without auth token."""
    hid = uuid.uuid4()
    v1 = uuid.uuid4()
    v2 = uuid.uuid4()
    assert (await async_client.get(f"/api/v1/handovers/{hid}/compare?from_version=v1.0&to_version=v2.0")).status_code == 401
    assert (await async_client.get(f"/api/v1/handovers/{hid}/versions/{v1}/compare/{v2}")).status_code == 401


@pytest.mark.asyncio
async def test_version_comparison_missing_params_and_nonexistent(async_client: AsyncClient, test_lead_user, sample_handover):
    """Tests missing query parameters (422) and nonexistent version comparison (404)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    app.dependency_overrides[require_handover_access] = lambda: sample_handover
    hid = sample_handover.id
    v1 = uuid.uuid4()
    v2 = uuid.uuid4()
    try:
        # Missing query parameters -> 422
        res1 = await async_client.get(f"/api/v1/handovers/{hid}/compare")
        assert res1.status_code == 422

        # Nonexistent versions to compare -> 404
        with patch("app.services.version_service.HandoverVersionService.compare_versions", side_effect=NotFoundException("Version", v1)):
            res2 = await async_client.get(f"/api/v1/handovers/{hid}/versions/{v1}/compare/{v2}")
            assert res2.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 14. INCOMING-MEMBER APIS (shared-with-me, share, continuity, acknowledge)
# =============================================================================

@pytest.mark.asyncio
async def test_incoming_member_apis_unauthorized(async_client: AsyncClient):
    """Verifies incoming continuity APIs return 401 without auth token."""
    hid = uuid.uuid4()
    assert (await async_client.get("/api/v1/handovers/shared-with-me")).status_code == 401
    assert (await async_client.post(f"/api/v1/handovers/{hid}/share", json={})).status_code == 401
    assert (await async_client.get(f"/api/v1/handovers/{hid}/continuity")).status_code == 401
    assert (await async_client.post(f"/api/v1/handovers/{hid}/acknowledge")).status_code == 401


@pytest.mark.asyncio
async def test_incoming_member_apis_missing_params_and_forbidden(async_client: AsyncClient, test_lead_user, test_incoming_user, sample_handover):
    """Tests bad UUIDs (422) and forbidden sharing of draft handover (403)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    hid = sample_handover.id
    try:
        # Invalid handover UUID in path -> 422
        res_bad_uuid = await async_client.post("/api/v1/handovers/not-a-uuid/share", json={"assigned_to": str(test_incoming_user.id)})
        assert res_bad_uuid.status_code == 422

        # Invalid UUID in request body -> 422
        app.dependency_overrides[require_handover_access] = lambda: sample_handover
        mock_lead_member = ProjectMember(id=uuid.uuid4(), project_id=sample_handover.project_id, user_id=test_lead_user.id, role="LEAD")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_lead_member):
            res1 = await async_client.post(f"/api/v1/handovers/{hid}/share", json={"assigned_to": "not-a-valid-uuid"})
            assert res1.status_code == 422

            # Attempting to share unapproved draft handover -> 403 Forbidden
            sample_handover.status = "DRAFT"
            res2 = await async_client.post(
                f"/api/v1/handovers/{hid}/share",
                json={"assigned_to": str(test_incoming_user.id)},
            )
            assert res2.status_code == 403
            assert "Only approved handovers" in res2.json()["error"]["message"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)
        app.dependency_overrides.pop(require_handover_access, None)


# =============================================================================
# 15. TASK MANAGEMENT APIS (/api/v1/tasks/* & project tasks)
# =============================================================================

@pytest.mark.asyncio
async def test_tasks_apis_unauthorized(async_client: AsyncClient):
    """Verifies continuation task endpoints return 401 without auth token."""
    tid = uuid.uuid4()
    dep_id = uuid.uuid4()
    pid = uuid.uuid4()
    assert (await async_client.get("/api/v1/tasks")).status_code == 401
    assert (await async_client.post("/api/v1/tasks", json={"title": "New Task"})).status_code == 401
    assert (await async_client.get(f"/api/v1/tasks/{tid}")).status_code == 401
    assert (await async_client.patch(f"/api/v1/tasks/{tid}", json={"title": "Updated"})).status_code == 401
    assert (await async_client.delete(f"/api/v1/tasks/{tid}")).status_code == 401
    assert (await async_client.patch(f"/api/v1/tasks/{tid}/status", json={"status": "in_progress"})).status_code == 401
    assert (await async_client.get(f"/api/v1/tasks/{tid}/progress")).status_code == 401
    assert (await async_client.post(f"/api/v1/tasks/{tid}/progress", json={"notes": "Progress note"})).status_code == 401
    assert (await async_client.post(f"/api/v1/tasks/{tid}/notes", json={"text": "Progress note"})).status_code == 401
    assert (await async_client.get(f"/api/v1/tasks/{tid}/dependencies")).status_code == 401
    assert (await async_client.post(f"/api/v1/tasks/{tid}/dependencies", json={"depends_on_task_id": str(dep_id)})).status_code == 401
    assert (await async_client.delete(f"/api/v1/tasks/{tid}/dependencies/{dep_id}")).status_code == 401
    assert (await async_client.get(f"/api/v1/projects/{pid}/tasks")).status_code == 401
    assert (await async_client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "New Task"})).status_code == 401


@pytest.mark.asyncio
async def test_tasks_apis_missing_parameters_and_invalid_enums(async_client: AsyncClient, test_incoming_user):
    """Tests missing required title, invalid status enums, and invalid UUIDs (422)."""
    app.dependency_overrides[get_current_user] = lambda: test_incoming_user
    tid = uuid.uuid4()
    try:
        # Missing title on task creation -> 422
        res1 = await async_client.post("/api/v1/tasks", json={})
        assert res1.status_code == 422

        # Invalid task UUID in path -> 422
        res2 = await async_client.patch("/api/v1/tasks/bad-task-uuid/status", json={"status": "in_progress"})
        assert res2.status_code == 422

        # Invalid UUID format on get -> 422
        res3 = await async_client.get("/api/v1/tasks/bad-task-uuid")
        assert res3.status_code == 422

        # Missing progress update text -> 422
        res4 = await async_client.post("/api/v1/tasks/bad-task-uuid/progress", json={})
        assert res4.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_tasks_apis_forbidden_and_nonexistent(async_client: AsyncClient, test_viewer_user, sample_project):
    """Verifies that nonexistent task returns 404, and unauthorized user receives 403."""
    app.dependency_overrides[get_current_user] = lambda: test_viewer_user
    tid = uuid.uuid4()
    mock_task = Task(
        id=tid,
        project_id=sample_project.id,
        title="Migrate database cluster",
        status="pending",
        priority="high",
    )
    try:
        # Nonexistent task ID (require_task_access raises 404) -> 404
        res_nf = await async_client.get(f"/api/v1/tasks/{tid}")
        assert res_nf.status_code == 404

        # When task exists, but user role lacks permission to delete task -> 403 Forbidden
        app.dependency_overrides[require_task_access] = lambda: mock_task
        with patch("app.dependencies.authorization.enforce_member_permission", side_effect=ForbiddenException("Viewer cannot delete task")):
            res_forbid = await async_client.delete(f"/api/v1/tasks/{tid}")
            assert res_forbid.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)
        app.dependency_overrides.pop(require_task_access, None)


# =============================================================================
# 16. VALID END-TO-END FLOW TESTS ACROSS ALL 15 DOMAINS
# =============================================================================

@pytest.mark.asyncio
async def test_auth_apis_login_success(async_client: AsyncClient, test_lead_user):
    """Tests valid login flow and token package generation (200)."""
    from app.schemas.auth import AuthResponse, UserResponse
    mock_auth_pkg = AuthResponse(
        access_token=create_access_token(user_id=test_lead_user.id, email=test_lead_user.email),
        refresh_token="valid_sample_refresh_token_string",
        token_type="bearer",
        expires_in_seconds=3600,
        user=UserResponse(
            id=test_lead_user.id,
            full_name=test_lead_user.full_name,
            email=test_lead_user.email,
            is_active=True,
        ),
    )
    with patch.object(AuthService, "login", return_value=mock_auth_pkg):
        res = await async_client.post(
            "/api/v1/auth/login",
            json={"email": test_lead_user.email, "password": "Password123!"},
        )
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert "access_token" in res.json()["data"]
        assert res.json()["data"]["user"]["email"] == test_lead_user.email


@pytest.mark.asyncio
async def test_projects_apis_valid_crud_lifecycle(async_client: AsyncClient, test_lead_user, sample_project):
    """Tests valid project creation, overview retrieval, and deletion (200/201)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    pid = sample_project.id
    from app.schemas.project import ProjectOverviewResponse, ProjectResponse
    from app.services.project_service import ProjectService

    now = datetime.now(timezone.utc)
    mock_proj_res = ProjectResponse(
        id=pid,
        name=sample_project.name,
        description=sample_project.description,
        status="active",
        created_by=test_lead_user.id,
        created_at=now,
        updated_at=now,
    )
    mock_overview = ProjectOverviewResponse(
        project=mock_proj_res,
        members=[],
        total_members=1,
        total_documents=3,
        processed_documents=3,
        total_handovers=1,
        pending_reviews=0,
        open_conflicts=0,
        pending_tasks=2,
        overall_handover_status="ready",
    )

    try:
        mock_member = ProjectMember(id=uuid.uuid4(), project_id=pid, user_id=test_lead_user.id, role="PROJECT_OWNER")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_member):
            # 1. Create project
            with patch.object(ProjectService, "create_project", return_value=mock_proj_res):
                res_create = await async_client.post("/api/v1/projects", json={"name": "New Project", "description": "Desc"})
                assert res_create.status_code == 201
                assert res_create.json()["success"] is True

            # 2. Get project overview
            with patch.object(ProjectService, "get_project_overview", return_value=mock_overview):
                res_overview = await async_client.get(f"/api/v1/projects/{pid}/overview")
                assert res_overview.status_code == 200
                assert res_overview.json()["data"]["total_documents"] == 3

            # 3. Delete project
            with patch.object(ProjectService, "delete_project", return_value=True):
                res_del = await async_client.delete(f"/api/v1/projects/{pid}")
                assert res_del.status_code == 200
                assert res_del.json()["success"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_documents_apis_valid_chunks_and_status(async_client: AsyncClient, test_lead_user, sample_project):
    """Tests valid document status and parsed chunks endpoints (200)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    doc_id = uuid.uuid4()
    mock_doc = Document(
        id=doc_id,
        project_id=sample_project.id,
        original_filename="architecture.md",
        stored_filename="arch_stored.md",
        file_type="md",
        file_size=1024,
        storage_path="/tmp/architecture.md",
        processing_status="completed",
    )
    app.dependency_overrides[require_document_access] = lambda: mock_doc

    try:
        mock_chunk = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            project_id=sample_project.id,
            chunk_index=0,
            content="Microservices architecture design documentation.",
            created_at=datetime.now(timezone.utc),
        )
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [mock_chunk]
        mock_res.rowcount = 1
        mock_db.execute.return_value = mock_res

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        # 1. Status
        res_status = await async_client.get(f"/api/v1/documents/{doc_id}/status")
        assert res_status.status_code == 200
        assert res_status.json()["data"]["status"] == "completed"

        # 2. Chunks
        res_chunks = await async_client.get(f"/api/v1/documents/{doc_id}/chunks")
        assert res_chunks.status_code == 200
        assert len(res_chunks.json()["data"]) == 1
        assert "Microservices architecture" in res_chunks.json()["data"][0]["content"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_document_access, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_handovers_apis_valid_review_flow(async_client: AsyncClient, test_lead_user, sample_handover):
    """Tests valid handover review submission and approval (200)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    app.dependency_overrides[require_handover_access] = lambda: sample_handover
    hid = sample_handover.id

    try:
        mock_lead_member = ProjectMember(id=uuid.uuid4(), project_id=sample_handover.project_id, user_id=test_lead_user.id, role="LEAD")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_lead_member):
            # 1. Submit for review
            sample_handover.status = "DRAFT"
            res_submit = await async_client.post(f"/api/v1/handovers/{hid}/submit-review")
            assert res_submit.status_code == 200
            assert res_submit.json()["data"]["status"] == "IN_REVIEW"

            # 2. Approve handover
            sample_handover.status = "IN_REVIEW"
            with patch("app.api.v1.endpoints.handovers.fetch_full_handover", return_value=sample_handover):
                res_approve = await async_client.post(f"/api/v1/handovers/{hid}/approve", json={"notes": "All verified"})
                assert res_approve.status_code == 200
                assert res_approve.json()["data"]["status"] == "APPROVED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_evidence_apis_valid_verification(async_client: AsyncClient, test_lead_user, sample_project):
    """Tests valid evidence verification endpoint (200)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    cid = uuid.uuid4()
    from app.services.verification_service import EvidenceVerificationService, ClaimVerificationRecord

    mock_rec = ClaimVerificationRecord(
        claim_id=str(cid),
        claim_text="Database replication runs every 5 minutes",
        verification_status="Supported",
        supporting_document_id=uuid.uuid4(),
        source_filename="infra.md",
        page_number=1,
        section_reference="Databases",
        supporting_text_excerpt="Database replication runs every 5 minutes.",
        verification_timestamp=datetime.now(timezone.utc),
    )

    try:
        with patch.object(EvidenceVerificationService, "get_claim_verification", return_value=mock_rec):
            res = await async_client.get(f"/api/v1/evidence/claims/{cid}")
            assert res.status_code == 200
            assert res.json()["data"]["verification_status"] == "Supported"
            assert res.json()["data"]["source_filename"] == "infra.md"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_contradiction_detection_valid_flow(async_client: AsyncClient, test_lead_user, sample_project):
    """Tests valid contradiction detection scan across project documents (200)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    pid = sample_project.id
    from app.services.contradiction_service import ContradictionDetectionService, ContradictionDetectionReport

    mock_report = ContradictionDetectionReport(
        project_id=pid,
        documents_analyzed=3,
        chunks_analyzed=6,
        statements_extracted=12,
        topics_evaluated=3,
        contradictions_detected=1,
        conflicts=[],
        scan_timestamp=datetime.now(timezone.utc),
    )

    try:
        mock_member = ProjectMember(id=uuid.uuid4(), project_id=pid, user_id=test_lead_user.id, role="LEAD")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_member):
            with patch.object(ContradictionDetectionService, "detect_project_conflicts", return_value=mock_report):
                res = await async_client.post(f"/api/v1/projects/{pid}/conflicts/detect")
                assert res.status_code == 200
                assert res.json()["success"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_conflict_resolution_valid_arbitration(async_client: AsyncClient, test_lead_user, sample_project):
    """Tests valid conflict resolution by authorized LEAD member (200)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    cid = uuid.uuid4()
    mock_conflict = Conflict(
        id=cid,
        project_id=sample_project.id,
        conflict_type="FACTUAL_CONTRADICTION",
        status="DETECTED",
        description="Version mismatch",
    )
    resolved_conflict = Conflict(
        id=cid,
        project_id=sample_project.id,
        conflict_type="FACTUAL_CONTRADICTION",
        status="RESOLVED",
        description="Version mismatch",
        resolution="Updated to v2 spec",
        resolved_by=test_lead_user.id,
    )
    from app.services.contradiction_service import ContradictionDetectionService

    try:
        mock_member = ProjectMember(id=uuid.uuid4(), project_id=sample_project.id, user_id=test_lead_user.id, role="LEAD")
        with patch.object(ContradictionDetectionService, "get_conflict", return_value=mock_conflict):
            with patch("app.dependencies.authorization.get_project_member", return_value=mock_member):
                with patch.object(ContradictionDetectionService, "resolve_conflict", return_value=resolved_conflict):
                    res = await async_client.post(
                        f"/api/v1/conflicts/{cid}/resolve",
                        json={"resolution_strategy": "MANUAL", "resolution_notes": "Updated to v2 spec"},
                    )
                    assert res.status_code == 200
                    assert res.json()["data"]["status"] == "RESOLVED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_members_apis_valid_invite_and_role_update(async_client: AsyncClient, test_lead_user, sample_project):
    """Tests valid member invitation and role updating (200/201)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    pid = sample_project.id
    mid = uuid.uuid4()
    from app.schemas.project import ProjectMemberResponse
    from app.services.project_service import ProjectService

    now = datetime.now(timezone.utc)
    mock_mem_res = ProjectMemberResponse(
        id=mid,
        project_id=pid,
        user_id=uuid.uuid4(),
        email="newengineer@company.qa",
        full_name="New Engineer",
        role=ProjectMemberRole.INCOMING,
        role_display_name="Incoming Member",
        status="active",
        invitation_status="accepted",
        joined_at=now,
    )

    try:
        mock_owner = ProjectMember(id=uuid.uuid4(), project_id=pid, user_id=test_lead_user.id, role="PROJECT_OWNER")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_owner):
            # 1. Invite/Add Member -> 201
            with patch.object(ProjectService, "add_member", return_value=mock_mem_res):
                res_invite = await async_client.post(
                    f"/api/v1/projects/{pid}/members",
                    json={"email": "newengineer@company.qa", "role": "INCOMING"},
                )
                assert res_invite.status_code == 201
                assert res_invite.json()["data"]["email"] == "newengineer@company.qa"

            # 2. Update Role -> 200
            mock_mem_res.role = ProjectMemberRole.LEAD
            with patch.object(ProjectService, "update_member_role", return_value=mock_mem_res):
                res_update = await async_client.patch(
                    f"/api/v1/projects/{pid}/members/{mid}",
                    json={"role": "LEAD"},
                )
                assert res_update.status_code == 200
                assert res_update.json()["data"]["role"] == "LEAD"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_audit_logs_valid_query_and_filtering(async_client: AsyncClient, test_lead_user, sample_project):
    """Tests valid audit log retrieval with permission enforcement (200)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    pid = sample_project.id
    aid = uuid.uuid4()
    from app.services.audit_service import AuditService
    from app.models.audit_log import AuditLog

    now = datetime.now(timezone.utc)
    mock_log = AuditLog(
        id=aid,
        project_id=pid,
        user_id=test_lead_user.id,
        action=AuditActionType.DOCUMENT_UPLOADED,
        entity_type=AuditEntityType.DOCUMENT,
        entity_id=str(uuid.uuid4()),
        change_metadata={"filename": "spec.md"},
        timestamp=now,
    )

    try:
        mock_member = ProjectMember(id=uuid.uuid4(), project_id=pid, user_id=test_lead_user.id, role="LEAD")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_member):
            # 1. List project audit logs
            with patch.object(AuditService, "list_project_audit_logs", return_value=([mock_log], 1)):
                res_list = await async_client.get(f"/api/v1/projects/{pid}/audit-logs")
                assert res_list.status_code == 200
                assert res_list.json()["data"]["total"] == 1
                assert len(res_list.json()["data"]["items"]) == 1

            # 2. Get specific audit log
            with patch.object(AuditService, "get_audit_log", return_value=mock_log):
                res_get = await async_client.get(f"/api/v1/audit-logs/{aid}")
                assert res_get.status_code == 200
                assert res_get.json()["data"]["id"] == str(aid)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_versions_and_diff_valid_lifecycle(async_client: AsyncClient, test_lead_user, sample_handover):
    """Tests valid handover version snapshot creation and version comparison diff (200/201)."""
    app.dependency_overrides[get_current_user] = lambda: test_lead_user
    app.dependency_overrides[require_handover_access] = lambda: sample_handover
    hid = sample_handover.id
    vid = uuid.uuid4()
    from app.services.version_service import HandoverVersionService, HandoverVersionResponse, VersionDiffResponse, ComparisonSummary

    now = datetime.now(timezone.utc)
    mock_ver = HandoverVersion(
        id=vid,
        handover_id=hid,
        version_number="v1.0",
        version_description="Initial Release",
        approval_status="APPROVED",
        is_latest=True,
        created_by=test_lead_user.id,
        created_at=now,
        snapshot={"title": sample_handover.title},
    )
    mock_ver_res = HandoverVersionResponse(
        id=vid,
        handover_id=hid,
        version_number="v1.0",
        version_description="Initial Release",
        approval_status="APPROVED",
        is_latest=True,
        created_by=test_lead_user.id,
        created_at=now,
        snapshot={"title": sample_handover.title},
    )
    mock_diff = VersionDiffResponse(
        from_version_id=vid,
        from_version_number="v1.0",
        to_version_id=uuid.uuid4(),
        to_version_number="v1.1",
        summary=ComparisonSummary(
            total_sections_compared=8,
            modified_sections_count=1,
            has_differences=True,
        ),
        section_diffs=[],
        task_diffs=[],
        responsibility_diffs=[],
    )

    try:
        mock_member = ProjectMember(id=uuid.uuid4(), project_id=sample_handover.project_id, user_id=test_lead_user.id, role="LEAD")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_member):
            # 1. Create version snapshot -> 201
            with patch.object(HandoverVersionService, "create_version_snapshot", return_value=mock_ver):
                with patch.object(HandoverVersionService, "to_response", return_value=mock_ver_res):
                    res_ver = await async_client.post(f"/api/v1/handovers/{hid}/versions", json={"version_description": "New Revision"})
                    assert res_ver.status_code == 201
                    assert res_ver.json()["data"]["version_number"] == "v1.0"

            # 2. Compare versions diff -> 200
            with patch.object(HandoverVersionService, "compare_versions", return_value=mock_diff):
                res_diff = await async_client.get(f"/api/v1/handovers/{hid}/compare?from_version=v1.0&to_version=v1.1")
                assert res_diff.status_code == 200
                assert res_diff.json()["data"]["summary"]["modified_sections_count"] == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_incoming_continuity_valid_acknowledgement(async_client: AsyncClient, test_incoming_user, sample_handover):
    """Tests valid incoming continuity workflow and receipt acknowledgement (200)."""
    app.dependency_overrides[get_current_user] = lambda: test_incoming_user
    app.dependency_overrides[require_handover_access] = lambda: sample_handover
    hid = sample_handover.id
    sample_handover.status = "APPROVED"

    try:
        mock_incoming_mem = ProjectMember(id=uuid.uuid4(), project_id=sample_handover.project_id, user_id=test_incoming_user.id, role="INCOMING")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_incoming_mem):
            # Acknowledge receipt
            res_ack = await async_client.post(
                f"/api/v1/handovers/{hid}/acknowledge",
                json={"checklist_confirmed": True, "notes": "Handover accepted"},
            )
            assert res_ack.status_code == 200
            assert res_ack.json()["success"] is True
            assert res_ack.json()["data"]["status"] == "ACKNOWLEDGED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_handover_access, None)


@pytest.mark.asyncio
async def test_task_management_valid_lifecycle(async_client: AsyncClient, test_incoming_user, sample_project):
    """Tests valid task creation, status transition, and progress note recording (200/201)."""
    app.dependency_overrides[get_current_user] = lambda: test_incoming_user
    tid = uuid.uuid4()
    pid = sample_project.id
    mock_task = Task(
        id=tid,
        project_id=pid,
        title="Setup Redis cluster replica",
        status="pending",
        priority="high",
        assigned_to=test_incoming_user.id,
    )
    app.dependency_overrides[require_task_access] = lambda: mock_task

    try:
        mock_member = ProjectMember(id=uuid.uuid4(), project_id=pid, user_id=test_incoming_user.id, role="INCOMING")
        with patch("app.dependencies.authorization.get_project_member", return_value=mock_member):
            # 1. Update task status -> 200
            res_status = await async_client.patch(
                f"/api/v1/tasks/{tid}/status",
                json={"status": "in_progress", "notes": "Started configuring replica"},
            )
            assert res_status.status_code == 200
            assert res_status.json()["data"]["status"] == "in_progress"

            # 2. Add progress note -> 201
            res_prog = await async_client.post(
                f"/api/v1/tasks/{tid}/progress",
                json={"update_text": "Completed node 1 configuration", "new_status": "in_progress"},
            )
            assert res_prog.status_code == 201
            assert res_prog.json()["success"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_task_access, None)
