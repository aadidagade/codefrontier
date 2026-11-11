import uuid
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.notification import Notification
from app.models.project import ProjectMember, ProjectMemberRole

logger = logging.getLogger("app.services.notifications")


class NotificationService:
    """Centralized service for dispatching and querying database-backed notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        notification_type: str,
        project_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        """Creates and stages an individual user notification."""
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            project_id=project_id,
            title=title,
            message=message,
            notification_type=notification_type,
            is_read=False,
        )
        self.db.add(notif)
        await self.db.flush()
        logger.info(f"Notification staged: [{notification_type}] for user {user_id}")
        return notif

    async def notify_project_members(
        self,
        project_id: uuid.UUID,
        title: str,
        message: str,
        notification_type: str,
        exclude_user_id: Optional[uuid.UUID] = None,
        roles: Optional[List[ProjectMemberRole]] = None,
    ) -> List[Notification]:
        """Broadcasts a notification to project members filtered by role."""
        stmt = select(ProjectMember).where(ProjectMember.project_id == project_id)
        if roles:
            role_values = [r.value if isinstance(r, ProjectMemberRole) else str(r) for r in roles]
            stmt = stmt.where(ProjectMember.role.in_(role_values))

        res = await self.db.execute(stmt)
        members = res.scalars().all()

        created_notifs = []
        for m in members:
            if exclude_user_id and m.user_id == exclude_user_id:
                continue
            notif = await self.create_notification(
                user_id=m.user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                project_id=project_id,
            )
            created_notifs.append(notif)

        return created_notifs

    # -------------------------------------------------------------------------
    # High-Level Event Notification Helpers
    # -------------------------------------------------------------------------

    async def notify_project_invitation(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        project_name: str,
        invited_by_name: str,
        role: str,
    ) -> Notification:
        return await self.create_notification(
            user_id=user_id,
            project_id=project_id,
            title="Project Workspace Invitation",
            message=f"{invited_by_name} invited you to join '{project_name}' as a {role}.",
            notification_type="project_invitation",
        )

    async def notify_document_processed(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        document_name: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> Notification:
        if success:
            return await self.create_notification(
                user_id=user_id,
                project_id=project_id,
                title="Document Indexed Successfully",
                message=f"Document '{document_name}' has been extracted, chunked, and vector indexed.",
                notification_type="document_processing_completed",
            )
        else:
            return await self.create_notification(
                user_id=user_id,
                project_id=project_id,
                title="Document Ingestion Failed",
                message=f"Failed to process document '{document_name}': {error or 'Unknown extraction error'}",
                notification_type="document_processing_failed",
            )

    async def notify_handover_generated(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        handover_title: str,
    ) -> Notification:
        return await self.create_notification(
            user_id=user_id,
            project_id=project_id,
            title="Knowledge Handover Generated",
            message=f"Structured 10-chapter handover '{handover_title}' was synthesized and saved as DRAFT.",
            notification_type="handover_generated",
        )

    async def notify_handover_submitted_review(
        self,
        project_id: uuid.UUID,
        handover_title: str,
        submitted_by_name: str,
    ) -> List[Notification]:
        return await self.notify_project_members(
            project_id=project_id,
            title="Handover Submitted for Review",
            message=f"{submitted_by_name} submitted '{handover_title}' for formal tech lead review.",
            notification_type="handover_submitted_review",
            roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.LEAD],
        )

    async def notify_changes_requested(
        self,
        author_id: uuid.UUID,
        project_id: uuid.UUID,
        handover_title: str,
        reviewer_name: str,
        feedback: str,
    ) -> Notification:
        return await self.create_notification(
            user_id=author_id,
            project_id=project_id,
            title="Changes Requested on Handover",
            message=f"{reviewer_name} requested revisions on '{handover_title}': \"{feedback[:120]}\"",
            notification_type="changes_requested",
        )

    async def notify_handover_approved(
        self,
        project_id: uuid.UUID,
        handover_title: str,
        approved_by_name: str,
    ) -> List[Notification]:
        return await self.notify_project_members(
            project_id=project_id,
            title="Handover Approved",
            message=f"Knowledge handover '{handover_title}' was formally approved by {approved_by_name}.",
            notification_type="handover_approved",
        )

    async def notify_handover_shared(
        self,
        recipient_id: uuid.UUID,
        project_id: uuid.UUID,
        handover_title: str,
        shared_by_name: str,
    ) -> Notification:
        return await self.create_notification(
            user_id=recipient_id,
            project_id=project_id,
            title="Knowledge Handover Shared",
            message=f"{shared_by_name} shared the approved handover '{handover_title}' with you for onboarding.",
            notification_type="handover_shared",
        )

    async def notify_handover_acknowledged(
        self,
        project_id: uuid.UUID,
        handover_title: str,
        acknowledged_by_name: str,
    ) -> List[Notification]:
        return await self.notify_project_members(
            project_id=project_id,
            title="Handover Acknowledged",
            message=f"{acknowledged_by_name} completed checklist sign-off and accepted project responsibility for '{handover_title}'.",
            notification_type="handover_acknowledged",
            roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.LEAD, ProjectMemberRole.OUTGOING],
        )

    async def notify_task_assigned(
        self,
        assigned_to: uuid.UUID,
        project_id: uuid.UUID,
        task_title: str,
        assigned_by_name: str,
    ) -> Notification:
        return await self.create_notification(
            user_id=assigned_to,
            project_id=project_id,
            title="Continuation Task Assigned",
            message=f"{assigned_by_name} assigned continuation task '{task_title}' to you.",
            notification_type="task_assigned",
        )

    async def notify_task_unblocked(
        self,
        assigned_to: uuid.UUID,
        project_id: uuid.UUID,
        task_title: str,
        prerequisite_title: str,
    ) -> Notification:
        return await self.create_notification(
            user_id=assigned_to,
            project_id=project_id,
            title="Task Unblocked",
            message=f"Prerequisite task '{prerequisite_title}' is completed. Task '{task_title}' is now ready to begin.",
            notification_type="task_unblocked",
        )
