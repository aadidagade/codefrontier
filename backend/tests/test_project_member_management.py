import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import Permission, ProjectRole
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.user import User
from app.schemas.project import (
    MemberAdd,
    MemberUpdateRole,
    ProjectMemberResponse,
    MemberRevokeResponse,
)
from app.services.project_service import ProjectService
from app.dependencies.authorization import enforce_member_permission


# =============================================================================
# 1. FEATURE 1 & 2: INVITE REGISTERED USERS & ASSIGN ROLES
# =============================================================================

@pytest.mark.asyncio
async def test_project_owner_can_invite_registered_user_with_role():
    """
    Feature 1 & 2: Project owners can invite existing registered users to a project
    and assign roles (Admin, Project Owner, Outgoing, Incoming, Reviewer).
    """
    mock_db = AsyncMock()
    service = ProjectService(mock_db)

    project_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    target_user_id = uuid.uuid4()

    target_user = User(
        id=target_user_id,
        full_name="Bob Developer",
        email="bob@company.internal",
        is_active=True,
    )

    created_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=target_user_id,
        role=ProjectMemberRole.REVIEWER.value,
        status="invited",
        invitation_status="pending",
        invited_by=owner_id,
        invited_at=datetime.now(timezone.utc),
        joined_at=datetime.now(timezone.utc),
    )

    with patch.object(service.user_repo, "get_by_email", return_value=target_user):
        with patch.object(service.project_repo, "get_member", return_value=None):
            with patch.object(service.project_repo, "add_member", return_value=created_member):
                payload = MemberAdd(
                    email="bob@company.internal",
                    role="Reviewer",
                    status="invited",
                )
                res = await service.add_member(
                    project_id=project_id,
                    payload=payload,
                    inviter_id=owner_id,
                )

    assert res.email == "bob@company.internal"
    assert res.role == ProjectMemberRole.REVIEWER.value
    assert res.role_display_name == "Reviewer"
    assert res.status == "invited"
    assert res.invitation_status == "pending"
    assert res.invited_by == owner_id


@pytest.mark.asyncio
async def test_invite_non_existent_user_raises_not_found():
    """Feature 1: Inviting an unregistered email raises NotFoundException."""
    mock_db = AsyncMock()
    service = ProjectService(mock_db)
    project_id = uuid.uuid4()

    with patch.object(service.user_repo, "get_by_email", return_value=None):
        payload = MemberAdd(email="ghost@company.internal", role=ProjectMemberRole.INCOMING)
        with pytest.raises(NotFoundException) as exc_info:
            await service.add_member(project_id, payload)
        assert "ghost@company.internal" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invite_already_active_member_raises_conflict():
    """Feature 1: Inviting a user who is already an active member raises ConflictException."""
    mock_db = AsyncMock()
    service = ProjectService(mock_db)
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    existing_user = User(id=user_id, email="existing@company.internal")
    existing_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
    )

    with patch.object(service.user_repo, "get_by_email", return_value=existing_user):
        with patch.object(service.project_repo, "get_member", return_value=existing_member):
            payload = MemberAdd(email="existing@company.internal", role=ProjectMemberRole.OUTGOING)
            with pytest.raises(ConflictException) as exc_info:
                await service.add_member(project_id, payload)
            assert "already an authorized member" in str(exc_info.value.message)


# =============================================================================
# 2. FEATURE 3: CHANGE MEMBER ROLES
# =============================================================================

@pytest.mark.asyncio
async def test_project_owner_can_change_member_roles():
    """Feature 3: Project owners can change member roles."""
    mock_db = AsyncMock()
    service = ProjectService(mock_db)

    project_id = uuid.uuid4()
    member_id = uuid.uuid4()
    user_id = uuid.uuid4()

    existing_member = ProjectMember(
        id=member_id,
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
        joined_at=datetime.now(timezone.utc),
    )

    updated_member = ProjectMember(
        id=member_id,
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.PROJECT_OWNER.value,
        status="active",
        joined_at=datetime.now(timezone.utc),
    )

    user = User(id=user_id, full_name="Alice Smith", email="alice@test.com")

    with patch.object(service.project_repo, "get_member_by_id", return_value=existing_member):
        with patch.object(service.project_repo, "update_member_role", return_value=updated_member):
            with patch.object(service.user_repo, "get_by_id", return_value=user):
                payload = MemberUpdateRole(role="Project Owner")
                res = await service.update_member_role(project_id, member_id, payload)

    assert res.role == ProjectMemberRole.PROJECT_OWNER.value
    assert res.role_display_name == "Project Owner"


