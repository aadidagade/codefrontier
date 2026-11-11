import uuid
from typing import List, Optional
from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.exceptions import ForbiddenException, NotFoundException
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.document import Document
from app.models.handover import Handover
from app.models.task import Task


async def get_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Optional[ProjectMember]:
    """Retrieves project membership record for a given user in a project."""
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalars().first()


def require_project_membership(allowed_roles: Optional[List[ProjectMemberRole]] = None):
    """
    Factory creating a FastAPI dependency that verifies project membership and roles.
    Completely eliminates IDOR by ensuring the user belongs to the project in the path.
    """
    async def dependency(
        project_id: uuid.UUID = Path(..., description="Project workspace UUID"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectMember:
        member = await get_project_member(project_id=project_id, user_id=current_user.id, db=db)
        if not member:
            raise ForbiddenException("Access denied: You are not an authorized member of this project workspace.")

        if allowed_roles:
            role_values = [r.value for r in allowed_roles]
            if member.role not in role_values:
                raise ForbiddenException(
                    f"Access denied: Action requires role in {role_values}. Your assigned role is '{member.role}'."
                )

        return member

    return dependency


async def require_document_access(
    document_id: uuid.UUID = Path(..., description="Document UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    """
    IDOR Prevention: Validates that the requested document exists and that
    the authenticated user is a verified member of the parent project.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalars().first()
    if not document:
        raise NotFoundException("Document", document_id)

    member = await get_project_member(project_id=document.project_id, user_id=current_user.id, db=db)
    if not member:
        raise ForbiddenException("Access denied: You do not have permission to access documents in this project.")

    return document


async def require_handover_access(
    handover_id: uuid.UUID = Path(..., description="Handover UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Handover:
    """
    IDOR & Information Leakage Prevention:
    1. Validates handover exists.
    2. Validates user is an authorized project member.
    3. Enforces rule: INCOMING members may ONLY access handovers that have been APPROVED or ACKNOWLEDGED.
       (Draft handovers remain hidden from incoming members until authorized human sign-off).
    """
    stmt = select(Handover).where(Handover.id == handover_id)
    result = await db.execute(stmt)
    handover = result.scalars().first()
    if not handover:
        raise NotFoundException("Handover", handover_id)

    member = await get_project_member(project_id=handover.project_id, user_id=current_user.id, db=db)
    if not member:
        raise ForbiddenException("Access denied: You are not a member of this project workspace.")

    # Role-based draft isolation for INCOMING members
    if member.role == ProjectMemberRole.INCOMING.value:
        status_upper = (handover.status or "").upper()
        if status_upper not in ("APPROVED", "SHARED", "ACKNOWLEDGED"):
            raise ForbiddenException(
                "Access restricted: This knowledge handover is still in draft or awaiting review. "
                "Incoming members can only access handovers after authorized approval."
            )

    return handover


async def require_task_access(
    task_id: uuid.UUID = Path(..., description="Task UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    """
    IDOR Prevention: Validates that the requested task exists and that
    the authenticated user is an authorized member of the owning project.
    """
    stmt = select(Task).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    if not task:
        raise NotFoundException("Task", task_id)

    member = await get_project_member(project_id=task.project_id, user_id=current_user.id, db=db)
    if not member:
        raise ForbiddenException("Access denied: You do not have permission to access tasks in this project.")

    return task
