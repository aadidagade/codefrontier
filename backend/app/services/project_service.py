from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    MemberAdd,
    MemberUpdateRole,
    ProjectMemberResponse,
    MemberRevokeResponse,
    ProjectOverviewResponse,
)
from app.core.permissions import ROLE_DISPLAY_NAMES, normalize_role
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)


class ProjectService:
    """
    Business service executing project workspace operations, member assignments,
    governance constraints (e.g. minimum ADMIN retention), and live metrics collation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.user_repo = UserRepository(db)

    def _format_member_response(self, pm: ProjectMember, user: User) -> ProjectMemberResponse:
        """Helper to build standardized ProjectMemberResponse with role display name and status."""
        canonical_role = normalize_role(pm.role)
        display_name = ROLE_DISPLAY_NAMES.get(canonical_role, pm.role)
        return ProjectMemberResponse(
            id=pm.id,
            project_id=pm.project_id,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            profile_image=user.profile_image,
            role=pm.role,
            role_display_name=display_name,
            status=getattr(pm, "status", None) or "active",
            invitation_status=getattr(pm, "invitation_status", None) or "accepted",
            invited_by=getattr(pm, "invited_by", None),
            invited_at=getattr(pm, "invited_at", None),
            joined_at=pm.joined_at,
            custom_permissions=getattr(pm, "custom_permissions", None),
        )

    async def create_project(self, payload: ProjectCreate, creator_id: uuid.UUID) -> ProjectResponse:
        """Initializes a new project and enlists creator as ADMIN."""
        project = await self.project_repo.create_project(
            name=payload.name,
            created_by=creator_id,
            description=payload.description,
            organization_name=payload.organization_name,
        )
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            organization_name=project.organization_name,
            status=project.status,
            created_by=project.created_by,
            created_at=project.created_at,
            updated_at=project.updated_at,
            members_count=1,
        )

    async def list_user_projects(self, user_id: uuid.UUID) -> List[ProjectResponse]:
        """Lists projects the user is authorized to access."""
        records = await self.project_repo.list_by_user(user_id)
        return [
            ProjectResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                organization_name=p.organization_name,
                status=p.status,
                created_by=p.created_by,
                created_at=p.created_at,
                updated_at=p.updated_at,
                members_count=m_count,
            )
            for p, m_count in records
        ]

    async def get_project(self, project_id: uuid.UUID) -> ProjectResponse:
        """Retrieves single project details."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        admin_count = await self.project_repo.count_admins(project_id)
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            organization_name=project.organization_name,
            status=project.status,
            created_by=project.created_by,
            created_at=project.created_at,
            updated_at=project.updated_at,
            members_count=admin_count,
        )

    async def update_project(self, project_id: uuid.UUID, payload: ProjectUpdate) -> ProjectResponse:
        """Updates project details."""
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return await self.get_project(project_id)

        updated_project = await self.project_repo.update_project(project_id, updates)
        if not updated_project:
            raise NotFoundException("Project", project_id)

        return ProjectResponse.model_validate(updated_project)

    async def delete_project(self, project_id: uuid.UUID) -> bool:
        """Deletes a project and cascaded records."""
        deleted = await self.project_repo.delete_project(project_id)
        if not deleted:
            raise NotFoundException("Project", project_id)
        return True

    # -------------------------------------------------------------------------
    # Member Workflows
    # -------------------------------------------------------------------------

    async def list_members(self, project_id: uuid.UUID, status_filter: Optional[str] = None) -> List[ProjectMemberResponse]:
        """Lists all members assigned to a project."""
        records = await self.project_repo.list_members_with_users(project_id, status_filter=status_filter)
        return [self._format_member_response(pm, u) for pm, u in records]

    async def add_member(
        self,
        project_id: uuid.UUID,
        payload: MemberAdd,
        inviter_id: Optional[uuid.UUID] = None,
    ) -> ProjectMemberResponse:
        """Invites/adds an existing registered user to a project with designated role and status."""
        target_user = None
        if payload.user_id:
            target_user = await self.user_repo.get_by_id(payload.user_id)
        elif payload.email:
            target_user = await self.user_repo.get_by_email(payload.email)
        else:
            raise ValidationException("Either 'email' or 'user_id' must be provided to add a member.")

        if not target_user:
            identifier = str(payload.user_id) if payload.user_id else str(payload.email)
            raise NotFoundException("User", identifier)

        now = datetime.now(timezone.utc)
        initial_status = payload.status or "active"
        invitation_status = "accepted" if initial_status == "active" else "pending"
        role_str = payload.role.value if hasattr(payload.role, "value") else str(payload.role)

        # Check if already a member
        existing_member = await self.project_repo.get_member(project_id, target_user.id)
        if existing_member:
            if existing_member.status == "revoked":
                # Re-activate revoked member with newly designated role
                updated = await self.project_repo.update_member_role(
                    member_id=existing_member.id,
                    new_role=role_str,
                    custom_permissions=payload.custom_permissions,
                    status=initial_status,
                )
                if inviter_id:
                    updated.invited_by = inviter_id
                    updated.invited_at = now
                    await self.db.commit()
                    await self.db.refresh(updated)
                return self._format_member_response(updated, target_user)
            else:
                raise ConflictException(
                    message=f"User '{target_user.email}' is already an authorized member of this project.",
                    details={"user_id": str(target_user.id), "current_role": existing_member.role, "status": existing_member.status},
                )

        new_member = await self.project_repo.add_member(
            project_id=project_id,
            user_id=target_user.id,
            role=role_str,
            custom_permissions=payload.custom_permissions,
            status=initial_status,
            invitation_status=invitation_status,
            invited_by=inviter_id,
            invited_at=now if inviter_id else None,
        )

        return self._format_member_response(new_member, target_user)

    async def update_member_role(
        self,
        project_id: uuid.UUID,
        member_id: uuid.UUID,
        payload: MemberUpdateRole,
    ) -> ProjectMemberResponse:
        """Updates a member's role while guaranteeing at least one ADMIN/OWNER remains."""
        member = await self.project_repo.get_member_by_id(member_id)
        if not member or member.project_id != project_id:
            raise NotFoundException("ProjectMember", member_id)

        role_str = payload.role.value if hasattr(payload.role, "value") else str(payload.role)

        # Check admin/owner retention
        if member.role in (ProjectMemberRole.ADMIN.value, ProjectMemberRole.PROJECT_OWNER.value) and role_str not in (ProjectMemberRole.ADMIN.value, ProjectMemberRole.PROJECT_OWNER.value):
            admin_count = await self.project_repo.count_admins(project_id)
            if admin_count <= 1:
                raise ConflictException("Cannot demote member: A project workspace must retain at least one active ADMIN or Project Owner.")

        updated_member = await self.project_repo.update_member_role(
            member_id=member_id,
            new_role=role_str,
            custom_permissions=payload.custom_permissions,
            status=payload.status,
        )
        user = await self.user_repo.get_by_id(updated_member.user_id)
        return self._format_member_response(updated_member, user)

    async def revoke_member_access(
        self,
        project_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> MemberRevokeResponse:
        """Revokes a member's access to the project workspace, effective immediately."""
        member = await self.project_repo.get_member_by_id(member_id)
        if not member or member.project_id != project_id:
            raise NotFoundException("ProjectMember", member_id)

        # Check admin/owner retention
        if member.role in (ProjectMemberRole.ADMIN.value, ProjectMemberRole.PROJECT_OWNER.value):
            admin_count = await self.project_repo.count_admins(project_id)
            if admin_count <= 1:
                raise ConflictException("Cannot revoke access: A project workspace must retain at least one active ADMIN or Project Owner.")

        now = datetime.now(timezone.utc)
        revoked = await self.project_repo.update_member_status(
            member_id=member_id,
            status="revoked",
            invitation_status="revoked",
        )
        return MemberRevokeResponse(
            member_id=revoked.id,
            project_id=revoked.project_id,
            user_id=revoked.user_id,
            status="revoked",
            invitation_status="revoked",
            revoked_at=now,
            message="Project workspace access revoked successfully.",
        )

    async def accept_invitation(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ProjectMemberResponse:
        """Allows an invited registered user to accept project workspace membership."""
        member = await self.project_repo.get_member(project_id, user_id)
        if not member:
            raise NotFoundException("ProjectMember invitation", str(user_id))

        if member.status == "revoked":
            raise ForbiddenException("Access denied: Your project membership has been revoked.")

        now = datetime.now(timezone.utc)
        updated = await self.project_repo.update_member_status(
            member_id=member.id,
            status="active",
            invitation_status="accepted",
        )
        user = await self.user_repo.get_by_id(user_id)
        return self._format_member_response(updated, user)

    async def remove_member(self, project_id: uuid.UUID, member_id: uuid.UUID) -> bool:
        """Removes a member from the project while guaranteeing at least one ADMIN/OWNER remains."""
        member = await self.project_repo.get_member_by_id(member_id)
        if not member or member.project_id != project_id:
            raise NotFoundException("ProjectMember", member_id)

        # Check admin retention
        if member.role in (ProjectMemberRole.ADMIN.value, ProjectMemberRole.PROJECT_OWNER.value):
            admin_count = await self.project_repo.count_admins(project_id)
            if admin_count <= 1:
                raise ConflictException("Cannot remove member: A project workspace must retain at least one active ADMIN or Project Owner.")

        return await self.project_repo.remove_member(member_id)

    # -------------------------------------------------------------------------
    # Project Overview & Live Metrics
    # -------------------------------------------------------------------------

    async def get_project_overview(self, project_id: uuid.UUID) -> ProjectOverviewResponse:
        """
        Collates live project metrics, member listings, and document statistics.
        All metrics are derived from actual PostgreSQL database queries.
        """
        project = await self.get_project(project_id)
        members = await self.list_members(project_id)
        stats = await self.project_repo.get_project_statistics(project_id)

        return ProjectOverviewResponse(
            project=project,
            members=members,
            total_members=len(members),
            total_documents=stats["total_documents"],
            processed_documents=stats["processed_documents"],
            total_handovers=stats["total_handovers"],
            pending_reviews=stats["pending_reviews"],
            open_conflicts=stats["open_conflicts"],
            pending_tasks=stats["pending_tasks"],
            overall_handover_status=stats["overall_handover_status"],
            recent_activity=stats["recent_activity"],
        )