@pytest.mark.asyncio
async def test_change_role_prevents_demoting_last_project_admin_or_owner():
    """Feature 3: Prevents demoting the last active Project Owner / Admin."""
    mock_db = AsyncMock()
    service = ProjectService(mock_db)

    project_id = uuid.uuid4()
    member_id = uuid.uuid4()

    sole_owner = ProjectMember(
        id=member_id,
        project_id=project_id,
        user_id=uuid.uuid4(),
        role=ProjectMemberRole.PROJECT_OWNER.value,
        status="active",
    )

    with patch.object(service.project_repo, "get_member_by_id", return_value=sole_owner):
        with patch.object(service.project_repo, "count_admins", return_value=1):
            payload = MemberUpdateRole(role=ProjectMemberRole.INCOMING)
            with pytest.raises(ConflictException) as exc_info:
                await service.update_member_role(project_id, member_id, payload)
            assert "retain at least one active ADMIN or Project Owner" in str(exc_info.value.message)


# =============================================================================
# 3. FEATURE 4: REVOKE PROJECT ACCESS
# =============================================================================

@pytest.mark.asyncio
async def test_project_owner_can_revoke_project_access():
    """Feature 4: Project owners can revoke project access."""
    mock_db = AsyncMock()
    service = ProjectService(mock_db)

    project_id = uuid.uuid4()
    member_id = uuid.uuid4()
    user_id = uuid.uuid4()

    active_member = ProjectMember(
        id=member_id,
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.OUTGOING.value,
        status="active",
    )

    revoked_member = ProjectMember(
        id=member_id,
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.OUTGOING.value,
        status="revoked",
        invitation_status="revoked",
    )

    with patch.object(service.project_repo, "get_member_by_id", return_value=active_member):
        with patch.object(service.project_repo, "update_member_status", return_value=revoked_member):
            res = await service.revoke_member_access(project_id, member_id)

    assert isinstance(res, MemberRevokeResponse)
    assert res.status == "revoked"
    assert res.invitation_status == "revoked"
    assert res.member_id == member_id


@pytest.mark.asyncio
async def test_revoke_prevents_revoking_last_project_admin_or_owner():
    """Feature 4: Prevents revoking access for the last active Project Owner or Admin."""
    mock_db = AsyncMock()
    service = ProjectService(mock_db)

    project_id = uuid.uuid4()
    member_id = uuid.uuid4()

    sole_admin = ProjectMember(
        id=member_id,
        project_id=project_id,
        user_id=uuid.uuid4(),
        role=ProjectMemberRole.ADMIN.value,
        status="active",
    )

    with patch.object(service.project_repo, "get_member_by_id", return_value=sole_admin):
        with patch.object(service.project_repo, "count_admins", return_value=1):
            with pytest.raises(ConflictException) as exc_info:
                await service.revoke_member_access(project_id, member_id)
            assert "retain at least one active ADMIN or Project Owner" in str(exc_info.value.message)


# =============================================================================
# 4. FEATURE 5, 6, 7: DISPLAY MEMBERS, ASSIGNED ROLES, STATUSES
# =============================================================================

@pytest.mark.asyncio
async def test_display_all_project_members_with_roles_and_statuses():
    """
    Features 5, 6, 7:
    - Display all project members
    - Display each member's assigned role (role + role_display_name)
    - Display invitation and membership status (status + invitation_status)
    """
    mock_db = AsyncMock()
    service = ProjectService(mock_db)
    project_id = uuid.uuid4()

    user1 = User(id=uuid.uuid4(), full_name="Sarah Connor", email="sarah@test.com")
    user2 = User(id=uuid.uuid4(), full_name="John Connor", email="john@test.com")

    pm1 = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user1.id,
        role=ProjectMemberRole.PROJECT_OWNER.value,
        status="active",
        invitation_status="accepted",
        joined_at=datetime.now(timezone.utc),
    )
    pm2 = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user2.id,
        role=ProjectMemberRole.INCOMING.value,
        status="invited",
        invitation_status="pending",
        joined_at=datetime.now(timezone.utc),
    )

    mock_records = [(pm1, user1), (pm2, user2)]

    with patch.object(service.project_repo, "list_members_with_users", return_value=mock_records):
        members = await service.list_members(project_id)

    assert len(members) == 2

    # Verify PM 1
    assert members[0].full_name == "Sarah Connor"
    assert members[0].role == ProjectMemberRole.PROJECT_OWNER.value
    assert members[0].role_display_name == "Project Owner"
    assert members[0].status == "active"
    assert members[0].invitation_status == "accepted"

    # Verify PM 2
    assert members[1].full_name == "John Connor"
    assert members[1].role == ProjectMemberRole.INCOMING.value
    assert members[1].role_display_name == "Incoming Member"
    assert members[1].status == "invited"
    assert members[1].invitation_status == "pending"


