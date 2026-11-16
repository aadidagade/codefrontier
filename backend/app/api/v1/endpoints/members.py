import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import require_permission
from app.core.permissions import Permission
from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.audit_log import AuditActionType, AuditEntityType
from app.services.audit_service import AuditService
from app.services.project_service import ProjectService
from app.services.notification_service import NotificationService
from app.schemas.common import ApiResponse
from app.schemas.project import (
    MemberAdd,
    MemberUpdateRole,
    ProjectMemberResponse,
    MemberRevokeResponse,
)

router = APIRouter()


# =============================================================================
# 1. INVITE / ADD MEMBER TO PROJECT
# =============================================================================

@router.post(
    "/{project_id}/members",
    response_model=ApiResponse[ProjectMemberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Invite / Add Member to Project (Project Owner / Admin)",
    description="Invites an existing registered user to the project workspace with an assigned role. Requires MANAGE_PROJECT_MEMBERS permission.",
)
@router.post(
    "/{project_id}/members/invite",
    response_model=ApiResponse[ProjectMemberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Invite Member to Project Workspace",
)
async def add_project_member(
    project_id: uuid.UUID,
    payload: MemberAdd,
    request: Request,
    member: ProjectMember = Depends(require_permission(Permission.MANAGE_PROJECT_MEMBERS)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    new_member = await service.add_member(
        project_id=project_id,
        payload=payload,
        inviter_id=current_user.id,
    )

    # Fetch project name for notification context
    proj_stmt = select(Project.name).where(Project.id == project_id)
    proj_res = await db.execute(proj_stmt)
    proj_name = proj_res.scalar_one_or_none() or "Project Workspace"

    notif_svc = NotificationService(db)
    await notif_svc.notify_project_invitation(
        user_id=new_member.user_id,
        project_id=project_id,
        project_name=proj_name,
        invited_by_name=current_user.full_name or current_user.email,
        role=new_member.role_display_name or new_member.role,
    )

    # Record member invited audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.MEMBER_INVITED,
        entity_type=AuditEntityType.PROJECT_MEMBER,
        entity_id=new_member.id,
        user_id=current_user.id,
        project_id=project_id,
        change_metadata={
            "invited_email": new_member.email,
            "invited_user_id": str(new_member.user_id),
            "assigned_role": str(new_member.role),
            "role_display_name": new_member.role_display_name,
            "status": new_member.status,
            "invitation_status": new_member.invitation_status,
        },
        request=request,
    )
    await db.commit()

    return ApiResponse(
        data=new_member,
        message=f"Member '{new_member.email}' invited with role '{new_member.role_display_name}'. Status: '{new_member.status}'.",
    )


# =============================================================================
# 2. LIST PROJECT MEMBERS
# =============================================================================

@router.get(
    "/{project_id}/members",
    response_model=ApiResponse[List[ProjectMemberResponse]],
    summary="List All Project Members",
    description="Retrieves all project members with their assigned roles, invitation status, and membership status. Protected by VIEW_PROJECT permission.",
)
async def list_project_members(
    project_id: uuid.UUID,
    status: Optional[str] = Query(None, description="Filter by status: active, invited, revoked"),
    member: ProjectMember = Depends(require_permission(Permission.VIEW_PROJECT)),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    members = await service.list_members(project_id, status_filter=status)
    return ApiResponse(
        data=members,
        message="Project members retrieved successfully.",
    )


# =============================================================================
# 3. CHANGE MEMBER ROLE
# =============================================================================

@router.patch(
    "/{project_id}/members/{member_id}",
    response_model=ApiResponse[ProjectMemberResponse],
    summary="Change Member Role (Project Owner / Admin)",
    description="Changes a member's assigned role and permissions. Effective immediately on subsequent requests. Requires MANAGE_PROJECT_MEMBERS permission.",
)
@router.put(
    "/{project_id}/members/{member_id}",
    response_model=ApiResponse[ProjectMemberResponse],
    summary="Update Member Role",
)
async def update_project_member_role(
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: MemberUpdateRole,
    request: Request,
    member: ProjectMember = Depends(require_permission(Permission.MANAGE_PROJECT_MEMBERS)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    updated = await service.update_member_role(project_id, member_id, payload)

    # Dispatch notification to the updated member
    notif_svc = NotificationService(db)
    await notif_svc.create_notification(
        user_id=updated.user_id,
        project_id=project_id,
        title="Project Role Updated",
        message=f"Your assigned role in the project workspace has been changed to '{updated.role_display_name}'.",
        notification_type="role_updated",
    )

    # Record permission change audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.PERMISSION_CHANGED,
        entity_type=AuditEntityType.PROJECT_MEMBER,
        entity_id=member_id,
        user_id=current_user.id,
        project_id=project_id,
        change_metadata={
            "member_id": str(member_id),
            "target_user_id": str(updated.user_id),
            "member_email": updated.email,
            "new_role": str(updated.role),
            "new_role_display": updated.role_display_name,
            "custom_permissions": updated.custom_permissions,
        },
        request=request,
    )
    await db.commit()

    return ApiResponse(
        data=updated,
        message=f"Member role updated to '{updated.role_display_name}'.",
    )


# =============================================================================
# 4. REVOKE MEMBER ACCESS
# =============================================================================

@router.post(
    "/{project_id}/members/{member_id}/revoke",
    response_model=ApiResponse[MemberRevokeResponse],
    summary="Revoke Project Access (Project Owner / Admin)",
    description="Revokes a user's project access. Takes effect immediately: subsequent requests are blocked with HTTP 403. Requires MANAGE_PROJECT_MEMBERS permission.",
)
async def revoke_project_member(
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    request: Request,
    member: ProjectMember = Depends(require_permission(Permission.MANAGE_PROJECT_MEMBERS)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    revoke_res = await service.revoke_member_access(project_id, member_id)

    # Dispatch notification to user informing of revoked access
    notif_svc = NotificationService(db)
    await notif_svc.create_notification(
        user_id=revoke_res.user_id,
        project_id=project_id,
        title="Project Access Revoked",
        message="Your access privileges to this project workspace have been revoked by a project administrator.",
        notification_type="access_revoked",
    )

    # Record access revocation audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.ACCESS_REVOKED,
        entity_type=AuditEntityType.PROJECT_MEMBER,
        entity_id=member_id,
        user_id=current_user.id,
        project_id=project_id,
        change_metadata={
            "member_id": str(member_id),
            "revoked_user_id": str(revoke_res.user_id),
            "revocation_status": revoke_res.status,
            "action": "revoke_access",
        },
        request=request,
    )
    await db.commit()

    return ApiResponse(
        data=revoke_res,
        message=revoke_res.message,
    )


# =============================================================================
# 5. REMOVE MEMBER FROM PROJECT
# =============================================================================

@router.delete(
    "/{project_id}/members/{member_id}",
    response_model=ApiResponse[bool],
    summary="Remove Member from Project Workspace",
    description="Permanently deletes the member's association with the project. Requires MANAGE_PROJECT_MEMBERS permission.",
)
async def remove_project_member(
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    request: Request = None,
    member: ProjectMember = Depends(require_permission(Permission.MANAGE_PROJECT_MEMBERS)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    await service.remove_member(project_id, member_id)

    # Record member removal / access revocation audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.ACCESS_REVOKED,
        entity_type=AuditEntityType.PROJECT_MEMBER,
        entity_id=member_id,
        user_id=current_user.id,
        project_id=project_id,
        change_metadata={
            "member_id": str(member_id),
            "action": "remove_member",
        },
        request=request,
    )

    return ApiResponse(
        data=True,
        message="Member removed from project workspace successfully.",
    )


# =============================================================================
# 6. ACCEPT PROJECT INVITATION
# =============================================================================

@router.post(
    "/{project_id}/members/accept-invitation",
    response_model=ApiResponse[ProjectMemberResponse],
    summary="Accept Project Invitation",
    description="Allows an invited registered user to formally accept workspace membership, transitioning status from 'invited' to 'active'.",
)
@router.post(
    "/{project_id}/invitations/accept",
    response_model=ApiResponse[ProjectMemberResponse],
    summary="Accept Project Workspace Invitation",
)
async def accept_project_invitation(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    accepted_member = await service.accept_invitation(project_id, current_user.id)
    return ApiResponse(
        data=accepted_member,
        message=f"Project invitation accepted. You are now an active member with role '{accepted_member.role_display_name}'.",
    )
