import uuid
from typing import List, Optional, Union
from fastapi import Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.permissions import (
    Permission,
    ProjectRole,
    has_permission,
    normalize_role,
    get_member_permissions,
)
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
    if hasattr(result, "scalars"):
        sc = result.scalars
        if callable(sc):
            sc = sc()
        if hasattr(sc, "__await__"):
            sc = await sc
        if hasattr(sc, "first"):
            first_fn = sc.first
            if callable(first_fn):
                first_fn = first_fn()
            if hasattr(first_fn, "__await__"):
                return await first_fn
            return first_fn
    return None


async def enforce_member_permission(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    permission: Permission,
    db: AsyncSession,
    handover_status: Optional[str] = None,
) -> ProjectMember:
    """
    Core reusable permission enforcement function:
    1. Validates user is an authorized member of the project workspace (preventing IDOR).
    2. Computes effective permissions combining role defaults and custom permission grants.
    3. Enforces business constraints (e.g. incoming members cannot edit approved handovers).
    4. Raises ForbiddenException if access is denied.
    """
    member = await get_project_member(project_id=project_id, user_id=user_id, db=db)
    if not member:
        raise ForbiddenException("Access denied: You are not an authorized member of this project workspace.")

    # Immediate access revocation check
    if getattr(member, "status", None) == "revoked" or getattr(member, "invitation_status", None) == "revoked":
        raise ForbiddenException("Access denied: Your project membership has been revoked.")

    custom_perms = getattr(member, "custom_permissions", None)
    allowed = has_permission(
        role=member.role,
        permission=permission,
        custom_permissions=custom_perms,
        handover_status=handover_status,
    )

    if not allowed:
        # Special descriptive error for incoming members attempting to edit approved handovers
        if (
            permission == Permission.EDIT_HANDOVER
            and normalize_role(member.role) == ProjectRole.INCOMING
            and handover_status
            and handover_status.upper() in ("APPROVED", "SHARED", "ACKNOWLEDGED")
        ):
            raise ForbiddenException(
                "Access denied: Incoming members cannot edit approved handovers unless explicitly permitted."
            )

        raise ForbiddenException(
            f"Access denied: Missing required permission '{permission.value}'. "
            f"Your assigned role is '{member.role}'."
        )

    return member


