import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update, delete
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.user import User
from app.models.document import Document
from app.models.handover import Handover, HandoverAuditLog
from app.models.conflict import Conflict
from app.models.task import Task


class ProjectRepository:
    """
    Asynchronous repository managing projects, team memberships,
    and live dashboard statistics calculated via PostgreSQL aggregation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        """Looks up a project by UUID."""
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_by_user(self, user_id: uuid.UUID) -> List[Tuple[Project, int]]:
        """
        Retrieves all projects where the given user is an active member,
        along with the total member count for each project.
        """
        # Count members subquery
        member_count_subq = (
            select(ProjectMember.project_id, func.count(ProjectMember.id).label("members_count"))
            .group_by(ProjectMember.project_id)
            .subquery()
        )

        stmt = (
            select(Project, func.coalesce(member_count_subq.c.members_count, 0))
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .outerjoin(member_count_subq, member_count_subq.c.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def create_project(
        self,
        name: str,
        created_by: uuid.UUID,
        description: Optional[str] = None,
        organization_name: Optional[str] = None,
    ) -> Project:
        """
        Creates a new project workspace and automatically enlists the creator
        as an authorized member with the ADMIN role.
        """
        project = Project(
            name=name.strip(),
            description=description.strip() if description else None,
            organization_name=organization_name.strip() if organization_name else None,
            created_by=created_by,
            status="active",
        )
        self.db.add(project)
        await self.db.flush()

        # Add creator as ADMIN
        admin_member = ProjectMember(
            project_id=project.id,
            user_id=created_by,
            role=ProjectMemberRole.ADMIN.value,
        )
        self.db.add(admin_member)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update_project(
        self,
        project_id: uuid.UUID,
        updates: Dict[str, Any],
    ) -> Optional[Project]:
        """Applies partial updates to a project."""
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(**updates)
            .returning(Project)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalars().first()

    async def delete_project(self, project_id: uuid.UUID) -> bool:
        """Deletes a project and all cascaded children (documents, handovers, members)."""
        stmt = delete(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    # -------------------------------------------------------------------------
    # Member Management
    # -------------------------------------------------------------------------

    async def get_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ProjectMember]:
        """Gets membership record for a specific user in a project."""
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_member_by_id(self, member_id: uuid.UUID) -> Optional[ProjectMember]:
        """Looks up a ProjectMember record by its UUID."""
        stmt = select(ProjectMember).where(ProjectMember.id == member_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_members_with_users(
        self,
        project_id: uuid.UUID,
    ) -> List[Tuple[ProjectMember, User]]:
        """Retrieves all project members joined with their User account information."""
        stmt = (
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.joined_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def count_admins(self, project_id: uuid.UUID) -> int:
        """Counts how many ADMINs exist in the project."""
        stmt = (
            select(func.count(ProjectMember.id))
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectMemberRole.ADMIN.value,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def add_member(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
    ) -> ProjectMember:
        """Adds a user to a project with a specific role."""
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def update_member_role(
        self,
        member_id: uuid.UUID,
        new_role: str,
    ) -> Optional[ProjectMember]:
        """Updates a member's role."""
        stmt = (
            update(ProjectMember)
            .where(ProjectMember.id == member_id)
            .values(role=new_role)
            .returning(ProjectMember)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalars().first()

    async def remove_member(self, member_id: uuid.UUID) -> bool:
        """Removes a member from the project."""
        stmt = delete(ProjectMember).where(ProjectMember.id == member_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    # -------------------------------------------------------------------------
    # Live Real-Time Project Statistics
    # -------------------------------------------------------------------------

    async def get_project_statistics(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """
        Executes actual SQL queries against PostgreSQL to compute live project metrics:
        - Uploaded vs processed documents
        - Total handovers and pending reviews
        - Open conflicts
        - Pending continuation tasks
        - Overall handover status
        """
        # 1. Document metrics
        doc_stmt = (
            select(
                func.count(Document.id).label("total_docs"),
                func.count(Document.id).filter(Document.processing_status == "ready").label("processed_docs"),
            )
            .where(Document.project_id == project_id)
        )
        doc_res = (await self.db.execute(doc_stmt)).one()
        total_docs = doc_res.total_docs
        processed_docs = doc_res.processed_docs

        # 2. Handover metrics
        hnd_stmt = (
            select(
                func.count(Handover.id).label("total_handovers"),
                func.count(Handover.id).filter(Handover.status == "awaiting_review").label("pending_reviews"),
                func.count(Handover.id).filter(Handover.status == "approved").label("approved_handovers"),
                func.count(Handover.id).filter(Handover.status == "acknowledged").label("acknowledged_handovers"),
            )
            .where(Handover.project_id == project_id)
        )
        hnd_res = (await self.db.execute(hnd_stmt)).one()
        total_handovers = hnd_res.total_handovers
        pending_reviews = hnd_res.pending_reviews
        approved_handovers = hnd_res.approved_handovers
        acknowledged_handovers = hnd_res.acknowledged_handovers

        # 3. Conflict metrics
        conflict_stmt = (
            select(func.count(Conflict.id))
            .where(Conflict.project_id == project_id, Conflict.status == "unresolved")
        )
        open_conflicts = (await self.db.execute(conflict_stmt)).scalar() or 0

        # 4. Continuation task metrics
        task_stmt = (
            select(func.count(Task.id))
            .where(Task.project_id == project_id, Task.status != "completed")
        )
        pending_tasks = (await self.db.execute(task_stmt)).scalar() or 0

        # 5. Derive overall handover status
        if total_handovers == 0:
            overall_status = "not_started"
        elif acknowledged_handovers > 0:
            overall_status = "acknowledged"
        elif approved_handovers > 0:
            overall_status = "approved"
        elif pending_reviews > 0:
            overall_status = "in_review"
        else:
            overall_status = "drafting"

        # 6. Fetch recent audit logs / activity
        activity_stmt = (
            select(HandoverAuditLog, User.full_name)
            .join(Handover, Handover.id == HandoverAuditLog.handover_id)
            .outerjoin(User, User.id == HandoverAuditLog.user_id)
            .where(Handover.project_id == project_id)
            .order_by(HandoverAuditLog.created_at.desc())
            .limit(10)
        )
        act_res = (await self.db.execute(activity_stmt)).all()
        recent_activity = [
            {
                "id": str(log.id),
                "action": log.action,
                "actor": actor_name or "System",
                "details": log.details,
                "timestamp": log.created_at.isoformat(),
            }
            for log, actor_name in act_res
        ]

        return {
            "total_documents": total_docs,
            "processed_documents": processed_docs,
            "total_handovers": total_handovers,
            "pending_reviews": pending_reviews,
            "open_conflicts": open_conflicts,
            "pending_tasks": pending_tasks,
            "overall_handover_status": overall_status,
            "recent_activity": recent_activity,
        }