@pytest.mark.asyncio
async def test_invited_member_can_accept_invitation():
    """Feature 7: An invited user can accept invitation, transitioning to active."""
    mock_db = AsyncMock()
    service = ProjectService(mock_db)

    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    invited_pm = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.INCOMING.value,
        status="invited",
        invitation_status="pending",
    )

    accepted_pm = ProjectMember(
        id=invited_pm.id,
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
        invitation_status="accepted",
        joined_at=datetime.now(timezone.utc),
    )
    user = User(id=user_id, full_name="New Member", email="new@test.com")

    with patch.object(service.project_repo, "get_member", return_value=invited_pm):
        with patch.object(service.project_repo, "update_member_status", return_value=accepted_pm):
            with patch.object(service.user_repo, "get_by_id", return_value=user):
                res = await service.accept_invitation(project_id, user_id)

    assert res.status == "active"
    assert res.invitation_status == "accepted"


# =============================================================================
# 5. FEATURE 8: PREVENT UNAUTHORIZED USERS FROM MANAGING MEMBERS
# =============================================================================

@pytest.mark.asyncio
async def test_unauthorized_roles_cannot_manage_project_members():
    """
    Feature 8: Prevent unauthorized users from managing project members.
    Incoming, Outgoing, and Reviewer members CANNOT manage project members.
    """
    project_id = uuid.uuid4()

    for unauthorized_role in [
        ProjectMemberRole.INCOMING,
        ProjectMemberRole.OUTGOING,
        ProjectMemberRole.REVIEWER,
    ]:
        unauthorized_member = ProjectMember(
            id=uuid.uuid4(),
            project_id=project_id,
            user_id=uuid.uuid4(),
            role=unauthorized_role.value,
            status="active",
        )

        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = unauthorized_member
        mock_db.execute.return_value = mock_res

        with pytest.raises(ForbiddenException) as exc_info:
            await enforce_member_permission(
                project_id=project_id,
                user_id=unauthorized_member.user_id,
                permission=Permission.MANAGE_PROJECT_MEMBERS,
                db=mock_db,
            )

        assert "Missing required permission 'manage_project_members'" in exc_info.value.message


# =============================================================================
# 6. IMMEDIATE ENFORCEMENT ON SUBSEQUENT REQUESTS
# =============================================================================

@pytest.mark.asyncio
async def test_revoking_access_takes_effect_immediately_on_subsequent_request():
    """
    Requirement: Ensure that revoking permissions takes effect immediately on subsequent API requests.
    Once status is set to 'revoked', subsequent enforce_member_permission calls immediately raise 403.
    """
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    revoked_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.PROJECT_OWNER.value,  # even if previous role was owner
        status="revoked",  # revoked
        invitation_status="revoked",
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = revoked_member
    mock_db.execute.return_value = mock_res

    # Attempt any action
    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(
            project_id=project_id,
            user_id=user_id,
            permission=Permission.VIEW_PROJECT,
            db=mock_db,
        )

    assert "membership has been revoked" in exc_info.value.message


@pytest.mark.asyncio
async def test_changing_role_takes_effect_immediately_on_subsequent_request():
    """
    Requirement: Ensure that changing permissions takes effect immediately on subsequent API requests.
    If an Outgoing member is changed to Incoming member in the DB, attempting to generate a handover
    on the very next request immediately raises 403 Forbidden.
    """
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Role was just changed in DB to INCOMING
    demoted_member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=ProjectMemberRole.INCOMING.value,
        status="active",
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = demoted_member
    mock_db.execute.return_value = mock_res

    # Attempt generate_handover (which Outgoing can do, but Incoming cannot)
    with pytest.raises(ForbiddenException) as exc_info:
        await enforce_member_permission(
            project_id=project_id,
            user_id=user_id,
            permission=Permission.GENERATE_HANDOVER,
            db=mock_db,
        )

    assert "Missing required permission 'generate_handover'" in exc_info.value.message