def require_permission(
    permission: Permission,
    handover_status: Optional[str] = None,
):
    """
    FastAPI dependency factory enforcing granular RBAC permissions.
    Extracts project_id directly from route path parameters or queries via Request,
    or resolves parent project from document_id, handover_id, or task_id.
    """
    async def dependency(
        request: Request = None,
        project_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        handover_id: Optional[uuid.UUID] = None,
        task_id: Optional[uuid.UUID] = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectMember:
        target_project_id = project_id
        target_handover_status = handover_status

        if request is not None:
            p_params = getattr(request, "path_params", {}) or {}
            q_params = getattr(request, "query_params", {}) or {}

            if not target_project_id:
                raw_p = p_params.get("project_id") or q_params.get("projectId") or q_params.get("project_id")
                if raw_p:
                    target_project_id = uuid.UUID(str(raw_p)) if not isinstance(raw_p, uuid.UUID) else raw_p

            if not target_project_id:
                raw_h = p_params.get("handover_id") or handover_id
                raw_d = p_params.get("document_id") or document_id
                raw_t = p_params.get("task_id") or task_id

                if raw_h:
                    hid = uuid.UUID(str(raw_h)) if not isinstance(raw_h, uuid.UUID) else raw_h
                    h_stmt = select(Handover).where(Handover.id == hid)
                    h_res = await db.execute(h_stmt)
                    handover = h_res.scalars().first()
                    if not handover:
                        raise NotFoundException("Handover", hid)
                    target_project_id = handover.project_id
                    if target_handover_status is None:
                        target_handover_status = handover.status
                elif raw_d:
                    did = uuid.UUID(str(raw_d)) if not isinstance(raw_d, uuid.UUID) else raw_d
                    d_stmt = select(Document).where(Document.id == did)
                    d_res = await db.execute(d_stmt)
                    doc = d_res.scalars().first()
                    if not doc:
                        raise NotFoundException("Document", did)
                    target_project_id = doc.project_id
                elif raw_t:
                    tid = uuid.UUID(str(raw_t)) if not isinstance(raw_t, uuid.UUID) else raw_t
                    t_stmt = select(Task).where(Task.id == tid)
                    t_res = await db.execute(t_stmt)
                    task = t_res.scalars().first()
                    if not task:
                        raise NotFoundException("Task", tid)
                    target_project_id = task.project_id
        else:
            if not target_project_id:
                if handover_id:
                    h_stmt = select(Handover).where(Handover.id == handover_id)
                    h_res = await db.execute(h_stmt)
                    handover = h_res.scalars().first()
                    if not handover:
                        raise NotFoundException("Handover", handover_id)
                    target_project_id = handover.project_id
                    if target_handover_status is None:
                        target_handover_status = handover.status
                elif document_id:
                    d_stmt = select(Document).where(Document.id == document_id)
                    d_res = await db.execute(d_stmt)
                    doc = d_res.scalars().first()
                    if not doc:
                        raise NotFoundException("Document", document_id)
                    target_project_id = doc.project_id
                elif task_id:
                    t_stmt = select(Task).where(Task.id == task_id)
                    t_res = await db.execute(t_stmt)
                    task = t_res.scalars().first()
                    if not task:
                        raise NotFoundException("Task", task_id)
                    target_project_id = task.project_id

        if not target_project_id:
            raise BadRequestException("Missing project workspace identifier.")

        return await enforce_member_permission(
            project_id=target_project_id,
            user_id=current_user.id,
            permission=permission,
            db=db,
            handover_status=target_handover_status,
        )

    return dependency


def require_project_membership(
    allowed_roles: Optional[List[Union[ProjectMemberRole, ProjectRole, str]]] = None,
    permission: Optional[Permission] = None,
    handover_status: Optional[str] = None,
):
    """
    Factory creating a FastAPI dependency that verifies project membership,
    granular permissions, and allowed roles.
    Maintains backward compatibility while enforcing modern granular RBAC.
    """
    async def dependency(
        project_id: uuid.UUID = Path(..., description="Project workspace UUID"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectMember:
        member = await get_project_member(project_id=project_id, user_id=current_user.id, db=db)
        if not member:
            raise ForbiddenException("Access denied: You are not an authorized member of this project workspace.")

        if getattr(member, "status", None) == "revoked" or getattr(member, "invitation_status", None) == "revoked":
            raise ForbiddenException("Access denied: Your project membership has been revoked.")

        if permission:
            custom_perms = getattr(member, "custom_permissions", None)
            allowed = has_permission(
                role=member.role,
                permission=permission,
                custom_permissions=custom_perms,
                handover_status=handover_status,
            )
            if not allowed:
                if (
                    permission == Permission.EDIT_HANDOVER
                    and normalize_role(member.role) == ProjectRole.INCOMING
                    and handover_status
                    and handover_status.upper() in ("APPROVED", "SHARED", "ACKNOWLEDGED")
                ):
                    raise ForbiddenException(
                        "Access denied: Incoming members cannot edit approved handovers unless explicitly permitted."
                    )
                raise ForbiddenException(
                    f"Access denied: Missing required permission '{permission.value}'. "
                    f"Your assigned role is '{member.role}'."
                )

        if allowed_roles:
            allowed_canonical = {normalize_role(r) for r in allowed_roles}
            member_canonical = normalize_role(member.role)
            if member_canonical not in allowed_canonical:
                role_values = [getattr(r, "value", str(r)) for r in allowed_roles]
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
    the authenticated user is a verified member with view access to the parent project.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalars().first()
    if not document:
        raise NotFoundException("Document", document_id)

    await enforce_member_permission(
        project_id=document.project_id,
        user_id=current_user.id,
        permission=Permission.VIEW_PROJECT,
        db=db,
    )

    return document


async def require_handover_access(
    handover_id: uuid.UUID = Path(..., description="Handover UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Handover:
    """
    IDOR & Information Leakage Prevention:
    1. Validates handover exists.
    2. Validates user has VIEW_HANDOVER permission on parent project.
    3. Enforces rule: INCOMING members may ONLY access handovers that have been APPROVED or ACKNOWLEDGED.
       (Draft handovers remain hidden from incoming members until authorized human sign-off).
    """
    stmt = select(Handover).where(Handover.id == handover_id)
    result = await db.execute(stmt)
    handover = result.scalars().first()
    if not handover:
        raise NotFoundException("Handover", handover_id)

    member = await enforce_member_permission(
        project_id=handover.project_id,
        user_id=current_user.id,
        permission=Permission.VIEW_HANDOVER,
        db=db,
    )

    # Role-based draft isolation for INCOMING members
    normalized_r = normalize_role(member.role)
    if normalized_r == ProjectRole.INCOMING:
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

    await enforce_member_permission(
        project_id=task.project_id,
        user_id=current_user.id,
        permission=Permission.VIEW_PROJECT,
        db=db,
    )

    return task
