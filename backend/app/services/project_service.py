import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    MemberAdd,
    MemberUpdateRole,
    ProjectMemberResponse,
    ProjectOverviewResponse,
)
from app.core.exceptions import (
    ConflictException,
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

    async def list_members(self, project_id: uuid.UUID) -> List[ProjectMemberResponse]:
        """Lists all members assigned to a project."""
        records = await self.project_repo.list_members_with_users(project_id)
        return [
            ProjectMemberResponse(
                id=pm.id,
                project_id=pm.project_id,
                user_id=u.id,
                full_name=u.full_name,
                email=u.email,
                profile_image=u.profile_image,
                role=pm.role,
                joined_at=pm.joined_at,
            )
            for pm, u in records
        ]

    async def add_member(self, project_id: uuid.UUID, payload: MemberAdd) -> ProjectMemberResponse:
        """Invites/adds an existing registered user to a project with designated role."""
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

        # Check if already a member
        existing_member = await self.project_repo.get_member(project_id, target_user.id)
        if existing_member:
            raise ConflictException(
                message=f"User '{target_user.email}' is already an authorized member of this project.",
                details={"user_id": str(target_user.id), "current_role": existing_member.role},
            )

        new_member = await self.project_repo.add_member(
            project_id=project_id,
            user_id=target_user.id,
            role=payload.role.value,
        )

        return ProjectMemberResponse(
            id=new_member.id,
            project_id=new_member.project_id,
            user_id=target_user.id,
            full_name=target_user.full_name,
            email=target_user.email,
            profile_image=target_user.profile_image,
            role=new_member.role,
            joined_at=new_member.joined_at,
        )

    async def update_member_role(
        self,
        project_id: uuid.UUID,
        member_id: uuid.UUID,
        payload: MemberUpdateRole,
    ) -> ProjectMemberResponse:
        """Updates a member's role while guaranteeing at least one ADMIN remains."""
        member = await self.project_repo.get_member_by_id(member_id)
        if not member or member.project_id != project_id:
            raise NotFoundException("ProjectMember", member_id)

        # Check admin retention
        if member.role == ProjectMemberRole.ADMIN.value and payload.role != ProjectMemberRole.ADMIN:
            admin_count = await self.project_repo.count_admins(project_id)
            if admin_count <= 1:
                raise ConflictException("Cannot demote member: A project workspace must retain at least one active ADMIN.")

        updated_member = await self.project_repo.update_member_role(member_id, payload.role.value)
        user = await self.user_repo.get_by_id(updated_member.user_id)

        return ProjectMemberResponse(
            id=updated_member.id,
            project_id=updated_member.project_id,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            profile_image=user.profile_image,
            role=updated_member.role,
            joined_at=updated_member.joined_at,
        )

    async def remove_member(self, project_id: uuid.UUID, member_id: uuid.UUID) -> bool:
        """Removes a member from the project while guaranteeing at least one ADMIN remains."""
        member = await self.project_repo.get_member_by_id(member_id)
        if not member or member.project_id != project_id:
            raise NotFoundException("ProjectMember", member_id)

        # Check admin retention
        if member.role == ProjectMemberRole.ADMIN.value:
            admin_count = await self.project_repo.count_admins(project_id)
            if admin_count <= 1:
                raise ConflictException("Cannot remove member: A project workspace must retain at least one active ADMIN.")

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
